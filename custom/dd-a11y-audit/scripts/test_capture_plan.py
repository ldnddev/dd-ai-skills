#!/usr/bin/env python3
"""Unit tests for annotated screenshot capture plan (no Chromium)."""
import unittest

from capture_a11y_screenshots import IMPACT_ORDER, build_capture_plan


def _violation(rule_id, impact, selector="main .bad"):
    return {
        "id": rule_id,
        "impact": impact,
        "nodes_preview": [{"target": [selector], "html": "<div class='bad'>x</div>"}]
        if selector
        else [{"target": [], "html": ""}],
    }


class TestBuildCapturePlan(unittest.TestCase):
    def test_task_ids_stable_over_all_violations(self):
        results = {
            "violations": [
                _violation("image-alt", "minor"),
                _violation("color-contrast", "critical"),
            ]
        }
        plan = build_capture_plan(results, cap=12)
        self.assertEqual([p["task_id"] for p in plan["all_tasks"]], ["A11Y-001", "A11Y-002"])
        # Imaging order prioritizes critical first among capped image candidates
        self.assertEqual(plan["image_tasks"][0]["task_id"], "A11Y-002")
        self.assertEqual(plan["image_tasks"][0]["rule_id"], "color-contrast")

    def test_cap_limits_image_tasks_not_task_ids(self):
        results = {
            "violations": [
                _violation(f"rule-{i}", "moderate", f".e{i}") for i in range(15)
            ]
        }
        plan = build_capture_plan(results, cap=3)
        self.assertEqual(len(plan["all_tasks"]), 15)
        self.assertEqual(len(plan["image_tasks"]), 3)

    def test_missing_selector_flagged(self):
        results = {"violations": [_violation("html-has-lang", "serious", selector="")]}
        plan = build_capture_plan(results, cap=12)
        self.assertEqual(plan["all_tasks"][0]["selector"], "")
        self.assertEqual(plan["image_tasks"], [])  # not eligible without selector

    def test_impact_order_critical_before_minor(self):
        self.assertLess(IMPACT_ORDER["critical"], IMPACT_ORDER["minor"])

    def test_pins_only_on_image_tasks(self):
        results = {
            "violations": [
                _violation("image-alt", "minor"),
                _violation("color-contrast", "critical"),
                _violation("label", "serious"),
            ]
        }
        plan = build_capture_plan(results, cap=12)
        k = len(plan["image_tasks"])
        self.assertEqual([t["pin"] for t in plan["image_tasks"]], list(range(1, k + 1)))
        for task in plan["all_tasks"]:
            self.assertNotIn("pin", task)

    def test_empty_violations(self):
        plan = build_capture_plan({"violations": []}, cap=12)
        self.assertEqual(plan["all_tasks"], [])
        self.assertEqual(plan["image_tasks"], [])

    def test_nested_axe_target_list(self):
        results = {
            "violations": [
                {
                    "id": "nested-rule",
                    "impact": "serious",
                    "nodes_preview": [
                        {"target": [[".nested"]], "html": "<div class='nested'>x</div>"}
                    ],
                }
            ]
        }
        plan = build_capture_plan(results, cap=12)
        self.assertEqual(plan["all_tasks"][0]["selector"], ".nested")
        self.assertEqual(plan["image_tasks"][0]["selector"], ".nested")

    def test_id_start_offsets_task_ids(self):
        results = {
            "violations": [
                _violation("image-alt", "minor"),
                _violation("color-contrast", "critical"),
            ]
        }
        plan = build_capture_plan(results, cap=12, id_start=5)
        self.assertEqual([p["task_id"] for p in plan["all_tasks"]], ["A11Y-005", "A11Y-006"])
        # Critical still first in image_tasks; IDs remain global
        self.assertEqual(plan["image_tasks"][0]["task_id"], "A11Y-006")
        self.assertEqual(plan["image_tasks"][0]["rule_id"], "color-contrast")


if __name__ == "__main__":
    unittest.main()
