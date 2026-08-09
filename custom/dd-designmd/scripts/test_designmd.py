#!/usr/bin/env python3
"""Unit tests for dd-designmd helpers (no network)."""

import unittest
from pathlib import Path

from domain_util import domain_from_url, normalize_url
from emit_tokens import build_token_doc, tokens_to_css
from extract_design_signals import extract_signals


class TestDomain(unittest.TestCase):
    def test_strip_www(self):
        self.assertEqual(domain_from_url("https://www.ldnddev.com/path"), "ldnddev.com")

    def test_normalize_adds_https(self):
        self.assertTrue(normalize_url("ldnddev.com").startswith("https://"))


class TestSignals(unittest.TestCase):
    def test_extracts_hex_and_font(self):
        payload = {
            "domain": "example.com",
            "css": [{
                "url": "https://example.com",
                "inline": ["body{color:#112233;font-family:Arial,sans-serif;padding:16px}"],
                "sheets": [],
            }],
        }
        sig = extract_signals(payload)
        values = [c["value"] for c in sig["colors"]]
        self.assertIn("#112233", values)
        self.assertTrue(sig["font_families"])


class TestTokens(unittest.TestCase):
    def test_build_and_css(self):
        signals = {
            "colors": [{"value": "#ffffff", "count": 10}, {"value": "#000000", "count": 8}, {"value": "#336699", "count": 5}],
            "font_families": [{"value": "Inter, sans-serif", "count": 3}],
            "font_sizes": [{"value": "16px", "count": 2}],
            "font_weights": [],
            "spacing_values": [{"value": "16px", "count": 4}],
            "radii": [{"value": "4px", "count": 2}],
            "shadows": [],
            "breakpoints": [],
            "css_variables": [{"name": "--brand", "value": "#336699"}],
        }
        doc = build_token_doc(signals, "https://example.com", "example.com")
        self.assertIn("tokens", doc)
        self.assertTrue(doc["tokens"])
        css = tokens_to_css(doc)
        self.assertIn(":root", css)
        self.assertIn("--", css)


class TestDashboard(unittest.TestCase):
    def test_build_dashboard_writes_index(self):
        import tempfile
        from generate_dashboard import build_dashboard

        signals = {
            "colors": [{"value": "#336699", "count": 5}, {"value": "#ffffff", "count": 3}],
            "font_families": [{"value": "Inter, sans-serif", "count": 2}],
            "font_sizes": [{"value": "16px", "count": 2}],
            "spacing_values": [{"value": "8px", "count": 2}],
            "radii": [{"value": "4px", "count": 1}],
        }
        token_doc = build_token_doc(signals, "https://example.com", "example.com")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            index = build_dashboard(
                out,
                domain="example.com",
                primary_url="https://example.com",
                mode="single+nav",
                evidence_mode="static",
                pages_scanned=1,
                token_doc=token_doc,
                signals=signals,
                file_basenames={
                    "design_md": "example.com-design.md",
                    "tokens_json": "example.com-tokens.json",
                    "tokens_css": "example.com-tokens.css",
                    "evidence_json": "example.com-designmd-evidence.json",
                },
            )
            self.assertTrue(index.is_file())
            text = index.read_text(encoding="utf-8")
            self.assertIn("example.com", text)
            self.assertIn("Downloads", text)
            self.assertIn("example.com-design.md", text)
            self.assertIn("example.com-tokens.json", text)
            self.assertIn("swatch", text)
            self.assertTrue((out / "assets" / "css" / "style.min.css").is_file())


if __name__ == "__main__":
    unittest.main()
