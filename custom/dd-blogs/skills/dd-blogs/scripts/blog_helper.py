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
import sys


SUBCOMMANDS = {"slug", "dates", "wordcount", "list-blogs", "merge-sitemap"}


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

    # Subcommand dispatch added in later tasks.
    print(f"subcommand {ns.subcommand} not yet implemented", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
