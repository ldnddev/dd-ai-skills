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
        self.assertIn("![Issue pin map](screenshots/pin-map.png)", md)
        self.assertIn("**Pin legend:**", md)
        self.assertIn("#1 → A11Y-001 (color-contrast)", md)
        self.assertIn("![Annotated issue A11Y-001](screenshots/A11Y-001.png)", md)
        self.assertNotIn("Full page screenshot", md)

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


if __name__ == "__main__":
    unittest.main()
