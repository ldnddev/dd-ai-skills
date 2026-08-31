#!/usr/bin/env python3
"""Tiny verification harness for dd-site-compare (v1.3+).

Runs an offline HTML fixture for v1.3 competitive signals, then the CLI
against stable public URLs (homepage-only for speed/reliability), asserts
the full contract from references/fields.md, basic types per row, and that
HTML output is generated.

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
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

FIXTURE_HTML = """<!doctype html>
<html lang="en">
<head>
  <title>Acme CRM</title>
  <meta name="description" content="CRM for small contractor teams">
  <meta name="viewport" content="width=device-width">
  <link rel="icon" href="/favicon.ico">
  <link rel="canonical" href="https://acme.example/">
</head>
<body>
  <header class="site-header">
    <nav>
      <a href="/features">Features</a>
      <a href="/pricing">Pricing</a>
      <a href="/integrations">Integrations</a>
      <a href="/blog">Blog</a>
      <a href="/docs">Docs</a>
      <a href="/changelog">Changelog</a>
      <a href="/alternatives">Alternatives</a>
      <a href="/login">Log in</a>
      <a href="/demo" class="btn">Book a demo</a>
      <button class="btn" type="button">Open menu</button>
      <button class="btn" type="button">Resources submenuResources</button>
    </nav>
  </header>
  <main>
    <h1>The CRM built for contractors</h1>
    <p>Win more jobs with proposals, scheduling, and invoicing in one place.</p>
    <a class="cta-primary" href="/signup">Start free trial</a>
    <form action="/signup">
      <input type="email" name="email">
      <input type="text" name="name">
      <input type="hidden" name="csrf" value="x">
      <button type="submit">Get started</button>
    </form>
    <img alt="G2 Leader Summer 2025" src="/g2.png">
    <a href="https://www.g2.com/products/acme">Read G2 reviews</a>
    <p>Plans from $49/month. SOC 2 Type II certified.</p>
  </main>
</body>
</html>
"""


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
        "h1_text", "hero_subhead", "nav_labels", "primary_cta", "cta_texts",
        "cta_count", "form_field_count", "offer_type", "pricing_visible",
        "trust_signals", "page_types",
    ]
    for m in must:
        if m not in seen:
            out.append(m)
    return out


def _check_positioning_fixture() -> str:
    import compare_websites as cw

    parser = cw.ParsedHTML()
    parser.feed(FIXTURE_HTML)
    signals = cw.derive_competitive_signals(parser, FIXTURE_HTML)
    expected = {
        "h1_text": "The CRM built for contractors",
        "hero_subhead": "Win more jobs with proposals, scheduling, and invoicing in one place.",
        "primary_cta": "Book a demo",
        "offer_type": "demo",
        "form_field_count": 2,
        "pricing_visible": True,
    }
    for key, want in expected.items():
        got = signals.get(key)
        if got != want:
            return f"fixture {key}: expected {want!r}, got {got!r}"

    nav = signals["nav_labels"]
    for label in ("Features", "Pricing", "Integrations", "Blog", "Docs", "Changelog", "Alternatives"):
        if label not in nav:
            return f"fixture nav_labels missing {label!r}: {nav!r}"

    cta_texts = signals["cta_texts"]
    for label in ("Book a demo", "Start free trial"):
        if label not in cta_texts:
            return f"fixture cta_texts missing {label!r}: {cta_texts!r}"
    if "Log in" in cta_texts:
        return f"fixture cta_texts should skip login: {cta_texts!r}"
    for noise in ("Open menu", "Resources submenuResources"):
        if noise in cta_texts:
            return f"fixture cta_texts should skip chrome control {noise!r}: {cta_texts!r}"

    page_types = set(signals["page_types"])
    missing_types = {
        "pricing", "features", "integrations", "alternatives", "blog", "docs", "changelog"
    } - page_types
    if missing_types:
        return f"fixture page_types missing {sorted(missing_types)}: {signals['page_types']!r}"

    trust = set(signals["trust_signals"])
    if "G2" not in trust or "SOC 2" not in trust:
        return f"fixture trust_signals expected G2 and SOC 2, got {signals['trust_signals']!r}"

    if int(signals["cta_count"]) != len(cta_texts):
        return f"fixture cta_count {signals['cta_count']!r} != len(cta_texts) {len(cta_texts)}"

    return ""


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

    fixture_error = _check_positioning_fixture()
    if fixture_error:
        print(fixture_error)
        return 1
    print("OK: offline positioning fixture")

    res = run_cli(args.urls, workers=args.workers)
    payload = res["json"]
    results = payload.get("results", [])
    field_order = payload.get("field_order", [])

    if not results:
        print("no results")
        return 1
    if payload.get("primary_url") != results[0]["URL"]:
        print(f"primary_url {payload.get('primary_url')!r} != first row {results[0]['URL']!r}")
        return 1

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
        if not isinstance(row.get("nav_labels", []), list):
            print("nav_labels not list")
            return 1
        if not isinstance(row.get("cta_texts", []), list):
            print("cta_texts not list")
            return 1
        if not isinstance(row.get("cta_count", 0), int):
            print("cta_count not int")
            return 1
        if not isinstance(row.get("form_field_count", 0), int):
            print("form_field_count not int")
            return 1
        if not isinstance(row.get("offer_type", ""), str):
            print("offer_type not str")
            return 1
        if not isinstance(row.get("pricing_visible", False), bool):
            print("pricing_visible not bool")
            return 1
        if not isinstance(row.get("trust_signals", []), list):
            print("trust_signals not list")
            return 1
        if not isinstance(row.get("page_types", []), list):
            print("page_types not list")
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
