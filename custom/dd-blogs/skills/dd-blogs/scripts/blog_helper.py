#!/usr/bin/env python3
"""blog_helper.py — deterministic ops for the dd-blogs skill.

Subcommands:
  slug <title>
  dates <YYYY-mm-dd>
  wordcount <file>
  list-blogs <blog_root>
  merge-sitemap <sitemap.xml> <slug> <YYYY-mm-dd>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime


SUBCOMMANDS = {"slug", "dates", "wordcount", "list-blogs", "merge-sitemap"}


def cmd_slug(args: list[str]) -> int:
    if not args or not args[0].strip():
        print("slug: title required and must not be empty", file=sys.stderr)
        return 2
    title = args[0]
    normalized = unicodedata.normalize("NFKD", title)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    no_apostrophes = re.sub(r"['’]", "", lowered)
    hyphenated = re.sub(r"[^a-z0-9]+", "-", no_apostrophes)
    stripped = hyphenated.strip("-")
    if not stripped:
        print("slug: title produced empty slug after normalization", file=sys.stderr)
        return 2
    print(stripped)
    return 0


def cmd_dates(args: list[str]) -> int:
    if not args:
        print("dates: YYYY-mm-dd argument required", file=sys.stderr)
        return 2
    try:
        d = datetime.strptime(args[0], "%Y-%m-%d").date()
    except ValueError as e:
        print(f"dates: invalid date format ({e})", file=sys.stderr)
        return 2
    out = {
        "mmddYYYY": d.strftime("%m%d%Y"),
        "mm-dd-YYYY": d.strftime("%m-%d-%Y"),
        "YYYY-mm-dd": d.strftime("%Y-%m-%d"),
        "long": f"{d.strftime('%B')} {d.day}, {d.year}",
    }
    print(json.dumps(out))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="blog_helper.py", add_help=True)
    parser.add_argument("subcommand", nargs="?", help="one of: " + ", ".join(sorted(SUBCOMMANDS)))
    parser.add_argument("args", nargs=argparse.REMAINDER)

    ns = parser.parse_args(argv)
    if not ns.subcommand:
        parser.print_usage(sys.stderr)
        return 2
    if ns.subcommand not in SUBCOMMANDS:
        print(f"unknown subcommand: {ns.subcommand}", file=sys.stderr)
        return 2

    dispatch = {
        "slug": cmd_slug,
        "dates": cmd_dates,
    }
    handler = dispatch.get(ns.subcommand)
    if handler is None:
        print(f"subcommand {ns.subcommand} not yet implemented", file=sys.stderr)
        return 2
    return handler(ns.args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
