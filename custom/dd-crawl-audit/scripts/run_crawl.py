#!/usr/bin/env python3
"""
dd-crawl orchestrator: crawl site → data.json + CSVs + Framework dashboard.

Default: web/<domain>-crawl-YYYY-MM-DD/ (use --no-web for explicit --output only).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from crawl_core import (  # noqa: E402
    Crawler,
    normalize_start_url,
    summarize,
    to_data_json,
    write_csvs,
)
from generate_dashboard import build_dashboard, default_web_dir  # noqa: E402


def domain_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    host = re.sub(r"[^a-z0-9.-]+", "-", host).strip(".-") or "site"
    return host


def parse_auth(user: str | None, password: str | None, auth: str | None):
    if auth:
        if ":" not in auth:
            raise SystemExit("--auth must be user:password")
        u, p = auth.split(":", 1)
        return u, p
    if user is not None or password is not None:
        return user or "", password or ""
    return None


def main():
    p = argparse.ArgumentParser(description="Crawl a site: map URLs, check status, write dashboard.")
    p.add_argument("base_url", help="Starting URL (https:// optional; will be added)")
    p.add_argument("--exclude-tag", action="append", default=[], metavar="TAG")
    p.add_argument("--exclude-id", action="append", default=[], metavar="ID")
    p.add_argument(
        "--chrome-tag",
        action="append",
        default=None,
        metavar="TAG",
        help="Chrome tags (default: header footer nav)",
    )
    p.add_argument("--max-pages", type=int, default=500)
    p.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Max link depth from start (0=start only). Default: unlimited within max-pages.",
    )
    p.add_argument("--delay", type=float, default=1.0, help="Seconds between page fetches (default 1.0)")
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument(
        "--no-check-external",
        action="store_true",
        help="List external URLs without requesting them",
    )
    p.add_argument(
        "--robots-override",
        action="store_true",
        help="Ignore robots.txt Disallow rules",
    )
    p.add_argument("--user", help="HTTP basic auth username")
    p.add_argument("--password", help="HTTP basic auth password")
    p.add_argument("--auth", help="HTTP basic auth as user:password")
    p.add_argument(
        "--web",
        action="store_true",
        default=True,
        help="Write web/<domain>-crawl-YYYY-MM-DD/ bundle (default)",
    )
    p.add_argument(
        "--no-web",
        action="store_true",
        help="Do not use web/ folder; write next to --output-dir",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: CWD when --no-web, else web/...)",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Deprecated alias: treated as output directory parent file name ignored; use --output-dir",
    )
    args = p.parse_args()

    base = normalize_start_url(args.base_url)
    chrome = args.chrome_tag if args.chrome_tag is not None else ["header", "footer", "nav"]
    auth = parse_auth(args.user, args.password, args.auth)
    use_web = args.web and not args.no_web

    domain = domain_from_url(base)
    if use_web:
        out_dir = default_web_dir(domain, Path.cwd())
    else:
        out_dir = Path(args.output_dir or ".")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Crawling {base} ...", flush=True)
    crawler = Crawler(
        base_url=base,
        exclude_tags=args.exclude_tag,
        exclude_ids=args.exclude_id,
        chrome_tags=chrome,
        max_pages=args.max_pages,
        delay=args.delay,
        timeout=args.timeout,
        check_external=not args.no_check_external,
        depth=args.depth,
        respect_robots=not args.robots_override,
        auth=auth,
    )
    result = crawler.crawl()
    excl_bits = sorted(set(args.exclude_tag) | set(args.exclude_id))
    options = {
        "max_pages": args.max_pages,
        "depth": args.depth,
        "delay": args.delay,
        "check_external": not args.no_check_external,
        "respect_robots": not args.robots_override,
        "chrome_tags": chrome,
        "excluded": ", ".join(excl_bits) if excl_bits else "none",
        "auth": bool(auth),
    }
    result.options = options
    summary = summarize(result)
    data = to_data_json(result, summary, options)

    data_path = out_dir / "data.json"
    all_csv = out_dir / "all-urls.csv"
    broken_csv = out_dir / "broken.csv"
    data_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    write_csvs(data, all_csv, broken_csv)

    index = build_dashboard(
        out_dir,
        data,
        {
            "all_csv": all_csv.name,
            "broken_csv": broken_csv.name,
            "data_json": data_path.name,
        },
    )

    print(
        f"\nDone. {summary['total_urls']} URLs, {summary['pages_crawled']} pages, "
        f"{summary['broken']} broken, {summary['redirects']} redirects.\n"
        f"Bundle: {out_dir.resolve()}\n"
        f"Dashboard: {index.resolve()}",
        flush=True,
    )
    print(
        json.dumps(
            {
                "output_dir": str(out_dir.resolve()),
                "dashboard_html": str(index.resolve()),
                "data_json": str(data_path.resolve()),
                "all_urls_csv": str(all_csv.resolve()),
                "broken_csv": str(broken_csv.resolve()),
                "summary": summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
