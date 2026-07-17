#!/usr/bin/env python3
"""Unit tests for report generation (no network)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_report import (  # noqa: E402
    build_task_rows,
    generate_all,
    resolve_insights,
    score_label,
    _rating_badge,
    _score_bar_mod,
    _render_score_bars,
)


class TestResolveInsights(unittest.TestCase):
    def test_known_id_uses_playbook(self):
        what, why, how = resolve_insights(
            "render-blocking-resources",
            psi_description="PSI says something",
            metric="LCP",
        )
        self.assertTrue(len(what) > 20)
        self.assertTrue(len(why) > 20)
        self.assertTrue(len(how) > 20)
        self.assertNotIn("PSI says something", what)

    def test_unknown_id_falls_back_to_psi_description(self):
        what, why, how = resolve_insights(
            "totally-unknown-audit-xyz",
            psi_description="Custom PSI description about widgets.",
            metric="TBT",
        )
        self.assertIn("widgets", what)
        self.assertIn("TBT", why)
        self.assertTrue(len(how) > 10)

    def test_unknown_id_without_psi_uses_generic_what(self):
        what, why, how = resolve_insights(
            "totally-unknown-audit-xyz",
            psi_description="",
            metric="Performance",
        )
        self.assertIn("Lighthouse", what)
        self.assertIn("performance score", why.lower())



def _fixture() -> dict:
    return {
        "metadata": {
            "url": "https://example.com",
            "urls": ["https://example.com", "https://example.com/about"],
            "timestamp": "2026-07-15T12:00:00Z",
            "strategies": ["mobile", "desktop"],
            "stack_labels": ["WordPress", "Cloudflare"],
            "tool": "dd-site-speed",
            "version": "1.1.0",
        },
        "pages": [
            {
                "page_url": "https://example.com",
                "page_slug": "example-com",
                "stack": {
                    "primary": {"id": "wordpress", "label": "WordPress", "confidence": 0.9},
                    "labels": ["WordPress", "Cloudflare"],
                },
                "strategies": {
                    "mobile": {
                        "strategy": "mobile",
                        "performance_score": 42,
                        "field_data_available": False,
                        "metrics": {
                            "LCP": {
                                "value": 4200,
                                "unit": "ms",
                                "label": "Largest Contentful Paint",
                                "rating": "poor",
                                "source": "lab",
                            },
                            "INP": {
                                "value": 280,
                                "unit": "ms",
                                "label": "Interaction to Next Paint",
                                "rating": "needs-improvement",
                                "source": "lab",
                            },
                            "CLS": {
                                "value": 0.18,
                                "unit": "",
                                "label": "Cumulative Layout Shift",
                                "rating": "needs-improvement",
                                "source": "lab",
                            },
                        },
                        "opportunities": [
                            {
                                "id": "render-blocking-resources",
                                "title": "Eliminate render-blocking resources",
                                "description": "Blocking",
                                "savings_ms": 1200,
                                "savings_bytes": 0,
                                "display": "1.2s",
                            },
                            {
                                "id": "modern-image-formats",
                                "title": "Serve images in next-gen formats",
                                "description": "Images",
                                "savings_ms": 800,
                                "savings_bytes": 250000,
                                "display": "250 KiB",
                            },
                        ],
                        "diagnostics": [],
                        "error": None,
                    },
                    "desktop": {
                        "strategy": "desktop",
                        "performance_score": 68,
                        "field_data_available": False,
                        "metrics": {
                            "LCP": {
                                "value": 2800,
                                "unit": "ms",
                                "label": "Largest Contentful Paint",
                                "rating": "needs-improvement",
                                "source": "lab",
                            },
                        },
                        "opportunities": [],
                        "diagnostics": [],
                        "error": None,
                    },
                },
                "error": None,
            },
            {
                "page_url": "https://example.com/about",
                "page_slug": "example-com-about",
                "stack": {"labels": ["WordPress"]},
                "strategies": {
                    "mobile": {
                        "strategy": "mobile",
                        "performance_score": 55,
                        "metrics": {
                            "LCP": {
                                "value": 3000,
                                "unit": "ms",
                                "label": "Largest Contentful Paint",
                                "rating": "needs-improvement",
                                "source": "lab",
                            },
                        },
                        "opportunities": [
                            {
                                "id": "unused-javascript",
                                "title": "Reduce unused JavaScript",
                                "description": "JS",
                                "savings_ms": 350,
                                "savings_bytes": 0,
                                "display": "350ms",
                            }
                        ],
                        "error": None,
                    },
                    "desktop": {
                        "strategy": "desktop",
                        "performance_score": 70,
                        "metrics": {},
                        "opportunities": [],
                        "error": None,
                    },
                },
                "error": None,
            },
        ],
        "limitations": [],
    }


class TestTaskInsights(unittest.TestCase):
    def test_opportunity_rows_include_what_why_how(self):
        rows = build_task_rows(_fixture())
        rbr = next(r for r in rows if r["opportunity_id"] == "render-blocking-resources")
        self.assertIn("block", rbr["what"].lower())
        self.assertTrue(len(rbr["why"]) > 20)
        self.assertIn("Defer", rbr["how"])  # playbook how
        self.assertIn("WordPress", rbr["how"])  # stack tip still appended

    def test_unknown_opportunity_uses_psi_description(self):
        data = _fixture()
        data["pages"][0]["strategies"]["mobile"]["opportunities"].append({
            "id": "brand-new-audit-999",
            "title": "Brand new audit",
            "description": "Widgets are not optimized for speed.",
            "savings_ms": 900,
            "savings_bytes": 0,
            "display": "0.9s",
        })
        rows = build_task_rows(data)
        row = next(r for r in rows if r["opportunity_id"] == "brand-new-audit-999")
        self.assertIn("Widgets", row["what"])
        self.assertTrue(row["why"])
        self.assertTrue(row["how"])

    def test_cwv_tasks_use_curated_insights(self):
        data = {
            "metadata": {"stack_labels": []},
            "pages": [{
                "page_url": "https://example.com/cwv",
                "page_slug": "cwv",
                "stack": {"labels": []},
                "strategies": {
                    "mobile": {
                        "strategy": "mobile",
                        "performance_score": 40,
                        "metrics": {
                            "INP": {
                                "value": 400,
                                "unit": "ms",
                                "label": "Interaction to Next Paint",
                                "rating": "poor",
                                "source": "lab",
                            },
                        },
                        "opportunities": [],
                        "error": None,
                    },
                    "desktop": {
                        "strategy": "desktop",
                        "performance_score": 50,
                        "metrics": {},
                        "opportunities": [],
                        "error": None,
                    },
                },
                "error": None,
            }],
        }
        rows = build_task_rows(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["opportunity_id"], "cwv-inp")
        self.assertIn("Interaction", rows[0]["what"])
        self.assertIn("Core Web Vital", rows[0]["why"])


class TestGenerateReport(unittest.TestCase):
    def test_score_label(self):
        self.assertEqual(score_label(95), "Excellent")
        self.assertEqual(score_label(42), "Poor")
        self.assertEqual(score_label(None), "Unavailable")

    def test_rating_badge_colors(self):
        self.assertIn("dd-badge -pass", _rating_badge("good"))
        self.assertIn("Good", _rating_badge("good"))
        self.assertIn("dd-badge -warning", _rating_badge("needs-improvement"))
        self.assertIn("Needs improvement", _rating_badge("needs-improvement"))
        self.assertIn("dd-badge -critical", _rating_badge("poor"))
        self.assertIn("Poor", _rating_badge("poor"))
        # CrUX aliases
        self.assertIn("-pass", _rating_badge("fast"))
        self.assertIn("-critical", _rating_badge("slow"))

    def test_score_bar_colors(self):
        self.assertEqual(_score_bar_mod(95), "-good")
        self.assertEqual(_score_bar_mod(70), "-warn")
        self.assertEqual(_score_bar_mod(42), "-bad")
        bars = _render_score_bars({"mobile_score": 51, "desktop_score": 90, "overall_score": 70})
        self.assertIn("dd-bar-chart__row -warn", bars)  # mobile 51
        self.assertIn("dd-bar-chart__row -good", bars)  # desktop 90
        self.assertIn("dd-bar-chart__row -warn", bars)  # overall 70

    def test_task_rows_prioritized(self):
        rows = build_task_rows(_fixture())
        self.assertGreaterEqual(len(rows), 3)
        self.assertTrue(rows[0]["task_id"].startswith("SPEED-"))
        self.assertEqual(rows[0]["priority"], "P0")
        # WordPress tip attached to render-blocking or image task
        joined = " ".join(r["how"] for r in rows)
        self.assertIn("WordPress", joined)
        # Multi-page URLs present
        urls = {r["page_url"] for r in rows}
        self.assertIn("https://example.com", urls)

    def test_full_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bundle"
            arts = generate_all(_fixture(), out)
            # page1 avg (42+68)/2=55; page2 (55+70)/2 → 62 under banker's round; overall ~58
            self.assertEqual(arts["summary"]["overall_score"], 58)
            for key in (
                "report_markdown",
                "action_plan_markdown",
                "tasks_csv",
                "client_docx",
                "action_plan_docx",
                "dashboard_html",
                "data_json",
            ):
                path = Path(arts[key])
                self.assertTrue(path.exists(), key)
                self.assertGreater(path.stat().st_size, 50, key)
            self.assertTrue((out / "assets" / "css" / "style.min.css").exists())
            html = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn("Prioritized Tasks", html)
            self.assertIn("SPEED-001", html)
            md = (out / "SPEED-AUDIT-REPORT.md").read_text(encoding="utf-8")
            self.assertIn("Core Web Vitals", md)
            self.assertIn("INP", md)
            data = json.loads((out / "data.json").read_text(encoding="utf-8"))
            self.assertEqual(len(data["pages"]), 2)

    def test_insights_in_markdown_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bundle"
            generate_all(_fixture(), out)
            csv_text = (out / "tasks.csv").read_text(encoding="utf-8")
            self.assertIn("what", csv_text.splitlines()[0])
            self.assertIn("why", csv_text.splitlines()[0])
            report = (out / "SPEED-AUDIT-REPORT.md").read_text(encoding="utf-8")
            plan = (out / "ACTION-PLAN.md").read_text(encoding="utf-8")
            for doc in (report, plan):
                self.assertIn("What it means", doc)
                self.assertIn("Why it matters", doc)
                self.assertIn("How to fix", doc)

    def test_insights_in_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bundle"
            generate_all(_fixture(), out)
            from zipfile import ZipFile
            for name in ("SPEED-CLIENT-REPORT.docx", "ACTION-PLAN.docx"):
                with ZipFile(out / name) as zf:
                    xml = zf.read("word/document.xml").decode("utf-8")
                self.assertIn("What it means", xml)
                self.assertIn("Why it matters", xml)
                self.assertIn("How to fix", xml)

    def test_dashboard_expandable_insights(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bundle"
            generate_all(_fixture(), out)
            html_text = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('aria-expanded="false"', html_text)
            self.assertIn("What it means", html_text)
            self.assertIn("Why it matters", html_text)
            self.assertIn("How to fix", html_text)
            self.assertIn("task-insight-detail", html_text)
            self.assertIn("data-filter-text", html_text)


if __name__ == "__main__":
    unittest.main()
