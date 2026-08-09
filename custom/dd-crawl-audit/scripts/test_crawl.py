#!/usr/bin/env python3
"""Unit tests for dd-crawl (stdlib, no network)."""

import tempfile
import unittest
from pathlib import Path

from crawl_core import LinkExtractor, normalize_start_url, same_domain, write_csvs
from generate_dashboard import build_dashboard


class TestHelpers(unittest.TestCase):
    def test_normalize_scheme(self):
        self.assertTrue(normalize_start_url("example.com").startswith("https://"))

    def test_same_domain_www(self):
        self.assertTrue(same_domain("https://www.example.com/a", "example.com"))
        self.assertTrue(same_domain("https://example.com/a", "www.example.com"))
        self.assertFalse(same_domain("https://blog.example.com/a", "example.com"))


class TestLinkExtractor(unittest.TestCase):
    def test_chrome_vs_page_and_exclude(self):
        html = """
        <html><body>
          <header><a href="/about">About</a></header>
          <main><a href="/pricing">Pricing</a>
            <div id="skip-me"><a href="/secret">Secret</a></div>
          </main>
          <footer><a href="/legal">Legal</a></footer>
        </body></html>
        """
        p = LinkExtractor(
            chrome_tags={"header", "footer", "nav"},
            exclude_tags=set(),
            exclude_ids={"skip-me"},
        )
        p.feed(html)
        self.assertIn("/pricing", p.page_links)
        self.assertNotIn("/secret", p.page_links)
        self.assertIn("/about", p.chrome_links)
        self.assertIn("/legal", p.chrome_links)


class TestExports(unittest.TestCase):
    def test_csv_and_dashboard(self):
        data = {
            "meta": {
                "base_url": "https://example.com",
                "generated": "2026-08-08T00:00:00Z",
                "options": {"excluded": "none"},
            },
            "summary": {
                "total_urls": 2,
                "chrome_urls": 1,
                "internal": 1,
                "external": 1,
                "broken": 1,
                "redirects": 0,
                "pages_crawled": 1,
                "max_pages_hit": False,
                "robots_used": False,
                "robots_blocked_count": 0,
                "elapsed_s": 0.5,
            },
            "urls": [
                {
                    "url": "https://example.com/",
                    "type": "internal page",
                    "status": 200,
                    "note": "",
                    "found_on": "(start)",
                    "chrome_only": False,
                    "is_broken": False,
                    "is_redirect": False,
                },
                {
                    "url": "https://example.com/missing",
                    "type": "internal page",
                    "status": 404,
                    "note": "",
                    "found_on": "https://example.com/",
                    "chrome_only": False,
                    "is_broken": True,
                    "is_redirect": False,
                },
            ],
            "chrome": [
                {
                    "url": "https://example.com/about",
                    "type": "internal",
                    "status": 200,
                    "note": "",
                    "found_on": "https://example.com/",
                    "chrome_only": True,
                    "is_broken": False,
                    "is_redirect": False,
                }
            ],
            "robots_blocked": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_csvs(data, out / "all-urls.csv", out / "broken.csv")
            self.assertIn("missing", (out / "broken.csv").read_text())
            self.assertIn("example.com", (out / "all-urls.csv").read_text())
            index = build_dashboard(
                out,
                data,
                {
                    "all_csv": "all-urls.csv",
                    "broken_csv": "broken.csv",
                    "data_json": "data.json",
                },
            )
            text = index.read_text(encoding="utf-8")
            self.assertIn("Broken URLs", text)
            self.assertIn("Site chrome", text)
            self.assertIn("Downloads", text)
            self.assertIn("all-urls.csv", text)
            self.assertTrue((out / "assets" / "css" / "style.min.css").is_file())


if __name__ == "__main__":
    unittest.main()
