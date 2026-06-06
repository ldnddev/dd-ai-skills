#!/usr/bin/env python3
"""Tiny verification harness for dd-site-compare (v1.1+).

Runs the CLI against stable public URLs (homepage-only for speed/reliability),
asserts the full contract from references/fields.md (plus new v1.1 fields),
basic types per row, and that HTML output is generated.

Usage:
  python3 scripts/verify.py
  python3 scripts/verify.py --urls https://example.com https://example.org
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "compare_websites.py"
FIELDS_MD = HERE.parent / "references" / "fields.md"
DEFAULT_URLS = [
    "https://example.com",
    "https://example.org",
    "https://www.iana.org",
]


def load_contract_fields() -> List[str]:
    text = FIELDS_MD.read_text(encoding="utf-8")
    # grab the bullet list under the first heading or the | table
    fields: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            f = line[2:].strip()
            if f and not f.startswith("`"):
                fields.append(f)
        elif line.startswith("| ") and " | " in line:
            # table row: first column after |
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts and parts[0] not in ("Field", "---"):
                fields.append(parts[0])
    # de-dup while preserving order, include the explicit v1.1 ones even if parsing misses
    seen = set()
    out: List[str] = []
    for f in fields:
        if f not in seen:
            seen.add(f)
            out.append(f)
    # ensure the full known set (defensive)
    must = [
        "URL", "final_url", "redirected", "status_code", "response_time",
        "page_size", "total_page_load_size", "resource_count", "js_file_count",
        "css_file_count", "largest_item", "trackers", "title", "meta_description",
        "h1_count", "h2_count", "h3_count", "image_count", "images_missing_alt",
        "link_count", "external_link_count", "technologies", "keywords",
        "mobile_responsive", "has_favicon", "has_canonical", "json_ld_count",
        "word_count", "server", "powered_by", "error",
    ]
    for m in must:
        if m not in seen:
            out.append(m)
    return out


def run_cli(urls: List[str], *, skip_resources: bool = True, workers: int = 2) -> dict:
    with tempfile.TemporaryDirectory() as td:
        out_html = Path(td) / "dash.html"
        out_json = Path(td) / "dash.json"
        cmd = [
            sys.executable, str(SCRIPT),
            "--workers", str(workers),
            "--output", str(out_html),
            "--json-output", str(out_json),
        ]
        if skip_resources:
            cmd.append("--skip-resources")
        else:
            cmd.extend(["--max-resources", "20"])
        cmd.extend(urls)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode != 0:
            print("CLI STDERR:", proc.stderr, file=sys.stderr)
            raise SystemExit(f"CLI failed (rc={proc.returncode})")
        data = json.loads(out_json.read_text(encoding="utf-8"))
        html = out_html.read_text(encoding="utf-8")
        return {"json": data, "html": html, "stdout": proc.stdout}


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", nargs="*", default=DEFAULT_URLS, help="Override test URLs")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args(argv)

    contract = load_contract_fields()
    print(f"Contract fields ({len(contract)}): {', '.join(contract[:6])} ...")

    res = run_cli(args.urls, workers=args.workers)
    payload = res["json"]
    results = payload.get("results", [])
    field_order = payload.get("field_order", [])

    # 1. field_order contains the full contract
    missing = [f for f in contract if f not in field_order]
    if missing:
        print("MISSING from field_order:", missing)
        return 1

    # 2. every row has every field + basic type sanity
    for i, row in enumerate(results):
        for f in contract:
            if f not in row:
                print(f"Row {i} missing field {f}")
                return 1
        # types (lenient but useful)
        if row.get("status_code") is not None and not isinstance(row.get("status_code"), (int, type(None))):
            print("bad status_code type")
            return 1
        if not isinstance(row.get("trackers", []), list):
            print("trackers not list")
            return 1
        if not isinstance(row.get("has_favicon", False), bool):
            print("has_favicon not bool")
            return 1
        if row.get("word_count", 0) is not None and not isinstance(row.get("word_count"), int):
            print("word_count not int")
            return 1

    # 3. HTML was produced and contains key strings
    if "Website Comparison Dashboard" not in res["html"]:
        print("HTML missing title")
        return 1
    if "__DASHBOARD_DATA_JSON__" in res["html"]:
        print("HTML placeholder not replaced")
        return 1

    print(f"OK: {len(results)} rows, {len(field_order)} fields in order, HTML generated.")
    print("All verifications passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
