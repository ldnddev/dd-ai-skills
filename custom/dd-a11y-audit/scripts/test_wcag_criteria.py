#!/usr/bin/env python3
"""WCAG criteria gap follows the scanned level."""
import tempfile
import unittest
from pathlib import Path

import generate_a11y_report as report
from wcag_criteria import criteria_for_level, criteria_not_run


def _results(level, checked):
    return {
        "metadata": {
            "url": "https://ex.com",
            "timestamp": "2026-10-24T00:00:00",
            "score": 80,
            "wcag_level": level,
            "wcag_target": f"WCAG 2.2 Level {level}",
            "axe_core_version": "4.14.0",
            "sc_checked": checked,
        },
        "summary": {
            "critical_violations": 1, "serious_violations": 0,
            "moderate_violations": 0, "minor_violations": 0,
            "total_violations": 1, "total_passes": 1,
            "total_incomplete": 0, "total_inapplicable": 0,
        },
        "principle_counts": {
            "perceivable": 1, "operable": 0, "understandable": 0, "robust": 0,
        },
        "violations": [{
            "id": "color-contrast",
            "impact": "serious",
            "description": "Elements must have sufficient color contrast",
            "help": "Fix contrast",
            "wcag_tags": ["wcag143"],
            "nodes_count": 1,
            "nodes_preview": [{"target": ["main p"], "html": "<p>x</p>"}],
            "task_id": "A11Y-002",
        }],
        "recommendations": [],
        "sitewide": [{
            "task_id": "A11Y-001",
            "rule_id": "color-contrast",
            "impact": "critical",
            "scope": "sitewide-chrome",
            "selector": "header a.logo",
            "html": "<a class='logo'>Home</a>",
            "description": "Elements must have sufficient color contrast",
            "help": "Fix contrast",
            "wcag_tags": ["wcag143"],
            "nodes_count": 1,
            "page_count": 2,
            "pages": [
                {"page_url": "https://ex.com/", "page_slug": "home"},
                {"page_url": "https://ex.com/about", "page_slug": "about"},
            ],
            "representative": {"page_url": "https://ex.com/", "page_slug": "home"},
            "visual": True,
            "issue_screenshot": "pages/home/screenshots/A11Y-001.png",
        }],
        "pages": [{
            "page_url": "https://ex.com/",
            "page_slug": "home",
            "metadata": {"score": 80, "sc_checked": checked},
            "summary": {
                "critical_violations": 1, "serious_violations": 1,
                "moderate_violations": 0, "minor_violations": 0,
            },
            "violations": [{
                "id": "color-contrast",
                "impact": "critical",
                "description": "Elements must have sufficient color contrast",
                "help": "Fix contrast",
                "wcag_tags": ["wcag143"],
                "nodes_count": 1,
                "rollup_task_id": "A11Y-001",
                "nodes_preview": [{"target": ["header a.logo"], "html": "<a class='logo'>Home</a>"}],
            }, {
                "id": "color-contrast",
                "impact": "serious",
                "description": "Elements must have sufficient color contrast",
                "help": "Fix contrast",
                "wcag_tags": ["wcag143"],
                "nodes_count": 1,
                "task_id": "A11Y-002",
                "nodes_preview": [{"target": ["main p"], "html": "<p>x</p>"}],
            }],
        }],
    }


class TestChecklistUsesTheCatalog(unittest.TestCase):
    def test_prose_checklist_does_not_repeat_the_criterion_list(self):
        checklist = (
            Path(__file__).resolve().parents[1]
            / "skills" / "dd-a11y" / "references" / "wcag-checklist.md"
        ).read_text()
        self.assertIn("scripts/wcag_criteria.py", checklist)
        self.assertNotIn("4.1.1 Parsing", checklist)
        self.assertNotIn("4.1.4", checklist)
        self.assertNotIn("1.2.1 Audio-only", checklist)
        for sc in criteria_for_level("AAA"):
            self.assertNotIn(f"{sc['id']} {sc['name']}", checklist)


