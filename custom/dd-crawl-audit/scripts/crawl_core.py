#!/usr/bin/env python3
"""
dd-crawl core: whole-site URL scanner + link checker (Python stdlib only).

Crawls internal pages from a base URL, records HTTP status for every discovered
URL, supports chrome-once / exclude, robots.txt, and basic auth.
"""

from __future__ import annotations

import collections
import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.robotparser import RobotFileParser

DEFAULT_UA = "dd-crawl/1.1 (+https://ldnddev.com; site-mapper/link-checker)"
HTML_TYPES = ("text/html", "application/xhtml+xml")
ASSET_EXTS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".mjs", ".zip", ".gz", ".mp4", ".mp3", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pptx", ".woff", ".woff2", ".ttf", ".map",
)


def normalize(url: str) -> str:
    url, _ = urllib.parse.urldefrag(url.strip())
    return url


def normalize_start_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return normalize(url)


def same_domain(url: str, root_netloc: str) -> bool:
    netloc = urllib.parse.urlparse(url).netloc.lower()
    root = root_netloc.lower()
    return netloc == root or netloc == "www." + root or "www." + netloc == root


def classify(url: str) -> str:
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme in ("mailto", "tel"):
        return "contact"
    if scheme in ("", "http", "https"):
        return "web"
    return "other"


def looks_like_asset(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in ASSET_EXTS)


class LinkExtractor(HTMLParser):
    """Collect hrefs; track chrome vs page anchors; honor exclude tags/ids."""

    def __init__(self, chrome_tags: set[str], exclude_tags: set[str], exclude_ids: set[str]):
        super().__init__()
        self.chrome_tags = chrome_tags
        self.exclude_tags = exclude_tags
        self.exclude_ids = exclude_ids
        self.page_links: list[str] = []
        self.chrome_links: list[str] = []
        # stack entries: (tag, starts_exclude, starts_chrome)
        self._stack: list[tuple[str, bool, bool]] = []
        self._exclude_depth = 0
        self._chrome_depth = 0

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        tag_l = tag.lower()
        starts_ex = tag_l in self.exclude_tags or (ad.get("id") in self.exclude_ids)
        starts_ch = (not starts_ex) and tag_l in self.chrome_tags and self._exclude_depth == 0
        self._stack.append((tag_l, starts_ex, starts_ch))
        if starts_ex:
            self._exclude_depth += 1
        if starts_ch:
            self._chrome_depth += 1
        if self._exclude_depth:
            return
        if tag_l == "a" and "href" in ad:
            href = ad.get("href") or ""
            if self._chrome_depth > 0:
                self.chrome_links.append(href)
            else:
                self.page_links.append(href)

    def handle_endtag(self, tag):
        tag_l = tag.lower()
        # pop until matching tag
        while self._stack:
            t, starts_ex, starts_ch = self._stack.pop()
            if starts_ex and self._exclude_depth:
                self._exclude_depth -= 1
            if starts_ch and self._chrome_depth:
                self._chrome_depth -= 1
            if t == tag_l:
                break


@dataclass
class CrawlResult:
    base_url: str
    root_netloc: str
    results: dict = field(default_factory=dict)
    chrome_links: dict = field(default_factory=dict)
    pages_crawled: int = 0
    max_pages_hit: bool = False
    robots_used: bool = False
    robots_blocked: list = field(default_factory=list)
    elapsed: float = 0.0
    options: dict = field(default_factory=dict)


