#!/usr/bin/env python3
"""
Orchestrate a full page-speed audit and write the client deliverable bundle.

Usage:
    python3 run_speed_audit.py https://example.com
    python3 run_speed_audit.py https://a.com https://b.com
    python3 run_speed_audit.py --urls-file urls.txt
    python3 run_speed_audit.py https://example.com --api-key "$PAGESPEED_API_KEY"
    python3 run_speed_audit.py https://example.com --output-dir reports/acme-speed/
    python3 run_speed_audit.py https://example.com --strategy mobile
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from detect_stack import detect_stack  # noqa: E402
from generate_report import generate_all  # noqa: E402
from pagespeed import get_pagespeed_both  # noqa: E402


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return url
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def domain_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "site"


def slugify(url: str) -> str:
    host = domain_from_url(url)
    path = urlparse(url).path.strip("/")
    if not path:
        return host.replace(".", "-") or "page"
    path = re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-").lower()
    return f"{host.replace('.', '-')}-{path}"[:80]


def default_output_dir(primary_url: str, project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    domain = domain_from_url(primary_url)
    return root / "web" / f"{domain}-speed-audit-{date}"


def load_urls(positional: list[str], urls_file: str | None) -> list[str]:
    urls: list[str] = []
    for u in positional:
        if u:
            urls.append(normalize_url(u))
    if urls_file:
        text = Path(urls_file).read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(normalize_url(line))
    # Dedupe preserving order
    seen = set()
    out = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def audit_one(
    url: str,
    strategies: list[str],
    api_key: str | None,
    skip_stack: bool = False,
) -> dict:
    page = {
        "page_url": url,
        "page_slug": slugify(url),
        "strategies": {},
        "stack": {},
        "error": None,
    }

    if not skip_stack:
        print(f"  [stack] Detecting technology for {url}…", file=sys.stderr)
        page["stack"] = detect_stack(url)

    psi = get_pagespeed_both(url, api_key=api_key, strategies=strategies)
    page["strategies"] = psi.get("strategies") or {}
    if psi.get("error"):
        page["error"] = psi["error"]
    return page


def run_audit(
    urls: list[str],
    strategies: list[str],
    api_key: str | None,
    output_dir: Path,
    skip_stack: bool = False,
) -> dict:
    if not urls:
        raise SystemExit("No URLs provided")

    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    pages = []
    limitations = []
    all_stack_labels: list[str] = []

    for i, url in enumerate(urls):
        print(f"[{i + 1}/{len(urls)}] Auditing {url}", file=sys.stderr)
        page = audit_one(url, strategies=strategies, api_key=api_key, skip_stack=skip_stack)
        pages.append(page)
        for label in (page.get("stack") or {}).get("labels") or []:
            if label not in all_stack_labels:
                all_stack_labels.append(label)
        # Collect errors as limitations
        if page.get("error"):
            limitations.append(f"{url}: {page['error']}")
        for strat, data in (page.get("strategies") or {}).items():
            if data.get("error"):
                limitations.append(f"{url} ({strat}): {data['error']}")
        # Polite delay between pages on free tier
        if i < len(urls) - 1:
            time.sleep(2)

    primary = urls[0]
    results = {
        "metadata": {
            "url": primary,
            "urls": urls,
            "timestamp": timestamp,
            "strategies": strategies,
            "stack_labels": all_stack_labels,
            "tool": "dd-site-speed",
            "version": "1.0.1",
        },
        "pages": pages,
        "limitations": limitations,
    }

    # Convenience: single-page also expose strategies/stack at top level
    if len(pages) == 1:
        results["strategies"] = pages[0].get("strategies")
        results["stack"] = pages[0].get("stack")
        results["error"] = pages[0].get("error")

    artifacts = generate_all(results, output_dir)
    artifacts["urls"] = urls
    artifacts["limitations"] = limitations
    return artifacts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run page speed audit and generate client deliverables"
    )
    parser.add_argument("urls", nargs="*", help="One or more URLs to audit")
    parser.add_argument("--urls-file", help="Text file with one URL per line")
    parser.add_argument(
        "--strategy",
        default="both",
        choices=["mobile", "desktop", "both"],
        help="PSI strategy (default: both mobile and desktop)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("PAGESPEED_API_KEY") or os.environ.get("PSI_API_KEY"),
        help="Google PageSpeed API key (optional; also PAGESPEED_API_KEY env)",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory (default: web/<domain>-speed-audit-YYYY-MM-DD/)",
    )
    parser.add_argument(
        "--max-urls",
        type=int,
        default=25,
        help="Maximum URLs to audit when many are provided (default: 25)",
    )
    parser.add_argument(
        "--skip-stack",
        action="store_true",
        help="Skip technology stack detection",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print artifact paths JSON to stdout",
    )
    args = parser.parse_args()

    urls = load_urls(args.urls, args.urls_file)
    if not urls:
        parser.error("Provide at least one URL or --urls-file")
    if len(urls) > args.max_urls:
        print(
            f"  [run] Truncating URL list from {len(urls)} to {args.max_urls}",
            file=sys.stderr,
        )
        urls = urls[: args.max_urls]

    if args.strategy == "both":
        strategies = ["mobile", "desktop"]
    else:
        strategies = [args.strategy]

    output_dir = Path(args.output_dir) if args.output_dir else default_output_dir(urls[0])

    artifacts = run_audit(
        urls=urls,
        strategies=strategies,
        api_key=args.api_key,
        output_dir=output_dir,
        skip_stack=args.skip_stack,
    )

    if args.json:
        print(json.dumps(artifacts, indent=2))
    else:
        print("Page speed audit complete.")
        print(f"Output: {artifacts['output_dir']}")
        summary = artifacts.get("summary") or {}
        print(
            f"Score: {summary.get('overall_score', 'n/a')}/100 "
            f"(mobile {summary.get('mobile_score', 'n/a')}, "
            f"desktop {summary.get('desktop_score', 'n/a')})"
        )
        print(f"Tasks: {artifacts.get('task_count', 0)}")
        for key in (
            "dashboard_html",
            "report_markdown",
            "action_plan_markdown",
            "tasks_csv",
            "client_docx",
            "action_plan_docx",
            "data_json",
        ):
            if artifacts.get(key):
                print(f"  - {artifacts[key]}")
        if artifacts.get("limitations"):
            print("Limitations:")
            for item in artifacts["limitations"]:
                print(f"  - {item}")


if __name__ == "__main__":
    main()
