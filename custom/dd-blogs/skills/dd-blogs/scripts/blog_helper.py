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
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


SUBCOMMANDS = {
    "slug", "dates", "wordcount", "list-blogs", "merge-sitemap", "split-sections",
    "list-dd-components", "validate-body",
}


def _find_dd_framework_helper() -> Path | None:
    """Locate dd_framework_helper.py across common install locations.

    Returns the helper path or None if dd-framework is not installed.
    Probes (in order): CODEX_HOME, default Codex install, Claude Code plugin cache,
    sibling worktree layout, repo layout. Returns the first match.
    """
    import os
    candidates: list[Path] = []
    rel = Path("skills/dd-framework/scripts/dd_framework_helper.py")

    if codex := os.environ.get("CODEX_HOME"):
        candidates.append(Path(codex) / "skills/dd-framework/scripts/dd_framework_helper.py")
    candidates.append(Path.home() / ".codex/skills/dd-framework/scripts/dd_framework_helper.py")

    # Walk up from this file looking for a sibling dd-framework
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidates.append(parent / "dd-framework" / rel)
        candidates.append(parent / "custom" / "dd-framework" / rel)

    # Claude Code plugin cache
    candidates.append(Path.home() / ".claude/plugins/cache/dd-skills/dd-framework" / rel)

    for c in candidates:
        if c.exists():
            return c
    return None


def cmd_list_dd_components(args: list[str]) -> int:
    """Forward to dd_framework_helper.py list. Returns JSON or a graceful-degrade message."""
    import subprocess
    helper = _find_dd_framework_helper()
    if helper is None:
        print(json.dumps({
            "available": False,
            "reason": "dd-framework not installed. Install via /plugin install dd-framework@dd-skills or bash install.sh.",
            "components": [],
        }))
        return 0
    extra = ["--human"] if args and args[0] == "--human" else []
    try:
        result = subprocess.run([sys.executable, str(helper), "list", *extra],
                                capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"list-dd-components: dd-framework helper failed: {exc.stderr}", file=sys.stderr)
        return 2
    sys.stdout.write(result.stdout)
    return 0


