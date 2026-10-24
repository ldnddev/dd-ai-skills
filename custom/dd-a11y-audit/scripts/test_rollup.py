#!/usr/bin/env python3
"""Sitewide rollup of repeated chrome and template findings."""
import unittest

from run_a11y_audit import is_chrome_finding, prepare_findings


def _page(url, slug, violations):
    return {
        "page_url": url,
        "page_slug": slug,
        "violations": violations,
    }


def _violation(rule_id, impact, selector, html="<a>x</a>"):
    return {
        "id": rule_id,
        "impact": impact,
        "description": rule_id,
        "help": "fix",
        "wcag_tags": ["wcag143"] if rule_id == "color-contrast" else ["wcag111"],
        "nodes_count": 1,
        "nodes_preview": [{"target": [selector], "html": html}],
    }


class TestChromeDetection(unittest.TestCase):
    def test_header_footer_nav_and_cookie_are_chrome(self):
        self.assertTrue(is_chrome_finding("header a.logo", ""))
        self.assertTrue(is_chrome_finding("footer .links a", ""))
        self.assertTrue(is_chrome_finding("nav.primary a", ""))
        self.assertTrue(is_chrome_finding("#onetrust-banner", ""))
        self.assertTrue(is_chrome_finding(".cookie-consent", ""))
        self.assertTrue(is_chrome_finding("[role='banner'] a", "<a>Home</a>"))

    def test_main_content_is_not_chrome(self):
        self.assertFalse(is_chrome_finding("main .card a", "<a class='card'>Read</a>"))
        self.assertFalse(is_chrome_finding(".navigation-note", "<p>See the navigation note</p>"))


class TestPrepareFindings(unittest.TestCase):
    def test_repeated_chrome_and_template_roll_up_once(self):
        pages = [
            _page("https://ex.com/", "home", [
                _violation("color-contrast", "serious", "header a.logo", "<a class='logo'>Home</a>"),
                _violation("image-alt", "critical", "main img.hero", "<img class='hero'>"),
                _violation("label", "moderate", "main form label", "<label></label>"),
            ]),
            _page("https://ex.com/about", "about", [
                _violation("color-contrast", "critical", "header a.logo", "<a class='logo'>Home</a>"),
                _violation("image-alt", "critical", "main img.hero", "<img class='hero'>"),
                _violation("button-name", "serious", "main button.buy", "<button></button>"),
            ]),
        ]
        sitewide = prepare_findings(pages)

        self.assertEqual(len(sitewide), 2)
        self.assertEqual(sitewide[0]["scope"], "sitewide-chrome")
        self.assertEqual(sitewide[0]["rule_id"], "color-contrast")
        self.assertEqual(sitewide[0]["impact"], "critical")
        self.assertEqual(sitewide[0]["task_id"], "A11Y-001")
        self.assertEqual(sitewide[0]["page_count"], 2)
        self.assertTrue(sitewide[0]["visual"])
        self.assertEqual(sitewide[0]["representative"]["page_slug"], "home")

        self.assertEqual(sitewide[1]["scope"], "sitewide-template")
        self.assertEqual(sitewide[1]["rule_id"], "image-alt")
        self.assertEqual(sitewide[1]["task_id"], "A11Y-002")
        self.assertFalse(sitewide[1]["visual"])

        home = pages[0]["violations"]
        about = pages[1]["violations"]
        self.assertTrue(home[0]["sitewide_representative"])
        self.assertTrue(home[0]["needs_crop"])
        self.assertEqual(home[0]["task_id"], "A11Y-001")
        self.assertFalse(about[0]["needs_crop"])
        self.assertEqual(about[0]["rollup_task_id"], "A11Y-001")
        self.assertNotIn("task_id", about[0])
        self.assertTrue(home[1]["sitewide_representative"])
        self.assertEqual(home[1]["task_id"], "A11Y-002")
        self.assertFalse(about[1]["needs_crop"])
        self.assertEqual(home[2]["task_id"], "A11Y-003")
        self.assertEqual(about[2]["task_id"], "A11Y-004")

    def test_single_page_chrome_stays_on_the_page(self):
        pages = [
            _page("https://ex.com/", "home", [
                _violation("color-contrast", "serious", "header a", "<a>Home</a>"),
            ]),
            _page("https://ex.com/about", "about", [
                _violation("color-contrast", "serious", "main h1", "<h1>About</h1>"),
            ]),
        ]
        sitewide = prepare_findings(pages)
        self.assertEqual(sitewide, [])
        self.assertEqual(pages[0]["violations"][0]["task_id"], "A11Y-001")
        self.assertNotIn("rollup_task_id", pages[0]["violations"][0])
        self.assertEqual(pages[1]["violations"][0]["task_id"], "A11Y-002")


if __name__ == "__main__":
    unittest.main()
