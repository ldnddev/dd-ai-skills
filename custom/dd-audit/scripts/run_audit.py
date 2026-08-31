#!/usr/bin/env python3
"""
dd-audit orchestrator: preflight child plugins, init nested output dirs,
assemble the cover dashboard. Does not run crawl/seo/speed/compare itself.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from assemble import assemble  # noqa: E402
from discover import MODULES, preflight  # noqa: E402

PLUGIN_ROOT = SCRIPT_DIR.parent


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return url
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def domain_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    host = re.sub(r"[^a-z0-9.-]+", "-", host).strip(".-") or "site"
    return host


def default_parent(domain: str, project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return root / "web" / f"{domain}-site-audit-{day}"


def invoke_hint(module: dict, url: str, output_dir: Path) -> str:
    entry = module.get("entry") or ""
    mid = module["id"]
    if mid == "dd-crawl":
        return f'python3 "{entry}" {url} --no-web --output-dir "{output_dir}"'
    if mid == "dd-seo":
        return f'python3 "{entry}" {url} --output-dir "{output_dir}"'
    if mid == "dd-site-speed":
        return f'python3 "{entry}" {url} --output-dir "{output_dir}"'
    if mid == "dd-site-compare":
        return (
            f'python3 "{entry}" --web {url}  # v1: installed only; not invoked'
        )
    return f'python3 "{entry}" {url}'


def init_parent(
    url: str,
    *,
    force: bool = False,
    output_dir: Path | None = None,
    plugin_root: Path | None = None,
    project_root: Path | None = None,
) -> dict:
    url = normalize_url(url)
    if not url:
        raise SystemExit("Provide a primary URL")
    check = preflight(plugin_root)
    if not check["ok"]:
        sys.stderr.write(check["install_help"] or "Child skills missing.\n")
        raise SystemExit(2)

    domain = domain_from_url(url)
    parent = Path(output_dir) if output_dir else default_parent(domain, project_root)
    if parent.exists() and any(parent.iterdir()) and not force:
        raise SystemExit(
            f"Refusing to overwrite existing files in {parent}. "
            "Re-run with --force after confirmation, or choose another --output-dir."
        )
    parent.mkdir(parents=True, exist_ok=True)

    modules_out = []
    for spec, found in zip(MODULES, check["modules"]):
        folder = parent / spec["folder"]
        if spec["run_in_v1"]:
            folder.mkdir(parents=True, exist_ok=True)
        rec = dict(found)
        rec["output_dir"] = str(folder.resolve()) if spec["run_in_v1"] else None
        rec["invoke_hint"] = (
            invoke_hint(found, url, folder) if spec["run_in_v1"] else None
        )
        modules_out.append(rec)

    plan = {
        "primary_url": url,
        "domain": domain,
        "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "parent": str(parent.resolve()),
        "required_installed": [m["id"] for m in MODULES],
        "run": [m["id"] for m in MODULES if m["run_in_v1"]],
        "modules": modules_out,
        "note": (
            "Invoke each run module by following its SKILL.md in full. "
            "Write that skill's bundle into output_dir. "
            "dd-site-compare must be installed but is not run in v1. "
            "Then run: python3 run_audit.py --assemble <parent>"
        ),
    }
    (parent / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    plan["plan_json"] = str((parent / "plan.json").resolve())
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(
        description="dd-audit: preflight child skills, init nested folders, assemble overview"
    )
    parser.add_argument("url", nargs="?", help="Primary site URL (required unless --preflight/--assemble)")
    parser.add_argument("--preflight", action="store_true", help="Only check that the four skills are installed")
    parser.add_argument("--assemble", metavar="DIR", help="Build overview dashboard from nested child folders")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing parent folder")
    parser.add_argument("--output-dir", help="Parent output directory (default web/<domain>-site-audit-YYYY-MM-DD/)")
    args = parser.parse_args()

    if args.preflight:
        result = preflight()
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["ok"] else 2)

    if args.assemble:
        rollup = assemble(Path(args.assemble))
        print(json.dumps(rollup, indent=2))
        return

    if not args.url:
        parser.error("Provide a URL, or --preflight / --assemble DIR")

    out = Path(args.output_dir) if args.output_dir else None
    plan = init_parent(args.url, force=args.force, output_dir=out)
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
