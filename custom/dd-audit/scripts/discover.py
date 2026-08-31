#!/usr/bin/env python3
"""Locate installed dd-audit child plugins. Does not run them."""

from __future__ import annotations

import json
import os
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# v1 requires all four installed. Only crawl / seo / speed are invoked.
MODULES = (
    {
        "id": "dd-crawl",
        "folder": "crawl",
        "run_in_v1": True,
        "env": "DD_CRAWL_ROOT",
        "dir_names": ("dd-crawl-audit", "dd-crawl"),
        "dir_prefix": "dd-crawl-audit-",
        "skill_md": ("skills/dd-crawl/SKILL.md", "SKILL.md"),
        "entry": ("scripts/run_crawl.py",),
        "marketplace": "dd-crawl@dd-skills",
        "codex_install": "bash custom/dd-crawl-audit/install.sh",
    },
    {
        "id": "dd-seo",
        "folder": "seo",
        "run_in_v1": True,
        "env": "DD_SEO_ROOT",
        "dir_names": ("dd-seo-audit", "dd-seo"),
        "dir_prefix": "dd-seo-audit-",
        "skill_md": (
            "skills/dd-seo/SKILL.md",
            "SKILL.md",
        ),
        "entry": (
            "skills/dd-seo/scripts/generate_report.py",
            "scripts/generate_report.py",
        ),
        "marketplace": "dd-seo@dd-skills",
        "codex_install": "bash custom/dd-seo-audit/install.sh",
    },
    {
        "id": "dd-site-speed",
        "folder": "speed",
        "run_in_v1": True,
        "env": "DD_SITE_SPEED_ROOT",
        "dir_names": ("dd-site-speed-audit", "dd-site-speed"),
        "dir_prefix": "dd-site-speed-audit-",
        "skill_md": ("skills/dd-site-speed/SKILL.md", "SKILL.md"),
        "entry": ("scripts/run_speed_audit.py",),
        "marketplace": "dd-site-speed@dd-skills",
        "codex_install": "bash custom/dd-site-speed-audit/install.sh",
    },
    {
        "id": "dd-site-compare",
        "folder": "compare",
        "run_in_v1": False,
        "env": "DD_SITE_COMPARE_ROOT",
        "dir_names": ("dd-site-compare-audit", "dd-site-compare"),
        "dir_prefix": "dd-site-compare-audit-",
        "skill_md": (
            "skills/dd-site-compare/SKILL.md",
            "SKILL.md",
        ),
        "entry": (
            "skills/dd-site-compare/scripts/compare_websites.py",
            "scripts/compare_websites.py",
        ),
        "marketplace": "dd-site-compare@dd-skills",
        "codex_install": "bash custom/dd-site-compare-audit/install.sh",
    },
)


def _first_file(root: Path, rels: tuple[str, ...]) -> Path | None:
    for rel in rels:
        path = root / rel
        if path.is_file():
            return path
    return None


def _looks_like_module(root: Path, spec: dict) -> bool:
    return _first_file(root, spec["skill_md"]) is not None


def search_roots(plugin_root: Path | None = None) -> list[Path]:
    root = (plugin_root or PLUGIN_ROOT).resolve()
    out: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        path = path.resolve()
        if path.is_dir() and path not in seen:
            seen.add(path)
            out.append(path)

    add(root.parent)
    for parent in root.parents:
        marketplace = parent / ".claude-plugin" / "marketplace.json"
        custom = parent / "custom"
        if marketplace.is_file() and custom.is_dir():
            add(custom)
            break

    grok = Path(os.environ.get("GROK_HOME") or (Path.home() / ".grok")).expanduser()
    add(grok / "installed-plugins")
    add(grok / "skills")
    codex = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser()
    add(codex / "skills")
    add(Path.home() / ".claude" / "plugins")
    extra = os.environ.get("DD_AUDIT_SEARCH_ROOT")
    if extra:
        add(Path(extra).expanduser())
    return out


