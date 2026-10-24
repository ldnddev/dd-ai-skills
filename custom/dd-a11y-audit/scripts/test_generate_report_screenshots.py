#!/usr/bin/env python3
"""Unit tests for pin map + annotated issue screenshot wiring in report rows."""
import unittest

import generate_a11y_report as r


class TestScreenshotRows(unittest.TestCase):
    def test_prefers_pin_map_and_captured_issue_only(self):
        results = {
            "metadata": {"url": "https://ex.com", "timestamp": "t", "score": 50, "wcag_level": "AA"},
            "summary": {
                "critical_violations": 1, "serious_violations": 0,
                "moderate_violations": 0, "minor_violations": 0,
                "total_violations": 1, "total_passes": 0,
                "total_incomplete": 0, "total_inapplicable": 0,
            },
            "principle_counts": {"perceivable": 1, "operable": 0, "understandable": 0, "robust": 0},
            "violations": [{
                "id": "color-contrast",
                "impact": "critical",
                "description": "Elements must have sufficient color contrast",
                "help": "Fix contrast",
                "wcag_tags": ["wcag143"],
                "nodes_count": 1,
                "nodes_preview": [{"target": [".x"], "html": "<span class=x>a</span>"}],
            }],
            "screenshots": {
                "pin_map": "screenshots/pin-map.png",
                "full_page": "screenshots/pin-map.png",
                "pin_legend": [{"pin": 1, "task_id": "A11Y-001", "rule_id": "color-contrast", "impact": "critical"}],
                "issues": [{
                    "task_id": "A11Y-001",
                    "path": "screenshots/A11Y-001.png",
                    "status": "captured",
                }],
            },
            "recommendations": [],
        }
        # Single-page JSON has screenshots on the root — get_pages wraps that.
        pages = r.get_pages(results)
        self.assertTrue(pages)
        rows = r.build_task_rows(results)
        self.assertEqual(rows[0]["page_screenshot"], "screenshots/pin-map.png")
        self.assertEqual(rows[0]["issue_screenshot"], "screenshots/A11Y-001.png")

        md = r.generate_markdown_report(results)
        # Default: link only (small reports); embed is opt-in
        self.assertIn("[Pin map](screenshots/pin-map.png)", md)
        self.assertNotIn("![Issue pin map]", md)
        self.assertIn("**Pin legend:**", md)
        self.assertIn("#1 → A11Y-001 (color-contrast)", md)
        self.assertIn("[Annotated screenshot for A11Y-001](screenshots/A11Y-001.png)", md)
        self.assertNotIn("Full page screenshot", md)

        md_embed = r.generate_markdown_report(results, embed_screenshots=True)
        self.assertIn("![Issue pin map](screenshots/pin-map.png)", md_embed)
        self.assertIn("![Annotated issue A11Y-001](screenshots/A11Y-001.png)", md_embed)

    def test_skips_non_captured_issue_path(self):
        results = {
            "metadata": {"url": "https://ex.com", "timestamp": "t", "score": 50, "wcag_level": "AA"},
            "summary": {
                "critical_violations": 0, "serious_violations": 1,
                "moderate_violations": 0, "minor_violations": 0,
                "total_violations": 1, "total_passes": 0,
                "total_incomplete": 0, "total_inapplicable": 0,
            },
            "principle_counts": {"perceivable": 0, "operable": 1, "understandable": 0, "robust": 0},
            "violations": [{
                "id": "button-name",
                "impact": "serious",
                "description": "Buttons must have discernible text",
                "help": "Add name",
                "wcag_tags": ["wcag412"],
                "nodes_count": 1,
                "nodes_preview": [{"target": ["button"], "html": "<button></button>"}],
            }],
            "screenshots": {
                "pin_map": None,
                "issues": [{"task_id": "A11Y-001", "path": None, "status": "not-found"}],
            },
            "recommendations": [],
        }
        rows = r.build_task_rows(results)
        self.assertEqual(rows[0]["issue_screenshot"], "")
        self.assertEqual(rows[0]["page_screenshot"], "")

    def test_skips_issue_with_path_but_non_captured_status(self):
        """Status filter must ignore non-captured entries even if path is set."""
        results = {
            "metadata": {"url": "https://ex.com", "timestamp": "t", "score": 50, "wcag_level": "AA"},
            "summary": {
                "critical_violations": 0, "serious_violations": 1,
                "moderate_violations": 0, "minor_violations": 0,
                "total_violations": 1, "total_passes": 0,
                "total_incomplete": 0, "total_inapplicable": 0,
            },
            "principle_counts": {"perceivable": 0, "operable": 1, "understandable": 0, "robust": 0},
            "violations": [{
                "id": "button-name",
                "impact": "serious",
                "description": "Buttons must have discernible text",
                "help": "Add name",
                "wcag_tags": ["wcag412"],
                "nodes_count": 1,
                "nodes_preview": [{"target": ["button"], "html": "<button></button>"}],
            }],
            "screenshots": {
                "pin_map": "screenshots/pin-map.png",
                "issues": [{
                    "task_id": "A11Y-001",
                    "path": "screenshots/stale.png",
                    "status": "not-visible",
                }],
            },
            "recommendations": [],
        }
        rows = r.build_task_rows(results)
        self.assertEqual(rows[0]["page_screenshot"], "screenshots/pin-map.png")
        self.assertEqual(rows[0]["issue_screenshot"], "")

    def test_page_pin_map_prefers_pin_map_over_full_page(self):
        page = {
            "screenshots": {
                "pin_map": "screenshots/pin-map.png",
                "full_page": "screenshots/legacy-full.png",
            }
        }
        self.assertEqual(r._page_pin_map(page), "screenshots/pin-map.png")

    def test_page_pin_map_falls_back_to_full_page(self):
        page = {"screenshots": {"full_page": "screenshots/legacy-full.png"}}
        self.assertEqual(r._page_pin_map(page), "screenshots/legacy-full.png")

    def test_page_cards_use_pin_map_button_label(self):
        pages = [{
            "page_url": "https://ex.com/page",
            "metadata": {"score": 42},
            "screenshots": {"pin_map": "screenshots/pin-map.png"},
        }]
        html = r._render_page_cards(pages)
        self.assertIn("View pin map", html)
        self.assertIn("of accessibility issues on https://ex.com/page", html)
        self.assertIn('src="screenshots/pin-map.png"', html)
        self.assertNotIn("View screenshot", html)

    def test_page_cards_link_to_the_live_page(self):
        pages = [{"page_url": "https://ex.com", "metadata": {"score": 90}, "screenshots": {}}]
        html = r._render_page_cards(pages)
        self.assertIn("Open page", html)
        self.assertIn('href="https://ex.com"', html)
        self.assertNotIn("No pin map captured", html)
        self.assertNotIn("<img", html)

    def test_task_rows_annotated_and_pin_map_labels(self):
        rows = [{
            "task_id": "A11Y-001",
            "page_url": "https://ex.com",
            "priority": "Critical",
            "issue": "Contrast",
            "owner": "Frontend Development",
            "timeline": "Immediate (1-2 days)",
            "selector": ".x",
            "issue_screenshot": "screenshots/A11Y-001.png",
            "page_screenshot": "screenshots/pin-map.png",
        }, {
            "task_id": "A11Y-002",
            "page_url": "https://ex.com",
            "priority": "Serious",
            "issue": "Name",
            "owner": "Frontend Development",
            "timeline": "Week 1",
            "selector": "button",
            "issue_screenshot": "",
            "page_screenshot": "screenshots/pin-map.png",
        }]
        html = r._render_task_rows(rows)
        self.assertIn(">Annotated<span", html)
        self.assertIn("screenshot for A11Y-001", html)
        self.assertIn('href="screenshots/A11Y-001.png"', html)
        self.assertIn(">Pin map<span", html)
        self.assertIn("for A11Y-002", html)

    def test_multi_page_global_task_ids_match_screenshot_paths(self):
        """Table task IDs must link to files named with the same global A11Y-###."""
        results = {
            "metadata": {
                "url": "https://ex.com", "timestamp": "t", "score": 50,
                "wcag_level": "AA", "mode": "multi",
            },
            "summary": {
                "critical_violations": 2, "serious_violations": 0,
                "moderate_violations": 0, "minor_violations": 0,
                "total_violations": 2, "total_passes": 0,
                "total_incomplete": 0, "total_inapplicable": 0,
            },
            "principle_counts": {
                "perceivable": 1, "operable": 1, "understandable": 0, "robust": 0,
            },
            "pages": [
                {
                    "page_url": "https://ex.com/a",
                    "page_slug": "a",
                    "task_id_start": 1,
                    "metadata": {"url": "https://ex.com/a", "score": 40},
                    "summary": {
                        "critical_violations": 1, "serious_violations": 0,
                        "moderate_violations": 0, "minor_violations": 0,
                    },
                    "violations": [{
                        "id": "image-alt",
                        "impact": "critical",
                        "description": "img alt",
                        "help": "add alt",
                        "wcag_tags": [],
                        "nodes_count": 1,
                        "nodes_preview": [{"target": ["img"], "html": "<img>"}],
                    }],
                    "screenshots": {
                        "pin_map": "pages/a/screenshots/pin-map.png",
                        "issues": [{
                            "task_id": "A11Y-001",
                            "path": "pages/a/screenshots/A11Y-001.png",
                            "status": "captured",
                            "rule_id": "image-alt",
                        }],
                    },
                },
                {
                    "page_url": "https://ex.com/b",
                    "page_slug": "b",
                    "task_id_start": 2,
                    "metadata": {"url": "https://ex.com/b", "score": 40},
                    "summary": {
                        "critical_violations": 1, "serious_violations": 0,
                        "moderate_violations": 0, "minor_violations": 0,
                    },
                    "violations": [{
                        "id": "button-name",
                        "impact": "critical",
                        "description": "btn name",
                        "help": "name",
                        "wcag_tags": [],
                        "nodes_count": 1,
                        "nodes_preview": [{"target": ["button"], "html": "<button>"}],
                    }],
                    "screenshots": {
                        "pin_map": "pages/b/screenshots/pin-map.png",
                        "issues": [{
                            "task_id": "A11Y-002",
                            "path": "pages/b/screenshots/A11Y-002.png",
                            "status": "captured",
                            "rule_id": "button-name",
                        }],
                    },
                },
            ],
            "recommendations": [],
        }
        rows = r.build_task_rows(results)
        self.assertEqual(rows[0]["task_id"], "A11Y-001")
        self.assertEqual(rows[0]["issue_screenshot"], "pages/a/screenshots/A11Y-001.png")
        self.assertEqual(rows[1]["task_id"], "A11Y-002")
        self.assertEqual(rows[1]["issue_screenshot"], "pages/b/screenshots/A11Y-002.png")
        # Must not point page-2 task at page-local A11Y-001.png
        self.assertNotEqual(rows[1]["issue_screenshot"], "pages/b/screenshots/A11Y-001.png")

        html = r._render_task_rows(rows)
        self.assertIn('href="pages/b/screenshots/A11Y-002.png"', html)
        self.assertIn("screenshot for A11Y-002", html)

        md = r.generate_markdown_report(results)
        self.assertIn(
            "[Annotated screenshot for A11Y-002](pages/b/screenshots/A11Y-002.png)",
            md,
        )

    def test_legacy_page_local_screenshot_fallback(self):
        """Older multi-page bundles stored A11Y-001 per page; still resolve content."""
        results = {
            "metadata": {
                "url": "https://ex.com", "timestamp": "t", "score": 50,
                "wcag_level": "AA", "mode": "multi",
            },
            "summary": {
                "critical_violations": 2, "serious_violations": 0,
                "moderate_violations": 0, "minor_violations": 0,
                "total_violations": 2, "total_passes": 0,
                "total_incomplete": 0, "total_inapplicable": 0,
            },
            "principle_counts": {
                "perceivable": 1, "operable": 1, "understandable": 0, "robust": 0,
            },
            "pages": [
                {
                    "page_url": "https://ex.com/a",
                    "page_slug": "a",
                    "metadata": {"score": 40},
                    "summary": {
                        "critical_violations": 1, "serious_violations": 0,
                        "moderate_violations": 0, "minor_violations": 0,
                    },
                    "violations": [{
                        "id": "image-alt", "impact": "critical",
                        "description": "img", "help": "alt", "wcag_tags": [],
                        "nodes_count": 1,
                        "nodes_preview": [{"target": ["img"], "html": "<img>"}],
                    }],
                    "screenshots": {
                        "issues": [{
                            "task_id": "A11Y-001",
                            "path": "pages/a/screenshots/A11Y-001.png",
                            "status": "captured",
                        }],
                    },
                },
                {
                    "page_url": "https://ex.com/b",
                    "page_slug": "b",
                    "metadata": {"score": 40},
                    "summary": {
                        "critical_violations": 1, "serious_violations": 0,
                        "moderate_violations": 0, "minor_violations": 0,
                    },
                    "violations": [{
                        "id": "button-name", "impact": "critical",
                        "description": "btn", "help": "name", "wcag_tags": [],
                        "nodes_count": 1,
                        "nodes_preview": [{"target": ["button"], "html": "<button>"}],
                    }],
                    "screenshots": {
                        "issues": [{
                            "task_id": "A11Y-001",
                            "path": "pages/b/screenshots/A11Y-001.png",
                            "status": "captured",
                        }],
                    },
                },
            ],
            "recommendations": [],
        }
        rows = r.build_task_rows(results)
        self.assertEqual(rows[1]["task_id"], "A11Y-002")
        # Legacy: path still page-local filename, but content is that page's first issue
        self.assertEqual(rows[1]["issue_screenshot"], "pages/b/screenshots/A11Y-001.png")


if __name__ == "__main__":
    unittest.main()
