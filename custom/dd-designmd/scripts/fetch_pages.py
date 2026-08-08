#!/usr/bin/env python3
"""Fetch HTML pages and discover same-site top-nav links."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse

from domain_util import domain_from_url, normalize_url, same_site

UA = "dd-designmd/1.0 (+https://ldnddev.com)"


class LinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: list[dict] = []
        self._in_nav = 0
        self._in_header = 0
        self._capture_a = False
        self._a_href = ""
        self._a_text: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag in ("nav",):
            self._in_nav += 1
        if tag == "header":
            self._in_header += 1
        if tag == "title":
            self._in_title = True
        if tag == "a" and "href" in ad:
            role = ad.get("role", "")
            classes = ad.get("class", "")
            in_chrome = self._in_nav > 0 or self._in_header > 0
            # Prefer nav/header; also allow top-level menu-ish classes
            if in_chrome or re.search(r"nav|menu|header", classes, re.I):
                self._capture_a = True
                self._a_href = ad.get("href", "")
                self._a_text = []

    def handle_endtag(self, tag):
        if tag in ("nav",) and self._in_nav:
            self._in_nav -= 1
        if tag == "header" and self._in_header:
            self._in_header -= 1
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._capture_a:
            href = urljoin(self.base_url, self._a_href)
            text = " ".join("".join(self._a_text).split())
            self.links.append({"href": href, "text": text})
            self._capture_a = False
            self._a_href = ""
            self._a_text = []

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._capture_a:
            self._a_text.append(data)


def fetch_html(url: str, timeout: int = 25) -> dict:
    url = normalize_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final = resp.geturl()
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read()
            # Cap 4MB
            html = raw[: 4 * 1024 * 1024].decode(charset, errors="replace")
            return {
                "url": url,
                "final_url": final,
                "status": getattr(resp, "status", 200),
                "html": html,
                "error": None,
            }
    except Exception as exc:  # noqa: BLE001 — surface as structured error
        return {
            "url": url,
            "final_url": url,
            "status": None,
            "html": "",
            "error": str(exc),
        }


def extract_nav_links(base_url: str, html: str) -> list[str]:
    parser = LinkParser(base_url)
    try:
        parser.feed(html)
    except Exception:
        return []
    seen = set()
    out = []
    for item in parser.links:
        href = item["href"]
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if not same_site(base_url, href):
            continue
        # Drop fragments and trailing slash normalize for dedupe
        parsed = urlparse(href)
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
        if parsed.query:
            clean += f"?{parsed.query}"
        key = clean.rstrip("/") or clean
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return out


def collect_urls(primary: str, extra: list[str] | None, expand_nav: bool, max_extra: int) -> list[str]:
    primary = normalize_url(primary)
    urls = [primary]
    if extra:
        for u in extra:
            u = normalize_url(u)
            if u not in urls:
                urls.append(u)
        return urls[: 1 + max(0, max_extra) + 50]  # multi-list: generous but bounded later

    if not expand_nav:
        return urls

    home = fetch_html(primary)
    if home.get("html"):
        for link in extract_nav_links(home.get("final_url") or primary, home["html"]):
            if link not in urls:
                urls.append(link)
            if len(urls) >= 1 + max_extra:
                break
    return urls


def main():
    parser = argparse.ArgumentParser(description="Fetch pages for design system extraction")
    parser.add_argument("urls", nargs="+", help="One or more URLs")
    parser.add_argument("--max-extra", type=int, default=8, help="Max nav pages when single URL")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    multi = len(args.urls) > 1
    if multi:
        plan = [normalize_url(u) for u in args.urls][:25]
    else:
        plan = collect_urls(args.urls[0], None, expand_nav=True, max_extra=args.max_extra)

    pages = []
    for u in plan:
        page = fetch_html(u)
        # Don't keep huge html in summary mode unless needed — keep for pipeline
        pages.append(page)

    out = {
        "domain": domain_from_url(plan[0]),
        "mode": "multi" if multi else "single+nav",
        "urls": plan,
        "pages": pages,
    }
    print(json.dumps(out, indent=2) if args.json else json.dumps(out))


if __name__ == "__main__":
    main()