def _scan_dir(base: Path, spec: dict) -> Path | None:
    names = set(spec["dir_names"])
    prefix = spec["dir_prefix"]
    try:
        children = list(base.iterdir())
    except OSError:
        return None
    exact = []
    prefixed = []
    for child in children:
        if not child.is_dir():
            continue
        if child.name in names and _looks_like_module(child, spec):
            exact.append(child)
        elif child.name.startswith(prefix) and _looks_like_module(child, spec):
            prefixed.append(child)
    if exact:
        return sorted(exact, key=lambda p: p.name)[0]
    if prefixed:
        return sorted(prefixed, key=lambda p: p.name)[0]
    if _looks_like_module(base, spec) and base.name in names:
        return base
    return None


def find_module(spec: dict, plugin_root: Path | None = None) -> dict:
    env_val = os.environ.get(spec["env"])
    candidates: list[Path] = []
    if env_val:
        candidates.append(Path(env_val).expanduser())
    for base in search_roots(plugin_root):
        hit = _scan_dir(base, spec)
        if hit:
            candidates.append(hit)
    for cand in candidates:
        if not cand.is_dir():
            continue
        skill_md = _first_file(cand, spec["skill_md"])
        entry = _first_file(cand, spec["entry"])
        if skill_md and entry:
            return {
                "id": spec["id"],
                "folder": spec["folder"],
                "run_in_v1": spec["run_in_v1"],
                "found": True,
                "usable": True,
                "root": str(cand.resolve()),
                "skill_md": str(skill_md.resolve()),
                "entry": str(entry.resolve()),
                "error": None,
                "marketplace": spec["marketplace"],
                "codex_install": spec["codex_install"],
            }
        if skill_md and not entry:
            return {
                "id": spec["id"],
                "folder": spec["folder"],
                "run_in_v1": spec["run_in_v1"],
                "found": True,
                "usable": False,
                "root": str(cand.resolve()),
                "skill_md": str(skill_md.resolve()),
                "entry": None,
                "error": f"Found {spec['id']} but missing entry script ({', '.join(spec['entry'])})",
                "marketplace": spec["marketplace"],
                "codex_install": spec["codex_install"],
            }
    return {
        "id": spec["id"],
        "folder": spec["folder"],
        "run_in_v1": spec["run_in_v1"],
        "found": False,
        "usable": False,
        "root": None,
        "skill_md": None,
        "entry": None,
        "error": f"{spec['id']} is not installed (no SKILL.md on the search path)",
        "marketplace": spec["marketplace"],
        "codex_install": spec["codex_install"],
    }


def discover_all(plugin_root: Path | None = None) -> list[dict]:
    return [find_module(spec, plugin_root) for spec in MODULES]


def install_help(modules: list[dict] | None = None) -> str:
    missing = [
        m for m in (modules or [])
        if isinstance(m, dict) and m.get("id") and not m.get("usable")
    ]
    if missing:
        market_lines = "\n".join(
            f"/plugin install {m['marketplace']}" for m in missing
        )
        codex_lines = "\n".join(f"  {m['codex_install']}" for m in missing)
    else:
        market_lines = "\n".join(
            f"/plugin install {m['marketplace']}" for m in MODULES
        )
        codex_lines = "\n".join(f"  {m['codex_install']}" for m in MODULES)
    source = missing if missing else list(MODULES)
    needed = ", ".join(m["id"] for m in source)
    return (
        f"dd-audit requires these plugins installed and usable: "
        f"dd-crawl, dd-seo, dd-site-speed, dd-site-compare.\n"
        f"Missing or unusable: {needed}\n\n"
        f"Claude Code / marketplace:\n"
        f"/plugin marketplace add ldnddev/dd-ai-skills\n"
        f"{market_lines}\n\n"
        f"Codex (from the dd-ai-skills repo):\n"
        f"{codex_lines}\n\n"
        f"Optional overrides: DD_CRAWL_ROOT, DD_SEO_ROOT, DD_SITE_SPEED_ROOT, "
        f"DD_SITE_COMPARE_ROOT (plugin root directories).\n"
    )


def preflight(plugin_root: Path | None = None) -> dict:
    modules = discover_all(plugin_root)
    ok = all(m["usable"] for m in modules)
    return {
        "ok": ok,
        "modules": modules,
        "install_help": None if ok else install_help(modules),
    }


if __name__ == "__main__":
    result = preflight()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 2)
