#!/usr/bin/env python3
"""dd-framework component helper CLI.

Provides `list`, `get`, and `validate` subcommands for AI agents and downstream
skills consuming the dd-framework component contracts. JSON output by default;
`--human` flag switches to prose. Validate is strict by default; `--warn`
makes findings non-fatal.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
MANIFEST_PATH = ASSETS / "components.manifest.json"
COMPONENTS_DIR = ASSETS / "components"

UTILITY_PREFIXES = ("dd-u-", "dd-g", "dd-t-", "dd-d-")
KNOWN_UTILITY_CLASSES = {"dd-button", "dd-img", "dd-image"}


def die(msg: str, code: int = 2) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        die(f"manifest not found at {MANIFEST_PATH}")
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"manifest is not valid JSON: {exc}")
        raise


def cmd_list(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    components = {
        name: {
            "summary": data["summary"],
            "file": data["file"],
            "spec": data["spec"],
            "required": data["required"],
            "variants": data["variants"],
            "wraps_in_section": data["wraps_in_section"],
        }
        for name, data in manifest["components"].items()
    }
    if args.human:
        for name, data in components.items():
            req = ", ".join(data["required"]) or "—"
            var = ", ".join(data["variants"]) or "—"
            print(f"{name}")
            print(f"  summary:  {data['summary']}")
            print(f"  required: {req}")
            print(f"  variants: {var}")
            print(f"  wraps:    {'dd-section' if data['wraps_in_section'] else 'standalone'}")
            print()
    else:
        json.dump({"components": components}, sys.stdout, indent=2)
        sys.stdout.write("\n")


def cmd_get(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    comp = manifest["components"].get(args.name)
    if not comp:
        die(f"Unknown component: {args.name}. Run `list` to enumerate.", code=2)
        return  # for type checker
    sections = {"spec", "html", "params"} if args.section == "all" else {args.section}
    result: dict[str, Any] = {"name": args.name, "manifest": comp}
    if "spec" in sections:
        spec_file = COMPONENTS_DIR / comp["spec"]
        if not spec_file.exists():
            die(f"Spec file missing: {spec_file}")
        result["spec_md"] = spec_file.read_text(encoding="utf-8")
    if "html" in sections:
        html_file = COMPONENTS_DIR / comp["file"]
        if not html_file.exists():
            die(f"HTML example missing: {html_file}")
        result["html_example"] = html_file.read_text(encoding="utf-8")
    if "params" in sections:
        result["params"] = {
            "required": comp["required"],
            "variants": comp["variants"],
            "wraps_in_section": comp["wraps_in_section"],
        }
    if args.human:
        print(f"# {args.name}\n")
        print(f"summary: {comp['summary']}\n")
        if "spec_md" in result:
            print("--- SPEC ---\n")
            print(result["spec_md"])
        if "html_example" in result:
            print("\n--- HTML EXAMPLE ---\n")
            print(result["html_example"])
        if "params" in result and "spec_md" not in result:
            print("--- PARAMS ---\n")
            print(json.dumps(result["params"], indent=2))
    else:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")


def _classes(el: Any) -> list[str]:
    val = el.get("class")
    if val is None:
        return []
    return val if isinstance(val, list) else val.split()


def _has_child_with_class(el: Any, cls: str) -> bool:
    return any(cls in _classes(child) for child in el.descendants if getattr(child, "get", None))


def _check_component(comp_name: str, el: Any, findings: list[dict[str, Any]]) -> None:
    block = comp_name
    classes = _classes(el)

    # Structural: most components require __items or __content child
    if comp_name not in {"dd-spacer", "dd-banner"}:
        has_struct = _has_child_with_class(el, f"{block}__items") or _has_child_with_class(el, f"{block}__content")
        if not has_struct:
            findings.append({
                "severity": "warning",
                "component": comp_name,
                "line": getattr(el, "sourceline", None),
                "message": f"Missing {block}__items or {block}__content child element",
            })

    if comp_name == "dd-hero":
        if not el.get("aria-label") and not el.get("aria-labelledby"):
            findings.append({"severity": "error", "component": comp_name,
                             "line": getattr(el, "sourceline", None),
                             "message": "dd-hero requires aria-label or aria-labelledby"})
        if not el.find("h1"):
            findings.append({"severity": "warning", "component": comp_name,
                             "line": getattr(el, "sourceline", None),
                             "message": "dd-hero should contain an <h1>"})
    elif comp_name == "dd-card":
        for img in el.find_all("img"):
            if "alt" not in img.attrs:
                findings.append({"severity": "error", "component": comp_name,
                                 "line": getattr(img, "sourceline", None),
                                 "message": "dd-card <img> missing alt attribute"})
    elif comp_name == "dd-alert":
        role = el.get("role")
        variant_classes = {c for c in classes if c.startswith("-")}
        is_severe = bool(variant_classes & {"-warning", "-error"})
        if is_severe and role != "alert":
            findings.append({"severity": "error", "component": comp_name,
                             "line": getattr(el, "sourceline", None),
                             "message": "Severe alert variant requires role=\"alert\""})
        if role == "alert" and el.get("aria-live"):
            findings.append({"severity": "warning", "component": comp_name,
                             "line": getattr(el, "sourceline", None),
                             "message": "role=\"alert\" implies aria-live; explicit aria-live override is contradictory"})
    elif comp_name == "dd-modal":
        if el.name != "dialog":
            findings.append({"severity": "error", "component": comp_name,
                             "line": getattr(el, "sourceline", None),
                             "message": f"dd-modal must use <dialog>, found <{el.name}>"})
    elif comp_name == "dd-tabs":
        for tab in el.find_all(attrs={"role": "tab"}):
            if tab.name != "button":
                findings.append({"severity": "error", "component": comp_name,
                                 "line": getattr(tab, "sourceline", None),
                                 "message": f"Tab must be <button>, found <{tab.name}>"})
            selected = tab.get("aria-selected")
            if selected not in ("true", "false"):
                findings.append({"severity": "error", "component": comp_name,
                                 "line": getattr(tab, "sourceline", None),
                                 "message": f"Tab aria-selected must be 'true' or 'false', got {selected!r}"})
    elif comp_name == "dd-section":
        if not (el.get("aria-label") or el.get("aria-labelledby")):
            findings.append({"severity": "warning", "component": comp_name,
                             "line": getattr(el, "sourceline", None),
                             "message": "dd-section without aria-label or aria-labelledby is not a labeled landmark"})
    elif comp_name == "dd-cookie-consent":
        role = el.get("role")
        if role == "dialog" and el.get("aria-modal") == "false":
            findings.append({"severity": "error", "component": comp_name,
                             "line": getattr(el, "sourceline", None),
                             "message": "Non-modal cookie banner should use role=\"region\", not role=\"dialog\" with aria-modal=\"false\""})
    elif comp_name == "dd-filmstrip":
        # Detect <figure> used as a caption (no <img> inside)
        for fig in el.find_all("figure"):
            if not fig.find("img"):
                findings.append({"severity": "warning", "component": comp_name,
                                 "line": getattr(fig, "sourceline", None),
                                 "message": "<figure> used without <img> — captions belong in <figcaption>"})


def cmd_validate(args: argparse.Namespace) -> None:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        die("beautifulsoup4 is required for validate. Install: pip install beautifulsoup4", code=2)
        return

    path = Path(args.file)
    if not path.exists():
        die(f"File not found: {path}", code=2)
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    manifest = load_manifest()
    known = set(manifest["components"].keys())
    findings: list[dict[str, Any]] = []

    seen: dict[str, list[Any]] = {}
    for el in soup.find_all(class_=True):
        for c in _classes(el):
            if c in known:
                seen.setdefault(c, []).append(el)

    for comp_name, els in seen.items():
        for el in els:
            _check_component(comp_name, el, findings)

    # Detect unknown dd-* class roots (not utilities, not BEM elements)
    dd_re = re.compile(r"^dd-[a-z][a-z0-9-]*$")
    bem_re = re.compile(r"^dd-[a-z][a-z0-9-]*__")
    for el in soup.find_all(class_=True):
        for c in _classes(el):
            if not dd_re.match(c):
                continue
            if c in known or c in KNOWN_UTILITY_CLASSES:
                continue
            if any(c.startswith(p) for p in UTILITY_PREFIXES):
                continue
            if bem_re.match(c):
                continue
            findings.append({
                "severity": "warning",
                "component": c,
                "line": getattr(el, "sourceline", None),
                "message": f"Unknown dd-* class: {c} (not in manifest)",
            })

    errors = [f for f in findings if f.get("severity") == "error"]
    warnings = [f for f in findings if f.get("severity") == "warning"]

    if args.human:
        print(f"File: {path}")
        comp_list = ", ".join(sorted(seen.keys())) or "(none detected)"
        print(f"Components: {comp_list}")
        print(f"Errors: {len(errors)}  Warnings: {len(warnings)}\n")
        for f in findings:
            sev = f.get("severity", "info").upper()
            line = f.get("line") or "?"
            comp = f.get("component", "")
            comp_str = f" [{comp}]" if comp else ""
            print(f"  {sev}{comp_str} line {line}: {f['message']}")
    else:
        json.dump({
            "file": str(path),
            "components_detected": sorted(seen.keys()),
            "errors": len(errors),
            "warnings": len(warnings),
            "findings": findings,
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")

    if args.warn:
        sys.exit(0)
    sys.exit(1 if errors else 0)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="dd_framework_helper",
                                description="dd-framework component helper. JSON output by default.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp_list = sub.add_parser("list", help="Enumerate available components")
    sp_list.add_argument("--human", action="store_true", help="Human-readable output instead of JSON")
    sp_list.set_defaults(func=cmd_list)

    sp_get = sub.add_parser("get", help="Get spec/html/params for a component")
    sp_get.add_argument("name", help="Component name (e.g. dd-hero)")
    sp_get.add_argument("--section", choices=("spec", "html", "params", "all"), default="all",
                        help="Which content to return (default: all)")
    sp_get.add_argument("--human", action="store_true")
    sp_get.set_defaults(func=cmd_get)

    sp_v = sub.add_parser("validate", help="Validate an HTML file against component contracts")
    sp_v.add_argument("file", help="HTML file path")
    sp_v.add_argument("--warn", action="store_true", help="Exit 0 even when errors found (warn-only mode)")
    sp_v.add_argument("--human", action="store_true")
    sp_v.set_defaults(func=cmd_validate)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