def cmd_validate_body(args: list[str]) -> int:
    """Validate a blog body HTML file against dd-framework component contracts.

    Graceful degrade: if dd-framework is not installed, returns a JSON note and
    exits 0 — the blog can still be written, just without component validation.
    Otherwise forwards to dd_framework_helper.py validate in --warn mode (we
    surface issues as warnings; blog flow shouldn't hard-fail on a-framework
    component misuse).
    """
    import subprocess
    if not args:
        print("validate-body: file path required", file=sys.stderr)
        return 2
    path = Path(args[0])
    if not path.exists():
        print(f"validate-body: file not found: {path}", file=sys.stderr)
        return 2
    helper = _find_dd_framework_helper()
    if helper is None:
        print(json.dumps({
            "available": False,
            "reason": "dd-framework not installed; skipping component validation.",
            "file": str(path),
            "findings": [],
        }))
        return 0
    try:
        result = subprocess.run(
            [sys.executable, str(helper), "validate", str(path), "--warn"],
            capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        print(f"validate-body: failed to invoke dd-framework helper: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(result.stdout)
    if result.returncode not in (0, 1):
        sys.stderr.write(result.stderr)
        return result.returncode
    return 0


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


WC_MIN = 1800
WC_MAX = 2200


def cmd_wordcount(args: list[str]) -> int:
    if not args:
        print("wordcount: file path required", file=sys.stderr)
        return 2
    path = Path(args[0])
    if not path.exists():
        print(f"wordcount: file not found: {path}", file=sys.stderr)
        return 2
    if path.is_dir():
        print(f"wordcount: path is a directory, not a file: {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    stripped = re.sub(r"<[^>]+>", " ", text)
    words = stripped.split()
    count = len(words)
    out = {
        "count": count,
        "in_range": WC_MIN <= count <= WC_MAX,
        "min": WC_MIN,
        "max": WC_MAX,
    }
    print(json.dumps(out))
    return 0


TITLE_RE = re.compile(r"<title>\s*ldnddev,\s*LLC\.\s*Insights\s*\|\s*(.+?)</title>", re.IGNORECASE | re.DOTALL)
CANONICAL_RE = re.compile(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', re.IGNORECASE)
DATE_PUBLISHED_RE = re.compile(r'"datePublished"\s*:\s*"([^"]+)"')


def _normalize_date(raw: str) -> str | None:
    """Accept mm-dd-YYYY or YYYY-mm-dd; return YYYY-mm-dd."""
    for fmt in ("%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _parse_blog_index(html: str, dir_name: str) -> dict | None:
    title_m = TITLE_RE.search(html)
    canon_m = CANONICAL_RE.search(html)
    date_m = DATE_PUBLISHED_RE.search(html)
    if not (title_m and canon_m and date_m):
        return None
    canonical = canon_m.group(1).rstrip("/")
    slug = canonical.rsplit("/", 1)[-1]
    if not slug:
        slug = dir_name
    date = _normalize_date(date_m.group(1).strip())
    if not date:
        return None
    return {
        "slug": slug,
        "title": title_m.group(1).strip(),
        "date": date,
    }


def cmd_list_blogs(args: list[str]) -> int:
    if not args:
        print("list-blogs: blog_root required", file=sys.stderr)
        return 2
    root = Path(args[0])
    if not root.exists():
        print(f"list-blogs: no such directory: {root}", file=sys.stderr)
        return 2
    entries = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        index = child / "index.html"
        if not index.exists():
            continue
        parsed = _parse_blog_index(index.read_text(encoding="utf-8"), child.name)
        if parsed is None:
            continue
        parsed["path"] = str(child.resolve())
        entries.append(parsed)
    print(json.dumps(entries))
    return 0


SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap-0.9"
LOC_PREFIX = "https://ldnddev.com/blog/"


def cmd_merge_sitemap(args: list[str]) -> int:
    if len(args) < 3:
        print("merge-sitemap: <sitemap.xml> <slug> <YYYY-mm-dd> required", file=sys.stderr)
        return 2
    sitemap_path, slug, date_raw = args[0], args[1], args[2]
    sm = Path(sitemap_path)
    if not sm.exists():
        print(f"merge-sitemap: file not found: {sm}", file=sys.stderr)
        return 2
    try:
        d = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError:
        print(f"merge-sitemap: invalid date: {date_raw} (expected YYYY-mm-dd)", file=sys.stderr)
        return 2

    new_loc = f"{LOC_PREFIX}{slug}/"
    lastmod = f"{d.strftime('%Y-%m-%d')}T12:13:00+00:00"

    ET.register_namespace("", SITEMAP_NS)
    try:
        tree = ET.parse(sm)
    except ET.ParseError as e:
        print(f"merge-sitemap: failed to parse XML: {e}", file=sys.stderr)
        return 2
    root = tree.getroot()
    ns = {"sm": SITEMAP_NS}

    for url in root.findall("sm:url", ns):
        loc = url.find("sm:loc", ns)
        if loc is not None and loc.text == new_loc:
            return 0

    backup = sm.with_suffix(sm.suffix + ".bak")
    backup.write_text(sm.read_text(encoding="utf-8"), encoding="utf-8")

    new_url = ET.Element(f"{{{SITEMAP_NS}}}url")
    loc_el = ET.SubElement(new_url, f"{{{SITEMAP_NS}}}loc")
    loc_el.text = new_loc
    lastmod_el = ET.SubElement(new_url, f"{{{SITEMAP_NS}}}lastmod")
    lastmod_el.text = lastmod
    priority_el = ET.SubElement(new_url, f"{{{SITEMAP_NS}}}priority")
    priority_el.text = "0.80"

    urls = list(root.findall("sm:url", ns))
    insert_idx = len(list(root))
    for i, url in enumerate(urls):
        loc = url.find("sm:loc", ns)
        if loc is not None and loc.text and loc.text > new_loc:
            insert_idx = list(root).index(url)
            break
    root.insert(insert_idx, new_url)

    ET.indent(tree, space="  ")
    tree.write(sm, xml_declaration=True, encoding="UTF-8")
    return 0


def cmd_split_sections(args: list[str]) -> int:
    """Split a blog body HTML file at each <h2> boundary.

    Returns a JSON array of chunks. Each chunk contains one <h2> plus all
    sibling content up to (but not including) the next <h2>. Any content
    appearing before the first <h2> becomes its own leading chunk so the
    caller can decide what to do with it.
    """
    if not args:
        print("split-sections: file path required", file=sys.stderr)
        return 2
    path = Path(args[0])
    if not path.exists():
        print(f"split-sections: file not found: {path}", file=sys.stderr)
        return 2
    if path.is_dir():
        print(f"split-sections: path is a directory, not a file: {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8").strip()
    parts = re.split(r"(?=<h2[\s>])", text)
    chunks = [p.strip() for p in parts if p.strip()]
    print(json.dumps(chunks))
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
        "wordcount": cmd_wordcount,
        "list-blogs": cmd_list_blogs,
        "merge-sitemap": cmd_merge_sitemap,
        "split-sections": cmd_split_sections,
        "list-dd-components": cmd_list_dd_components,
        "validate-body": cmd_validate_body,
    }
    handler = dispatch.get(ns.subcommand)
    if handler is None:
        print(f"subcommand {ns.subcommand} not yet implemented", file=sys.stderr)
        return 2
    return handler(ns.args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
