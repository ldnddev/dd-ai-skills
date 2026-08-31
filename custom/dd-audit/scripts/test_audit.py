#!/usr/bin/env python3
"""Unit tests for dd-audit (no network, no child skill execution)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from assemble import assemble
from discover import PLUGIN_ROOT, preflight
from run_audit import domain_from_url, init_parent, normalize_url


def _write(path: Path, text: str = "ok\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fake_children(parent: Path) -> None:
    _write(parent / "dd-crawl-audit" / "skills" / "dd-crawl" / "SKILL.md")
    _write(parent / "dd-crawl-audit" / "scripts" / "run_crawl.py")
    _write(parent / "dd-seo-audit" / "skills" / "dd-seo" / "SKILL.md")
    _write(parent / "dd-seo-audit" / "skills" / "dd-seo" / "scripts" / "generate_report.py")
    _write(parent / "dd-site-speed-audit" / "skills" / "dd-site-speed" / "SKILL.md")
    _write(parent / "dd-site-speed-audit" / "scripts" / "run_speed_audit.py")
    _write(parent / "dd-site-compare-audit" / "skills" / "dd-site-compare" / "SKILL.md")
    _write(
        parent / "dd-site-compare-audit" / "skills" / "dd-site-compare" / "scripts" / "compare_websites.py"
    )


class TestDomain(unittest.TestCase):
    def test_strip_www_and_scheme(self):
        self.assertEqual(domain_from_url("https://www.ldnddev.com/path"), "ldnddev.com")
        self.assertTrue(normalize_url("ldnddev.com").startswith("https://"))


class TestPreflight(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def _isolate(self, tmp: Path) -> None:
        os.environ["GROK_HOME"] = str(tmp / "grok")
        os.environ["CODEX_HOME"] = str(tmp / "codex")
        os.environ["HOME"] = str(tmp / "home")
        os.environ.pop("DD_CRAWL_ROOT", None)
        os.environ.pop("DD_SEO_ROOT", None)
        os.environ.pop("DD_SITE_SPEED_ROOT", None)
        os.environ.pop("DD_SITE_COMPARE_ROOT", None)
        os.environ.pop("DD_AUDIT_SEARCH_ROOT", None)
        (tmp / "home").mkdir()

    def test_repo_siblings_are_usable(self):
        result = preflight(PLUGIN_ROOT)
        self.assertTrue(result["ok"], result.get("install_help"))
        ids = {m["id"] for m in result["modules"]}
        self.assertEqual(ids, {"dd-crawl", "dd-seo", "dd-site-speed", "dd-site-compare"})
        self.assertTrue(all(m["usable"] for m in result["modules"]))

    def test_missing_skills_fail_with_install_help(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            self._isolate(tmp)
            plugin = tmp / "dd-audit"
            plugin.mkdir()
            result = preflight(plugin)
            self.assertFalse(result["ok"])
            help_text = result["install_help"] or ""
            self.assertIn("/plugin install dd-crawl@dd-skills", help_text)
            self.assertIn("/plugin install dd-seo@dd-skills", help_text)
            self.assertIn("/plugin install dd-site-speed@dd-skills", help_text)
            self.assertIn("/plugin install dd-site-compare@dd-skills", help_text)

    def test_compare_required_even_if_others_present(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            self._isolate(tmp)
            parent = tmp / "custom"
            parent.mkdir()
            plugin = parent / "dd-audit"
            plugin.mkdir()
            _write(parent / "dd-crawl-audit" / "skills" / "dd-crawl" / "SKILL.md")
            _write(parent / "dd-crawl-audit" / "scripts" / "run_crawl.py")
            _write(parent / "dd-seo-audit" / "skills" / "dd-seo" / "SKILL.md")
            _write(parent / "dd-seo-audit" / "skills" / "dd-seo" / "scripts" / "generate_report.py")
            _write(parent / "dd-site-speed-audit" / "skills" / "dd-site-speed" / "SKILL.md")
            _write(parent / "dd-site-speed-audit" / "scripts" / "run_speed_audit.py")
            result = preflight(plugin)
            self.assertFalse(result["ok"])
            compare = next(m for m in result["modules"] if m["id"] == "dd-site-compare")
            self.assertFalse(compare["usable"])
            self.assertIn("dd-site-compare", result["install_help"])


class TestInitAndAssemble(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def _isolate_with_children(self, tmp: Path) -> Path:
        os.environ["GROK_HOME"] = str(tmp / "grok")
        os.environ["CODEX_HOME"] = str(tmp / "codex")
        os.environ["HOME"] = str(tmp / "home")
        (tmp / "home").mkdir()
        parent = tmp / "custom"
        parent.mkdir()
        plugin = parent / "dd-audit"
        plugin.mkdir()
        _fake_children(parent)
        return plugin

    def test_init_writes_plan_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            plugin = self._isolate_with_children(tmp)
            out = tmp / "web" / "example.com-site-audit-test"
            plan = init_parent(
                "https://www.example.com",
                output_dir=out,
                plugin_root=plugin,
                project_root=tmp,
            )
            self.assertTrue((out / "plan.json").is_file())
            self.assertTrue((out / "crawl").is_dir())
            self.assertTrue((out / "seo").is_dir())
            self.assertTrue((out / "speed").is_dir())
            self.assertEqual(plan["run"], ["dd-crawl", "dd-seo", "dd-site-speed"])
            self.assertIn("dd-site-compare", plan["required_installed"])
            crawl = next(m for m in plan["modules"] if m["id"] == "dd-crawl")
            self.assertIn("--no-web", crawl["invoke_hint"])
            self.assertIn("/crawl", crawl["invoke_hint"])
            with self.assertRaises(SystemExit) as raised:
                init_parent(
                    "https://www.example.com",
                    output_dir=out,
                    plugin_root=plugin,
                    project_root=tmp,
                )
            self.assertIn("Refusing to overwrite", str(raised.exception))

    def test_assemble_continue_on_error_does_not_rewrite_child_html(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            parent = tmp / "bundle"
            parent.mkdir()
            (parent / "plan.json").write_text(
                json.dumps({"primary_url": "https://example.com", "domain": "example.com"}),
                encoding="utf-8",
            )
            crawl = parent / "crawl"
            crawl.mkdir()
            child_html = "<html><body>CRAWL-ORIGINAL</body></html>"
            (crawl / "index.html").write_text(child_html, encoding="utf-8")
            (crawl / "data.json").write_text(
                json.dumps(
                    {
                        "summary": {
                            "pages_crawled": 4,
                            "total_urls": 12,
                            "broken": 2,
                            "redirects": 1,
                        }
                    }
                ),
                encoding="utf-8",
            )
            speed = parent / "speed"
            speed.mkdir()
            (speed / "index.html").write_text("<html>speed</html>", encoding="utf-8")
            (speed / "data.json").write_text(
                json.dumps(
                    {
                        "strategies": {
                            "mobile": {"performance_score": 41},
                            "desktop": {"performance_score": 88},
                        }
                    }
                ),
                encoding="utf-8",
            )
            seo = parent / "seo"
            seo.mkdir()
            (seo / "error.txt").write_text("generate_report failed: timeout\n", encoding="utf-8")

            rollup = assemble(parent)
            self.assertEqual(rollup["ok_count"], 2)
            self.assertEqual(rollup["failed_count"], 1)
            self.assertTrue((parent / "index.html").is_file())
            cover = (parent / "index.html").read_text(encoding="utf-8")
            self.assertIn("CRAWL-ORIGINAL", (crawl / "index.html").read_text(encoding="utf-8"))
            self.assertNotIn("CRAWL-ORIGINAL", cover)
            self.assertIn("href='crawl/index.html'", cover)
            self.assertIn("41", cover)
            self.assertIn("generate_report failed", cover)
            self.assertIn("dd-site-compare is required", cover)
            seo_mod = next(m for m in rollup["modules"] if m["id"] == "dd-seo")
            self.assertEqual(seo_mod["status"], "failed")
            self.assertIsNone(seo_mod["href"])


if __name__ == "__main__":
    unittest.main()