class Crawler:
    def __init__(
        self,
        base_url: str,
        exclude_tags: Iterable[str],
        exclude_ids: Iterable[str],
        chrome_tags: Iterable[str],
        max_pages: int,
        delay: float,
        timeout: float,
        check_external: bool,
        depth: int | None,
        respect_robots: bool,
        auth: tuple[str, str] | None,
    ):
        self.base_url = normalize_start_url(base_url)
        self.root_netloc = urllib.parse.urlparse(self.base_url).netloc
        self.exclude_tags = {t.lower() for t in exclude_tags}
        self.exclude_ids = set(exclude_ids)
        self.chrome_tags = {t.lower() for t in chrome_tags} - self.exclude_tags
        self.max_pages = max_pages
        self.delay = delay
        self.timeout = timeout
        self.check_external = check_external
        self.depth_limit = depth  # None = unlimited (still capped by max_pages)
        self.respect_robots = respect_robots
        self.auth = auth

        self.results: dict[str, dict] = {}
        self.chrome_links: dict[str, dict] = {}
        self.chrome_scanned = False
        self.status_cache: dict[str, tuple] = {}
        self.queue: collections.deque[tuple[str, int]] = collections.deque()
        self.crawl_seen: set[str] = set()
        self.pages_crawled = 0
        self.robots_blocked: list[str] = []
        self._rp: RobotFileParser | None = None
        self._opener = self._build_opener()

    def _build_opener(self):
        handlers = []
        if self.auth:
            user, password = self.auth
            pwd = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            # protect entire origin
            origin = f"{urllib.parse.urlparse(self.base_url).scheme}://{self.root_netloc}"
            pwd.add_password(None, origin, user, password)
            # also bare www variant
            bare = self.root_netloc[4:] if self.root_netloc.startswith("www.") else "www." + self.root_netloc
            pwd.add_password(None, f"{urllib.parse.urlparse(self.base_url).scheme}://{bare}", user, password)
            handlers.append(urllib.request.HTTPBasicAuthHandler(pwd))
        return urllib.request.build_opener(*handlers)

    def _load_robots(self):
        if not self.respect_robots:
            return
        parsed = urllib.parse.urlparse(self.base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        try:
            req = urllib.request.Request(robots_url, headers={"User-Agent": DEFAULT_UA})
            with self._opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            rp.parse(raw.splitlines())
            self._rp = rp
        except Exception:
            self._rp = None  # missing/unreadable robots → allow

    def _allowed(self, url: str) -> bool:
        if not self.respect_robots or self._rp is None:
            return True
        try:
            return self._rp.can_fetch(DEFAULT_UA, url)
        except Exception:
            return True

    def _request(self, url: str, method: str = "GET") -> tuple[int | str, str, str, bytes]:
        """Return status, note, content-type, body bytes (empty for HEAD)."""
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
        req.get_method = lambda m=method: m  # type: ignore[method-assign]
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                final = resp.geturl()
                status = getattr(resp, "status", None) or resp.getcode() or 200
                ctype = resp.headers.get("Content-Type", "")
                body = b"" if method == "HEAD" else resp.read()
                note = f"redirected -> {final}" if final.rstrip("/") != url.rstrip("/") else ""
                # history not available like requests; detect via final URL
                return status, note, ctype, body
        except urllib.error.HTTPError as e:
            note = ""
            try:
                final = e.geturl()
                if final and final.rstrip("/") != url.rstrip("/"):
                    note = f"redirected -> {final}"
            except Exception:
                pass
            return e.code, note or (e.reason or ""), e.headers.get("Content-Type", "") if e.headers else "", b""
        except Exception as e:
            return "ERROR", type(e).__name__, "", b""

    def _probe(self, url: str) -> tuple:
        if url in self.status_cache:
            return self.status_cache[url]
        status, note, _ctype, _body = self._request(url, method="HEAD")
        if status == "ERROR" or (isinstance(status, int) and (status >= 400 or status == 405)):
            status, note, _ctype, _body = self._request(url, method="GET")
        self.status_cache[url] = (status, note)
        return status, note

    def _check_head(self, url: str, bucket: dict):
        status, note = self._probe(url)
        target = bucket.get(url)
        if target:
            target["status"], target["note"] = status, note

    def _enqueue(self, url: str, depth: int):
        if url not in self.crawl_seen:
            if self.depth_limit is not None and depth > self.depth_limit:
                return
            self.queue.append((url, depth))
            self.crawl_seen.add(url)

    def _record_chrome(self, href: str, page_url: str, depth: int):
        url = normalize(urllib.parse.urljoin(page_url, href))
        kind = classify(url)
        if kind == "web" and url not in self.chrome_links:
            internal = same_domain(url, self.root_netloc)
            self.chrome_links[url] = {
                "type": "internal" if internal else "external",
                "status": None,
                "note": "",
                "found_on": page_url,
                "chrome_only": True,
            }
            if internal and not looks_like_asset(url):
                if self._allowed(url):
                    self._enqueue(url, depth + 1)
                else:
                    self.robots_blocked.append(url)
                    self.chrome_links[url]["status"] = "robots-disallow"
                    self.chrome_links[url]["note"] = "blocked by robots.txt"
            elif internal:
                self._check_head(url, self.chrome_links)
            elif self.check_external:
                self._check_head(url, self.chrome_links)
            else:
                self.chrome_links[url]["status"] = "not checked"
        elif kind == "contact" and url not in self.chrome_links:
            self.chrome_links[url] = {
                "type": "contact",
                "status": "-",
                "note": "",
                "found_on": page_url,
                "chrome_only": True,
            }

    def _record(self, href: str, page_url: str, depth: int):
        url = normalize(urllib.parse.urljoin(page_url, href))
        kind = classify(url)
        if kind == "contact":
            if url not in self.results:
                self.results[url] = {
                    "type": "contact", "status": "-", "note": "",
                    "found_on": page_url, "chrome_only": False,
                }
            return
        if kind == "other":
            if url not in self.results:
                self.results[url] = {
                    "type": "other", "status": "-",
                    "note": urllib.parse.urlparse(url).scheme + " link",
                    "found_on": page_url, "chrome_only": False,
                }
            return

        internal = same_domain(url, self.root_netloc)
        if url in self.results or url in self.chrome_links:
            return

        if internal:
            if looks_like_asset(url):
                self.results[url] = {
                    "type": "internal asset", "status": None, "note": "",
                    "found_on": page_url, "chrome_only": False,
                }
                self._check_head(url, self.results)
            else:
                self.results[url] = {
                    "type": "internal page", "status": None, "note": "",
                    "found_on": page_url, "chrome_only": False,
                }
                if self._allowed(url):
                    self._enqueue(url, depth + 1)
                else:
                    self.robots_blocked.append(url)
                    self.results[url]["status"] = "robots-disallow"
                    self.results[url]["note"] = "blocked by robots.txt"
        else:
            self.results[url] = {
                "type": "external", "status": None, "note": "",
                "found_on": page_url, "chrome_only": False,
            }
            if self.check_external:
                self._check_head(url, self.results)
            else:
                self.results[url]["status"] = "not checked"

    def crawl(self) -> CrawlResult:
        t0 = time.time()
        self._load_robots()
        if not self._allowed(self.base_url):
            self.results[self.base_url] = {
                "type": "internal page",
                "status": "robots-disallow",
                "note": "start URL blocked by robots.txt",
                "found_on": "(start)",
                "chrome_only": False,
            }
            return self._finish(t0)

        self.results[self.base_url] = {
            "type": "internal page", "status": None, "note": "",
            "found_on": "(start)", "chrome_only": False,
        }
        self._enqueue(self.base_url, 0)

        while self.queue and self.pages_crawled < self.max_pages:
            url, depth = self.queue.popleft()
            self._crawl_page(url, depth)
            self.pages_crawled += 1
            if self.delay:
                time.sleep(self.delay)

        max_hit = bool(self.queue)
        return self._finish(t0, max_hit)

    def _finish(self, t0: float, max_hit: bool = False) -> CrawlResult:
        return CrawlResult(
            base_url=self.base_url,
            root_netloc=self.root_netloc,
            results=self.results,
            chrome_links=self.chrome_links,
            pages_crawled=self.pages_crawled,
            max_pages_hit=max_hit,
            robots_used=self.respect_robots and self._rp is not None,
            robots_blocked=sorted(set(self.robots_blocked)),
            elapsed=time.time() - t0,
            options={},
        )

    def _crawl_page(self, url: str, depth: int):
        print(f"  [{self.pages_crawled + 1}] (d={depth}) {url}", flush=True)
        entry = self.results.get(url) or self.chrome_links.get(url)
        if entry is None:
            entry = self.results.setdefault(
                url,
                {
                    "type": "internal page", "status": None, "note": "",
                    "found_on": "(start)", "chrome_only": False,
                },
            )
        status, note, ctype, body = self._request(url, method="GET")
        entry["status"] = status
        entry["note"] = note
        if status == "ERROR" or (isinstance(status, int) and status >= 400):
            return
        ctype0 = (ctype or "").split(";")[0].strip().lower()
        if not any(ctype0.startswith(t) for t in HTML_TYPES):
            return
        try:
            text = body.decode("utf-8", errors="replace")
        except Exception:
            return

        parser = LinkExtractor(self.chrome_tags, self.exclude_tags, self.exclude_ids)
        try:
            parser.feed(text)
        except Exception:
            return

        if not self.chrome_scanned and parser.chrome_links:
            for href in parser.chrome_links:
                self._record_chrome(href, url, depth)
            self.chrome_scanned = True
        elif not self.chrome_scanned:
            # still mark scanned after first HTML page so we don't wait forever
            self.chrome_scanned = True

        for href in parser.page_links:
            self._record(href, url, depth)


def summarize(result: CrawlResult) -> dict:
    def count(pred):
        return sum(1 for m in result.results.values() if pred(m))

    broken = count(
        lambda m: (isinstance(m["status"], int) and m["status"] >= 400)
        or m["status"] in ("ERROR", "robots-disallow")
    )
    redirects = count(
        lambda m: (isinstance(m["status"], int) and 300 <= m["status"] < 400)
        or (isinstance(m.get("note"), str) and m["note"].startswith("redirected"))
    )
    return {
        "total_urls": len(result.results),
        "chrome_urls": len(result.chrome_links),
        "internal": count(lambda m: str(m["type"]).startswith("internal")),
        "external": count(lambda m: m["type"] == "external"),
        "broken": broken,
        "redirects": redirects,
        "pages_crawled": result.pages_crawled,
        "max_pages_hit": result.max_pages_hit,
        "robots_used": result.robots_used,
        "robots_blocked_count": len(result.robots_blocked),
        "elapsed_s": round(result.elapsed, 2),
    }


def to_data_json(result: CrawlResult, summary: dict, options: dict) -> dict:
    def pack(bucket: dict, chrome_only: bool):
        rows = []
        for url, m in sorted(bucket.items()):
            rows.append({
                "url": url,
                "type": m.get("type"),
                "status": m.get("status"),
                "note": m.get("note") or "",
                "found_on": m.get("found_on") or "",
                "chrome_only": chrome_only or bool(m.get("chrome_only")),
                "is_broken": (
                    (isinstance(m.get("status"), int) and m["status"] >= 400)
                    or m.get("status") in ("ERROR", "robots-disallow")
                ),
                "is_redirect": bool(
                    (isinstance(m.get("status"), int) and 300 <= m["status"] < 400)
                    or str(m.get("note") or "").startswith("redirected")
                ),
            })
        return rows

    return {
        "meta": {
            "base_url": result.base_url,
            "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tool": "dd-crawl",
            "version": "1.1.0",
            "options": options,
        },
        "summary": summary,
        "urls": pack(result.results, False),
        "chrome": pack(result.chrome_links, True),
        "robots_blocked": result.robots_blocked,
    }


def write_csvs(data: dict, all_path: Path, broken_path: Path) -> None:
    fields = ["url", "type", "status", "note", "found_on", "chrome_only", "is_broken", "is_redirect"]
    all_rows = data.get("urls", []) + data.get("chrome", [])
    with all_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in all_rows:
            w.writerow({k: row.get(k, "") for k in fields})
    with broken_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in all_rows:
            if row.get("is_broken"):
                w.writerow({k: row.get(k, "") for k in fields})