class TestCatalog(unittest.TestCase):
    def test_level_counts_exclude_removed_parsing(self):
        self.assertEqual(len(criteria_for_level("A")), 31)
        self.assertEqual(len(criteria_for_level("AA")), 55)
        self.assertEqual(len(criteria_for_level("AAA")), 86)
        for level in ("A", "AA", "AAA"):
            ids = [item["id"] for item in criteria_for_level(level)]
            self.assertNotIn("4.1.1", ids)
            self.assertNotIn("4.1.4", ids)

    def test_gap_follows_the_requested_level(self):
        checked = ["wcag143", "wcag326"]
        aa_ids = [item["id"] for item in criteria_not_run("AA", checked)]
        a_ids = [item["id"] for item in criteria_not_run("A", checked)]
        aaa_ids = [item["id"] for item in criteria_not_run("AAA", checked)]
        self.assertNotIn("1.4.3", aa_ids)
        self.assertNotIn("3.2.6", aa_ids)
        self.assertIn("1.2.4", aa_ids)
        self.assertIn("2.4.11", aa_ids)
        self.assertIn("2.5.8", aa_ids)
        self.assertIn("3.3.8", aa_ids)
        self.assertNotIn("1.4.6", aa_ids)
        self.assertNotIn("3.3.9", aa_ids)
        self.assertNotIn("1.4.3", a_ids)
        self.assertNotIn("2.5.8", a_ids)
        self.assertIn("1.4.6", aaa_ids)
        self.assertIn("2.5.5", aaa_ids)
        self.assertIn("3.3.9", aaa_ids)


class TestReportGap(unittest.TestCase):
    def test_markdown_lists_gap_and_sitewide_once(self):
        results = _results("AA", ["wcag143"])
        md = report.generate_markdown_report(results)
        self.assertIn("## Criteria this scan did not run", md)
        self.assertIn("WCAG 2.2 Level AA", md)
        self.assertIn("1.2.4 Captions (Live) (AA)", md)
        self.assertNotIn("1.4.3 Contrast (Minimum)", md)
        self.assertNotIn("1.4.6 Contrast (Enhanced)", md)
        self.assertNotIn("4.1.1", md)
        self.assertIn("## Sitewide findings", md)
        self.assertIn("**Scope:** Sitewide chrome", md)
        self.assertIn("**Seen on:** 2 pages", md)
        self.assertEqual(md.count("#### A11Y-001"), 0)
        self.assertEqual(md.count("### A11Y-001"), 1)
        self.assertIn("#### A11Y-002", md)
        self.assertIn("listed once above (1)", md)
        self.assertIn("[Annotated screenshot for A11Y-001](pages/home/screenshots/A11Y-001.png)", md)

    def test_level_a_omits_aa_criteria(self):
        md = report.generate_markdown_report(_results("A", []))
        self.assertIn("WCAG 2.2 Level A", md)
        self.assertIn("1.1.1 Non-text Content (A)", md)
        self.assertNotIn("1.4.3 Contrast (Minimum)", md)
        self.assertNotIn("2.5.5 Target Size (Enhanced)", md)

    def test_dashboard_has_criteria_sitewide_and_live_link(self):
        results = _results("AAA", ["wcag143"])
        rows = report.build_task_rows(results)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.html"
            report.build_dashboard(path, results, rows)
            html = path.read_text()
        self.assertIn("Criteria this scan did not run", html)
        self.assertIn("WCAG 2.2 Level AAA", html)
        self.assertIn("2.5.5 Target Size (Enhanced) (AAA)", html)
        self.assertNotIn("1.4.3 Contrast (Minimum)", html)
        self.assertIn('id="sitewide"', html)
        self.assertIn("Sitewide chrome", html)
        self.assertIn("Open page", html)
        self.assertNotIn("data-sal=", html)
        self.assertNotIn("No pin map captured", html)

    def test_unrecorded_scan_does_not_invent_a_full_gap(self):
        results = _results("AA", [])
        del results["metadata"]["sc_checked"]
        del results["pages"][0]["metadata"]["sc_checked"]
        md = report.generate_markdown_report(results)
        self.assertIn("did not record which success criteria ran", md)
        self.assertNotIn("1.2.4 Captions (Live)", md)


if __name__ == "__main__":
    unittest.main()
