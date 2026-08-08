#!/usr/bin/env python3
"""Collect same-origin CSS text from fetched page HTML."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

from domain_util import same_site

UA = "dd-designmd/1.0 (+https://ldnddev.com)"


class StyleRefParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.stylesheets: list[str] = []
        self.inline: list[str] = []
        self._in_style = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "link":
            rel = (ad.get("rel") or "").lower()
            href = ad.get("href") or ""
            if "stylesheet" in rel and href:
                self.stylesheets.append(urljoin(self.base_url, href))
        if tag == "style":
            self._in_style = True
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "style" and self._in_style:
            self.inline.append("".join(self._buf))
            self._in_style = False
            self._buf = []

    def handle_data(self, data):
        if self._in_style:
            self._buf.append(data)


def fetch_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read()[: 2 * 1024 * 1024].decode(charset, errors="replace")


def collect_css_for_page(page: dict, max_sheets: int = 20) -> dict:
    base = page.get("final_url") or page.get("url") or ""
    html = page.get("html") or ""
    parser = StyleRefParser(base)
    try:
        parser.feed(html)
    except Exception as exc:  # noqa: BLE001
        return {"url": base, "inline": [], "sheets": [], "error": str(exc)}

    sheets = []
    for href in parser.stylesheets[:max_sheets]:
        if not same_site(base, href):
            continue
        try:
            text = fetch_text(href)
            sheets.append({"href": href, "css": text, "error": None})
        except Exception as exc:  # noqa: BLE001
            sheets.append({"href": href, "css": "", "error": str(exc)})

    return {
        "url": base,
        "inline": parser.inline,
        "sheets": sheets,
        "error": None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON from fetch_pages.py")
    args = parser.parse_args()
    data = json.loads(open(args.input, encoding="utf-8").read())
    results = []
    for page in data.get("pages") or []:
        if page.get("error") or not page.get("html"):
            continue
        results.append(collect_css_for_page(page))
    print(json.dumps({"domain": data.get("domain"), "css": results}, indent=2))


if __name__ == "__main__":
    main()
