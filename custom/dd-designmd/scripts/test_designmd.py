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

    def test_extracts_layout_and_elevation(self):
        payload = {
            "domain": "example.com",
            "css": [{
                "url": "https://example.com",
                "inline": [
                    ".wrap{max-width:72rem;display:grid;grid-template-columns:1fr 1fr;"
                    "gap:24px;padding:16px;z-index:10;"
                    "box-shadow:0 2px 8px rgba(0,0,0,.2);"
                    "background:linear-gradient(#fff,#eee)}"
                ],
                "sheets": [],
            }],
        }
        sig = extract_signals(payload)
        self.assertTrue(any(x["value"] == "72rem" for x in sig["max_widths"]))
        self.assertTrue(any(x["value"] == "grid" for x in sig["displays"]))
        self.assertTrue(sig["grid_templates"])
        self.assertTrue(any(x["value"] == "24px" for x in sig["gaps"]))
        self.assertTrue(any(x["value"] == "16px" for x in sig["paddings"]))
        self.assertTrue(any(x["value"] == "10" for x in sig["z_indexes"]))
        self.assertTrue(sig["shadows"])
        self.assertTrue(sig["gradients"])

    def test_extracts_focus_outline(self):
        payload = {
            "domain": "example.com",
            "css": [{
                "url": "https://example.com",
                "inline": [
                    "a:focus-visible{outline:2px solid #336699;outline-offset:3px}"
                ],
                "sheets": [],
            }],
        }
        sig = extract_signals(payload)
        self.assertTrue(sig["focus_rules"])
        self.assertTrue(any("2px" in x["value"] for x in sig["outlines"]))

    def test_extracts_hover_and_disabled(self):
        payload = {
            "domain": "example.com",
            "css": [{
                "url": "https://example.com",
                "inline": [
                    "a:hover{color:#336699} button:disabled{opacity:0.5}"
                    "[aria-disabled='true']{pointer-events:none}"
                ],
                "sheets": [],
            }],
        }
        sig = extract_signals(payload)
        self.assertTrue(sig["interactions"]["hover"])
        self.assertTrue(sig["interactions"]["disabled"])


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

    def test_container_token_from_max_width(self):
        signals = {
            "colors": [],
            "font_families": [],
            "font_sizes": [],
            "font_weights": [],
            "spacing_values": [],
            "radii": [],
            "shadows": [],
            "breakpoints": [],
            "css_variables": [],
            "max_widths": [{"value": "72rem", "count": 4}],
        }
        doc = build_token_doc(signals, "https://example.com", "example.com")
        self.assertEqual(doc["tokens"]["space.container"]["value"], "72rem")


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
            self.assertIn("/assets/css/style.min.css", text)
            self.assertFalse((out / "assets").exists())


class TestDesignMd(unittest.TestCase):
    def test_required_headings_and_overview_surface(self):
        from run_designmd import missing_required_headings, render_design_md

        signals = {
            "colors": [{"value": "#112233", "count": 2}],
            "font_families": [],
            "font_sizes": [],
            "spacing_values": [],
            "radii": [],
            "shadows": [],
            "breakpoints": [],
            "max_widths": [{"value": "72rem", "count": 2}],
            "displays": [{"value": "flex", "count": 3}],
            "gradients": [],
        }
        token_doc = build_token_doc(signals, "https://example.com", "example.com")
        md = render_design_md(
            domain="example.com",
            primary_url="https://example.com",
            pages=[{
                "url": "https://example.com",
                "final_url": "https://example.com",
                "status": 200,
                "html": (
                    "<html><head><title>Acme Widgets</title>"
                    '<meta name="description" content="We make widgets.">'
                    '<link rel="icon" href="/favicon.svg">'
                    "</head><body>"
                    '<img class="logo" src="/logo.svg" alt="Acme">'
                    "<h1>Hello</h1>"
                    "<button>Get started</button>"
                    "</body></html>"
                ),
                "error": None,
            }],
            mode="single+nav",
            evidence_mode="static",
            signals=signals,
            token_doc=token_doc,
        )
        self.assertEqual(missing_required_headings(md), [])
        self.assertIn("### Product summary", md)
        self.assertIn("We make widgets.", md)
        self.assertIn("Acme Widgets", md)
        self.assertIn("### Generation constraints", md)
        self.assertIn("Do not introduce gradients", md)
        self.assertIn("## Agent instructions", md)
        self.assertIn("## Logo & brand mark", md)
        self.assertIn("/logo.svg", md)
        self.assertIn("## Content & copy patterns", md)
        self.assertIn("Get started", md)
        self.assertIn("## Focus & keyboard", md)
        self.assertIn("## Color usage rules", md)
        self.assertIn("## Interactive states", md)
        self.assertIn("Do not use for", md)
        self.assertIn("none extracted — do not invent", md)
        self.assertNotIn("## Product / brand snapshot", md)

    def test_template_lists_required_headings(self):
        from run_designmd import REQUIRED_MD_HEADINGS

        template = (
            Path(__file__).resolve().parent.parent
            / "skills"
            / "dd-designmd"
            / "references"
            / "design-doc-template.md"
        )
        text = template.read_text(encoding="utf-8")
        missing = [h for h in REQUIRED_MD_HEADINGS if h not in text]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
