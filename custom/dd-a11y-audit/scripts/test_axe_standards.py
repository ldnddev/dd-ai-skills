#!/usr/bin/env python3
"""Standards and dashboard checks that do not launch a browser."""
import tempfile
import unittest
from pathlib import Path

import axe_audit
import generate_a11y_report as report


class TestWcagTags(unittest.TestCase):
    def test_default_aa_is_wcag_22_a_and_aa(self):
        self.assertEqual(
            axe_audit.wcag_tags("AA"),
            ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"],
        )

    def test_level_a_excludes_aa_and_aaa(self):
        tags = axe_audit.wcag_tags("A")
        self.assertIn("wcag2a", tags)
        self.assertNotIn("wcag2aa", tags)
        self.assertNotIn("wcag2aaa", tags)
        self.assertNotIn("best-practice", tags)
        self.assertNotIn("wcag2a-obsolete", tags)

    def test_aaa_includes_aaa_tags(self):
        tags = axe_audit.wcag_tags("AAA")
        self.assertIn("wcag2aaa", tags)
        self.assertIn("wcag22aa", tags)


class TestPrinciples(unittest.TestCase):
    def test_sc_tags_map_to_pour_and_ignore_level_tags(self):
        tags = ["wcag2aa", "wcag22aa", "wcag111", "wcag412", "wcag1410", "wcag2411"]
        self.assertEqual(
            axe_audit.principles_for_tags(tags),
            ["perceivable", "robust", "operable"],
        )

    def test_counts_a_rule_once_per_principle(self):
        formatted = axe_audit.format_axe_results(
            {
                "violations": [
                    {"id": "area-alt", "impact": "critical", "tags": ["wcag2a", "wcag111", "wcag412"], "nodes": []},
                    {"id": "target-size", "impact": "serious", "tags": ["wcag22aa", "wcag258"], "nodes": []},
                ],
                "passes": [],
                "incomplete": [],
                "inapplicable": [],
                "testEngine": {"name": "axe-core", "version": "4.14.0"},
            },
            "https://example.com",
            "AA",
            expected_axe_version="4.14.0",
        )
        self.assertEqual(formatted["metadata"]["wcag_target"], "WCAG 2.2 Level AA")
        self.assertEqual(formatted["metadata"]["axe_core_version"], "4.14.0")
        self.assertNotIn("axe_version_warning", formatted["metadata"])
        self.assertEqual(formatted["principle_counts"]["perceivable"], 1)
        self.assertEqual(formatted["principle_counts"]["operable"], 1)
        self.assertEqual(formatted["principle_counts"]["robust"], 1)
        self.assertEqual(formatted["principle_counts"]["understandable"], 0)
        self.assertEqual(
            formatted["metadata"]["sc_checked"],
            ["wcag111", "wcag258", "wcag412"],
        )


class TestRuntimeManifest(unittest.TestCase):
    def test_override_forces_direct_axe_core(self):
        manifest = axe_audit.runtime_manifest("4.14.0", "4.14.0")
        self.assertEqual(manifest["dependencies"]["axe-core"], "4.14.0")
        self.assertEqual(manifest["dependencies"]["@axe-core/playwright"], "4.14.0")
        self.assertEqual(manifest["overrides"]["axe-core"], "$axe-core")


class TestDashboardMotion(unittest.TestCase):
    def test_page_cards_have_no_sal(self):
        html_doc = report._render_page_cards([
            {"page_url": "https://ex.com", "metadata": {"score": 80, "url": "https://ex.com"}},
            {"page_url": "https://ex.com/a", "metadata": {"score": 70, "url": "https://ex.com/a"}},
        ])
        self.assertNotIn("data-sal", html_doc)

    def test_template_disables_animation(self):
        text = (report.TEMPLATES_DIR / "dashboard.html").read_text()
        self.assertNotIn("data-sal=", text)
        self.assertIn("animation: none !important", text)
        self.assertIn("transition: none !important", text)
        self.assertIn("{{AXE_VERSION}}", text)

    def test_built_dashboard_strips_sal_and_names_wcag_22(self):
        results = {
            "metadata": {
                "url": "https://ex.com",
                "timestamp": "2026-10-24T00:00:00",
                "score": 80,
                "wcag_level": "AA",
                "wcag_target": "WCAG 2.2 Level AA",
                "axe_core_version": "4.14.0",
            },
            "summary": {
                "critical_violations": 0,
                "serious_violations": 0,
                "moderate_violations": 0,
                "minor_violations": 0,
                "total_violations": 0,
                "total_passes": 1,
                "total_incomplete": 0,
                "total_inapplicable": 0,
            },
            "principle_counts": {
                "perceivable": 0, "operable": 0, "understandable": 0, "robust": 0,
            },
            "violations": [],
            "recommendations": [],
            "pages": [{
                "page_url": "https://ex.com",
                "metadata": {"url": "https://ex.com", "score": 80},
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.html"
            report.build_dashboard(path, results, [])
            text = path.read_text()
        self.assertNotIn("data-sal=", text)
        self.assertIn("WCAG 2.2 Level AA", text)
        self.assertIn("4.14.0", text)
        self.assertIn("animation: none !important", text)
        self.assertNotIn("AA Compliant", text)

    def test_score_label_is_not_a_conformance_claim(self):
        self.assertNotIn("Compliant", report.score_label(95))
        self.assertEqual(report.wcag_target_label({"wcag_target": "WCAG 2.2 Level AA"}), "WCAG 2.2 Level AA")


if __name__ == "__main__":
    unittest.main()
