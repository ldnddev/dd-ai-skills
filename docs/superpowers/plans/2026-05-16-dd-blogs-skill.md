# dd-blogs Skill Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `custom/dd-blogs/` from a guidelines-only skill into an executable workflow that produces a complete drop-in blog post for ldnddev.com from a guided Q&A intake.

**Architecture:** Single fat SKILL.md drives a 7-phase workflow (intake → discovery → plan → draft → review gate → assemble → summary). A stdlib-only Python helper (`blog_helper.py`) handles deterministic operations (slug, date formats, word count, blog discovery, sitemap merge). Existing reference templates are preserved; one new `social-template.md` added.

**Tech Stack:** Python 3 stdlib, pytest, bash, Claude Code SKILL format, markdown, HTML5.

**Spec:** [`docs/superpowers/specs/2026-05-16-dd-blogs-skill-design.md`](../specs/2026-05-16-dd-blogs-skill-design.md)

---

## File Structure

**Create:**
- `custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py` — CLI helper (one responsibility per subcommand)
- `custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py` — pytest suite
- `custom/dd-blogs/skills/dd-blogs/references/social-template.md` — social post format spec

**Modify:**
- `custom/dd-blogs/skills/dd-blogs/SKILL.md` — full rewrite
- `custom/dd-blogs/.claude-plugin/plugin.json` — version bump
- `custom/dd-blogs/install.sh` — copy scripts dir
- `custom/dd-blogs/README.md` — rewrite for new flow

**Preserve unchanged:**
- `custom/dd-blogs/skills/dd-blogs/references/blog-header.md`
- `custom/dd-blogs/skills/dd-blogs/references/blog-markup.md`
- `custom/dd-blogs/skills/dd-blogs/references/ldjson-template.md`
- `custom/dd-blogs/skills/dd-blogs/references/sitemap-blog.md`

---

## Task 1: Scaffold scripts directory and helper skeleton

**Files:**
- Create: `custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py`
- Create: `custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py`

- [ ] **Step 1: Create scripts dir**

```bash
mkdir -p custom/dd-blogs/skills/dd-blogs/scripts
```

- [ ] **Step 2: Write failing CLI smoke test**

Create `custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py`:

```python
"""Tests for blog_helper.py."""
import json
import subprocess
import sys
from pathlib import Path

HELPER = Path(__file__).parent / "blog_helper.py"


def run(*args):
    """Run helper, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(HELPER), *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def test_no_args_prints_usage_and_exits_nonzero():
    code, _, err = run()
    assert code != 0
    assert "usage" in err.lower()


def test_unknown_subcommand_exits_nonzero():
    code, _, err = run("nonsense")
    assert code != 0
    assert "unknown" in err.lower() or "invalid" in err.lower()
```

- [ ] **Step 3: Run test, expect fail (helper missing)**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v
```

Expected: FAIL — `blog_helper.py` does not exist.

- [ ] **Step 4: Implement helper skeleton**

Create `custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py`:

```python
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
```

- [ ] **Step 5: Make executable**

```bash
chmod +x custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py
```

- [ ] **Step 6: Run tests, expect pass**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v
```

Expected: both tests PASS.

- [ ] **Step 7: Commit**

```bash
git add custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py
git commit -m "feat(dd-blogs): scaffold blog_helper CLI skeleton"
```

---

## Task 2: Implement `slug` subcommand

**Files:**
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py`
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py`

- [ ] **Step 1: Write failing tests for slug**

Append to `test_blog_helper.py`:

```python
def test_slug_basic():
    code, out, _ = run("slug", "Hello World")
    assert code == 0
    assert out.strip() == "hello-world"


def test_slug_punctuation_stripped():
    code, out, _ = run("slug", "Don't Repeat Yourself: A Guide!")
    assert code == 0
    assert out.strip() == "dont-repeat-yourself-a-guide"


def test_slug_collapses_multiple_hyphens():
    code, out, _ = run("slug", "foo --- bar___baz")
    assert code == 0
    assert out.strip() == "foo-bar-baz"


def test_slug_strips_leading_trailing_hyphens():
    code, out, _ = run("slug", "  ---hello---  ")
    assert code == 0
    assert out.strip() == "hello"


def test_slug_unicode_normalized():
    code, out, _ = run("slug", "Café résumé — naïve")
    assert code == 0
    assert out.strip() == "cafe-resume-naive"


def test_slug_leading_numbers_kept():
    code, out, _ = run("slug", "2026 Year in Review")
    assert code == 0
    assert out.strip() == "2026-year-in-review"


def test_slug_empty_title_errors():
    code, _, err = run("slug", "")
    assert code != 0
    assert "empty" in err.lower() or "required" in err.lower()
```

- [ ] **Step 2: Run tests, expect fail**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v -k slug
```

Expected: 7 FAIL.

- [ ] **Step 3: Implement `slug` in helper**

In `blog_helper.py`, add after the `SUBCOMMANDS` constant:

```python
import re
import unicodedata


def cmd_slug(args: list[str]) -> int:
    if not args or not args[0].strip():
        print("slug: title required and must not be empty", file=sys.stderr)
        return 2
    title = args[0]
    normalized = unicodedata.normalize("NFKD", title)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", hyphenated)
    stripped = collapsed.strip("-")
    if not stripped:
        print("slug: title produced empty slug after normalization", file=sys.stderr)
        return 2
    print(stripped)
    return 0
```

Replace the dispatch block in `main()`:

```python
    # Subcommand dispatch added in later tasks.
    print(f"subcommand {ns.subcommand} not yet implemented", file=sys.stderr)
    return 2
```

with:

```python
    dispatch = {
        "slug": cmd_slug,
    }
    handler = dispatch.get(ns.subcommand)
    if handler is None:
        print(f"subcommand {ns.subcommand} not yet implemented", file=sys.stderr)
        return 2
    return handler(ns.args)
```

- [ ] **Step 4: Run tests, expect pass**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v
```

Expected: 9 PASS (2 skeleton + 7 slug).

- [ ] **Step 5: Commit**

```bash
git add custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py
git commit -m "feat(dd-blogs): implement slug subcommand"
```

---

## Task 3: Implement `dates` subcommand

**Files:**
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py`
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py`

- [ ] **Step 1: Write failing tests for dates**

Append to `test_blog_helper.py`:

```python
def test_dates_basic():
    code, out, _ = run("dates", "2026-05-16")
    assert code == 0
    data = json.loads(out)
    assert data == {
        "mmddYYYY": "05162026",
        "mm-dd-YYYY": "05-16-2026",
        "YYYY-mm-dd": "2026-05-16",
        "long": "May 16, 2026",
    }


def test_dates_january_pads():
    code, out, _ = run("dates", "2026-01-01")
    assert code == 0
    data = json.loads(out)
    assert data["mmddYYYY"] == "01012026"
    assert data["long"] == "January 1, 2026"


def test_dates_leap_year_valid():
    code, out, _ = run("dates", "2024-02-29")
    assert code == 0
    data = json.loads(out)
    assert data["YYYY-mm-dd"] == "2024-02-29"


def test_dates_invalid_format_errors():
    code, _, err = run("dates", "05/16/2026")
    assert code != 0
    assert "invalid" in err.lower() or "format" in err.lower()


def test_dates_invalid_day_errors():
    code, _, err = run("dates", "2026-02-30")
    assert code != 0
```

- [ ] **Step 2: Run tests, expect fail**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v -k dates
```

Expected: 5 FAIL.

- [ ] **Step 3: Implement `dates`**

In `blog_helper.py`, add:

```python
import json
from datetime import datetime


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
```

Register in dispatch:

```python
    dispatch = {
        "slug": cmd_slug,
        "dates": cmd_dates,
    }
```

- [ ] **Step 4: Run tests, expect pass**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v
```

Expected: 14 PASS.

- [ ] **Step 5: Commit**

```bash
git add custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py
git commit -m "feat(dd-blogs): implement dates subcommand"
```

---

## Task 4: Implement `wordcount` subcommand

**Files:**
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py`
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py`

- [ ] **Step 1: Write failing tests for wordcount**

Append to `test_blog_helper.py`:

```python
import tempfile


def _write_tmp(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False)
    f.write(content)
    f.close()
    return f.name


def test_wordcount_strips_html_tags():
    path = _write_tmp("<p>Hello <strong>brave</strong> new world</p>")
    code, out, _ = run("wordcount", path)
    assert code == 0
    data = json.loads(out)
    assert data["count"] == 4


def test_wordcount_in_range_true():
    body = "word " * 1900
    path = _write_tmp(f"<p>{body}</p>")
    code, out, _ = run("wordcount", path)
    data = json.loads(out)
    assert data["count"] == 1900
    assert data["in_range"] is True
    assert data["min"] == 1800
    assert data["max"] == 2200


def test_wordcount_below_range():
    body = "word " * 1799
    path = _write_tmp(f"<p>{body}</p>")
    code, out, _ = run("wordcount", path)
    data = json.loads(out)
    assert data["count"] == 1799
    assert data["in_range"] is False


def test_wordcount_above_range():
    body = "word " * 2201
    path = _write_tmp(f"<p>{body}</p>")
    code, out, _ = run("wordcount", path)
    data = json.loads(out)
    assert data["count"] == 2201
    assert data["in_range"] is False


def test_wordcount_lower_boundary_inclusive():
    body = "word " * 1800
    path = _write_tmp(f"<p>{body}</p>")
    code, out, _ = run("wordcount", path)
    data = json.loads(out)
    assert data["in_range"] is True


def test_wordcount_upper_boundary_inclusive():
    body = "word " * 2200
    path = _write_tmp(f"<p>{body}</p>")
    code, out, _ = run("wordcount", path)
    data = json.loads(out)
    assert data["in_range"] is True


def test_wordcount_missing_file_errors():
    code, _, err = run("wordcount", "/nonexistent/path.html")
    assert code != 0
    assert "not found" in err.lower() or "no such" in err.lower()
```

- [ ] **Step 2: Run tests, expect fail**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v -k wordcount
```

Expected: 7 FAIL.

- [ ] **Step 3: Implement `wordcount`**

In `blog_helper.py`, add:

```python
from pathlib import Path

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
```

Register in dispatch:

```python
    dispatch = {
        "slug": cmd_slug,
        "dates": cmd_dates,
        "wordcount": cmd_wordcount,
    }
```

- [ ] **Step 4: Run tests, expect pass**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v
```

Expected: 21 PASS.

- [ ] **Step 5: Commit**

```bash
git add custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py
git commit -m "feat(dd-blogs): implement wordcount subcommand"
```

---

## Task 5: Implement `list-blogs` subcommand

**Files:**
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py`
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py`

- [ ] **Step 1: Write failing tests for list-blogs**

Append to `test_blog_helper.py`:

```python
SAMPLE_BLOG_HTML = """<!doctype html>
<html>
<head>
<title>ldnddev, LLC. Insights | Why Drupal Still Wins in 2026</title>
<link rel="canonical" href="https://www.ldnddev.com/blog/why-drupal-still-wins-in-2026" />
<script type="application/ld+json">
{
  "@type": "BlogPosting",
  "datePublished": "03-15-2026"
}
</script>
</head>
<body></body>
</html>"""


def test_list_blogs_empty_dir():
    with tempfile.TemporaryDirectory() as tmp:
        code, out, _ = run("list-blogs", tmp)
        assert code == 0
        assert json.loads(out) == []


def test_list_blogs_finds_valid_blog():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        blog = root / "why-drupal-still-wins-in-2026"
        blog.mkdir()
        (blog / "index.html").write_text(SAMPLE_BLOG_HTML)
        code, out, _ = run("list-blogs", tmp)
        assert code == 0
        entries = json.loads(out)
        assert len(entries) == 1
        e = entries[0]
        assert e["slug"] == "why-drupal-still-wins-in-2026"
        assert e["title"] == "Why Drupal Still Wins in 2026"
        assert e["date"] == "2026-03-15"
        assert e["path"].endswith("why-drupal-still-wins-in-2026")


def test_list_blogs_skips_dirs_without_index():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "no-index").mkdir()
        code, out, _ = run("list-blogs", tmp)
        assert code == 0
        assert json.loads(out) == []


def test_list_blogs_skips_malformed_index():
    with tempfile.TemporaryDirectory() as tmp:
        blog = Path(tmp) / "broken"
        blog.mkdir()
        (blog / "index.html").write_text("<html>no metadata</html>")
        code, out, _ = run("list-blogs", tmp)
        assert code == 0
        assert json.loads(out) == []


def test_list_blogs_root_missing_errors():
    code, _, err = run("list-blogs", "/nonexistent/path")
    assert code != 0
    assert "not found" in err.lower() or "no such" in err.lower()
```

- [ ] **Step 2: Run tests, expect fail**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v -k list_blogs
```

Expected: 5 FAIL.

- [ ] **Step 3: Implement `list-blogs`**

In `blog_helper.py`, add:

```python
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
```

Register in dispatch:

```python
    dispatch = {
        "slug": cmd_slug,
        "dates": cmd_dates,
        "wordcount": cmd_wordcount,
        "list-blogs": cmd_list_blogs,
    }
```

- [ ] **Step 4: Run tests, expect pass**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v
```

Expected: 26 PASS.

- [ ] **Step 5: Commit**

```bash
git add custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py
git commit -m "feat(dd-blogs): implement list-blogs subcommand"
```

---

## Task 6: Implement `merge-sitemap` subcommand

**Files:**
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py`
- Modify: `custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py`

- [ ] **Step 1: Write failing tests for merge-sitemap**

Append to `test_blog_helper.py`:

```python
EMPTY_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap-0.9">
</urlset>
"""

POPULATED_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap-0.9">
  <url>
    <loc>https://ldnddev.com/blog/aaa-first-post/</loc>
    <lastmod>2026-01-01T12:13:00+00:00</lastmod>
    <priority>0.80</priority>
  </url>
  <url>
    <loc>https://ldnddev.com/blog/zzz-last-post/</loc>
    <lastmod>2026-04-01T12:13:00+00:00</lastmod>
    <priority>0.80</priority>
  </url>
</urlset>
"""


def test_merge_sitemap_into_empty():
    with tempfile.TemporaryDirectory() as tmp:
        sm = Path(tmp) / "sitemap.xml"
        sm.write_text(EMPTY_SITEMAP)
        code, _, err = run("merge-sitemap", str(sm), "new-post", "2026-05-16")
        assert code == 0, err
        content = sm.read_text()
        assert "https://ldnddev.com/blog/new-post/" in content
        assert "2026-05-16T12:13:00+00:00" in content


def test_merge_sitemap_sorted_insert():
    with tempfile.TemporaryDirectory() as tmp:
        sm = Path(tmp) / "sitemap.xml"
        sm.write_text(POPULATED_SITEMAP)
        code, _, err = run("merge-sitemap", str(sm), "middle-post", "2026-02-15")
        assert code == 0, err
        content = sm.read_text()
        idx_aaa = content.index("aaa-first-post")
        idx_mid = content.index("middle-post")
        idx_zzz = content.index("zzz-last-post")
        assert idx_aaa < idx_mid < idx_zzz


def test_merge_sitemap_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        sm = Path(tmp) / "sitemap.xml"
        sm.write_text(POPULATED_SITEMAP)
        run("merge-sitemap", str(sm), "new-post", "2026-05-16")
        content_first = sm.read_text()
        run("merge-sitemap", str(sm), "new-post", "2026-05-16")
        content_second = sm.read_text()
        assert content_first.count("/blog/new-post/") == 1
        assert content_second.count("/blog/new-post/") == 1


def test_merge_sitemap_creates_backup():
    with tempfile.TemporaryDirectory() as tmp:
        sm = Path(tmp) / "sitemap.xml"
        sm.write_text(POPULATED_SITEMAP)
        bak = sm.with_suffix(".xml.bak")
        run("merge-sitemap", str(sm), "new-post", "2026-05-16")
        assert bak.exists()
        assert bak.read_text() == POPULATED_SITEMAP


def test_merge_sitemap_missing_file_errors():
    code, _, err = run("merge-sitemap", "/nonexistent/sitemap.xml", "x", "2026-05-16")
    assert code != 0
    assert "not found" in err.lower() or "no such" in err.lower()


def test_merge_sitemap_bad_date_errors():
    with tempfile.TemporaryDirectory() as tmp:
        sm = Path(tmp) / "sitemap.xml"
        sm.write_text(EMPTY_SITEMAP)
        code, _, err = run("merge-sitemap", str(sm), "x", "05/16/2026")
        assert code != 0
```

- [ ] **Step 2: Run tests, expect fail**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v -k merge_sitemap
```

Expected: 6 FAIL.

- [ ] **Step 3: Implement `merge-sitemap`**

In `blog_helper.py`, add:

```python
import xml.etree.ElementTree as ET

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

    backup = sm.with_suffix(sm.suffix + ".bak")
    backup.write_text(sm.read_text(encoding="utf-8"), encoding="utf-8")

    ET.register_namespace("", SITEMAP_NS)
    tree = ET.parse(sm)
    root = tree.getroot()
    ns = {"sm": SITEMAP_NS}

    for url in root.findall("sm:url", ns):
        loc = url.find("sm:loc", ns)
        if loc is not None and loc.text == new_loc:
            return 0

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
```

Register in dispatch:

```python
    dispatch = {
        "slug": cmd_slug,
        "dates": cmd_dates,
        "wordcount": cmd_wordcount,
        "list-blogs": cmd_list_blogs,
        "merge-sitemap": cmd_merge_sitemap,
    }
```

- [ ] **Step 4: Run tests, expect pass**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v
```

Expected: 32 PASS.

- [ ] **Step 5: Commit**

```bash
git add custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py
git commit -m "feat(dd-blogs): implement merge-sitemap subcommand"
```

---

## Task 7: Add social-template.md reference

**Files:**
- Create: `custom/dd-blogs/skills/dd-blogs/references/social-template.md`

- [ ] **Step 1: Create social-template.md**

```markdown
# Social Posts Template

Use this format for `social.md` output. Produce 3 distinct angles per platform. Replace all `[placeholder]` values.

```
# Social Posts — [SEO_Title]

URL: https://ldnddev.com/blog/[blog_slug]/

## X.com

Each post ≤280 characters including URL. Conversational, hook-driven. No hashtag spam (max 2).

### Post 1 — Hook angle
[Open with a sharp observation or contrarian framing. End with URL.]

### Post 2 — Stat/insight angle
[Lead with a specific number or insight from the post. End with URL.]

### Post 3 — Question/engagement angle
[Ask the reader a question that the post answers. End with URL.]

## LinkedIn

Each post 1200–2000 characters. Professional, value-dense, line-broken for skim.

### Post 1 — Problem-first
[Open with the problem the post solves. Build through 3-4 short paragraphs. Close with URL + soft CTA.]

### Post 2 — Lessons-learned
[Frame as "what we learned from X". First-person plural. 3-4 takeaways. URL + CTA.]

### Post 3 — Direct CTA
[Open with the outcome. State who it's for. Provide URL early. Close with explicit invitation to talk.]
```

## Placeholder Reference

| Placeholder | Source |
|---|---|
| `[SEO_Title]` | Blog title |
| `[blog_slug]` | kebab-case slug from helper |
```

- [ ] **Step 2: Commit**

```bash
git add custom/dd-blogs/skills/dd-blogs/references/social-template.md
git commit -m "feat(dd-blogs): add social-template reference"
```

---

## Task 8: Rewrite SKILL.md to drive the 7-phase workflow

**Files:**
- Modify: `custom/dd-blogs/skills/dd-blogs/SKILL.md`

- [ ] **Step 1: Replace SKILL.md contents**

Overwrite `custom/dd-blogs/skills/dd-blogs/SKILL.md` with:

```markdown
---
name: dd-blogs
description: Generate a complete drop-in blog post for ldnddev.com from a guided Q&A intake. Produces index.html (head + body + ld+json), hero images or prompts, social.md (3 X + 3 LinkedIn), and sitemap entry. Apply ldnddev brand tone (60% professional / 20% conversational / 20% personality). Use for all blog writing tasks — new posts, scheduled cron generation, draft revisions.
---

# dd-blogs — ldnddev Blog Writing Workflow

## Role

Senior copywriter for ldnddev, LLC — a custom website, Drupal, and WordPress development agency. Every post builds trust, clarity, and confidence while feeling human.

## Tone Formula

- **60% professional** — credible, competent, not robotic
- **20% conversational** — approachable, lowers intimidation
- **20% personality** — honest, slightly opinionated, a little fun

### Do
- Lead with outcomes and benefits; tech details come second
- Sound confident using proof, not bragging
- Be educational and transparent
- Align content with a CTA for possible client leads

### Don't
- Buzzwords or jargon ("synergistic digital ecosystems")
- Oversell or sound salesy
- Overexplain technical details

**Good:** "Your site will load fast, rank well, and convert visitors into customers."
**Bad:** "We leverage modern frameworks and optimized build pipelines."

## Writing Standards

- **Word count:** 1800–2200 words
- **Structure:** `<h2>` to open each new section
- **Sign-off:** Always end with "Until next time, Jared Lyvers"
- **Voice:** First-person plural ("we") for ldnddev; second-person ("you") for the reader

## Workflow

Execute these 7 phases in order. The helper script `scripts/blog_helper.py` provides deterministic operations.

### Phase 1 — Intake (ask one question per turn)

1. Topic (one-liner)
2. Target audience (decision-makers, developers, marketing leads, etc.)
3. Key takeaway + CTA goal (one sentence main point + desired reader action)
4. Output root path (default `./blog`)
5. Existing blog root path (optional — enables cross-link scan and duplicate detection)
6. Publish date (default today, YYYY-mm-dd)
7. Keyword hints (optional, comma-separated)

### Phase 2 — Discovery

- If existing blog root provided, run:
  ```bash
  python3 scripts/blog_helper.py list-blogs <existing_root>
  ```
  Store the returned slug/title/date list for cross-link selection.

- Generate candidate slug from the working title:
  ```bash
  python3 scripts/blog_helper.py slug "<draft title>"
  ```

- If the slug collides with an existing entry, ask the user to refine the title. Repeat.

- Run WebSearch on `<topic> <keyword hints>` (mandatory). Fetch the top 3-5 results via WebFetch. Summarize key facts inline. Cite sources internally; do not insert source URLs into the blog body unless quoting directly.

### Phase 3 — Plan

- Finalize SEO_Title, SEO_Description (150-160 chars), SEO_Keywords (5-10 comma-separated), final slug.
- Plan H2 sections (5-8 typical).
- From the `list-blogs` output, pick 2-3 contextually relevant existing posts to cross-link inline.

### Phase 4 — Draft

- Write the full blog body HTML.
- `<h2>` per section. First-person plural for ldnddev, second-person for reader.
- Insert cross-link anchors inline: `<a href="/blog/<slug>/">…</a>`.
- End with sign-off: `Until next time, Jared Lyvers`.
- Write the draft body to a temp file and run:
  ```bash
  python3 scripts/blog_helper.py wordcount /tmp/blog-draft.html
  ```
  Record count and `in_range` flag.

### Phase 5 — Review gate

Print to chat in this order:

```
SEO_Title: ...
SEO_Description: ...
SEO_Keywords: ...
Slug: ...
Publish date: YYYY-mm-dd
Word count: NNNN (in_range: true|false; min 1800, max 2200)

--- Draft body ---
<HTML body>
```

If `in_range` is false, prepend a one-line warning.

Wait for the user to reply "approved" or request edits. Loop: apply edits, re-count, re-display, until approved.

### Phase 6 — Assemble + write

Run dates expansion:
```bash
python3 scripts/blog_helper.py dates <YYYY-mm-dd>
```
Use the returned formats:
- `mmddYYYY` → `blog_date` (deliverable label)
- `mm-dd-YYYY` → ld+json `datePublished` / `dateModified`
- `YYYY-mm-dd` → sitemap
- `long` → blog body byline `By Jared Lyvers, ldnddev — May 16, 2026`

Substitute placeholders across the three reference templates:
- `references/blog-header.md` → fills `[SEO_Title]`, `[SEO_Description]`, `[SEO_Keywords]`, `[blog_slug]`
- `references/blog-markup.md` → fills `[hero_title]` (first 3 words of SEO_Title), `[hero_copy]` (remainder), `[blog_slug]`, `[blog_draft_date]` (long format), `[blog_draft]` (body HTML), `[blog_draft_end]` ("Until next time, Jared Lyvers")
- `references/ldjson-template.md` → fills `[SEO_Title]`, `[blog_slug]`, `[blog_date]` (mm-dd-YYYY), `[SEO_Description]`, `[SEO_Keywords]`

Assemble single `index.html`:
- Document type: `<!doctype html>` then `<html lang="en">`
- `<head>` from blog-header template with the ld+json `<script>` block inserted before `</head>`
- `<body>` containing the blog-markup template

Write to `<output_root>/<slug>/index.html`.

Hero images:
- Check available tools. If an image-gen tool (MCP or built-in) is available, invoke with both prompts and save:
  - `hero-lg.webp` at 1920×1080
  - `hero-sm.webp` at 1024×576
- If unavailable, write `hero-prompts.md` containing both prompts, sizes, and filename targets.

Social posts:
- Use `references/social-template.md` as the format. Generate 3 X posts + 3 LinkedIn posts with distinct angles per platform.
- Write to `<output_root>/<slug>/social.md`.

Sitemap entry:
- Always write `<output_root>/<slug>/sitemap-entry.xml` using the sitemap-blog template (substituting `[blog_slug]` and `[blog_date]` in YYYY-mm-dd).
- If the user provided a sitemap path in intake, also run:
  ```bash
  python3 scripts/blog_helper.py merge-sitemap <sitemap.xml> <slug> <YYYY-mm-dd>
  ```

Output directory collision:
- If `<output_root>/<slug>/` already exists, prompt the user: overwrite, choose a new slug, or abort.

### Phase 7 — Summary

Print:
- Absolute paths of every file written
- Sitemap merge status (merged into `<path>` / snippet only)
- Word count + in_range flag

## Deliverables Checklist

Every blog post produces:

- [ ] `SEO_Title`, `SEO_Description` (150-160 chars), `SEO_Keywords` (5-10)
- [ ] `blog_date` (mmddYYYY), `blog_slug` (kebab-case), URL (`https://ldnddev.com/blog/<slug>/`)
- [ ] `<output_root>/<slug>/index.html` (head + body + ld+json)
- [ ] `<output_root>/<slug>/hero-lg.webp` + `hero-sm.webp` (or `hero-prompts.md` fallback)
- [ ] `<output_root>/<slug>/social.md` (3 X + 3 LinkedIn)
- [ ] `<output_root>/<slug>/sitemap-entry.xml`
- [ ] Sitemap merge (if path given)

## Reference Files

- `references/blog-header.md` — HTML `<head>` template
- `references/blog-markup.md` — HTML body template
- `references/ldjson-template.md` — schema.org BlogPosting
- `references/sitemap-blog.md` — sitemap `<url>` snippet
- `references/social-template.md` — social post format
- `scripts/blog_helper.py` — deterministic operations (slug, dates, wordcount, list-blogs, merge-sitemap)

## Error Handling

- Slug collision → ask user to refine title
- Existing blog path invalid → warn once, skip cross-links, continue
- WebSearch fails → ask: proceed without research / retry / abort
- Word count out of range → warn, show draft anyway, user decides
- Sitemap path invalid → write snippet only, warn
- Image gen fails → fall back to hero-prompts.md
- Output slug dir exists → prompt: overwrite / new slug / abort
- Helper non-zero exit → surface stderr, abort phase, ask user how to proceed
```

- [ ] **Step 2: Commit**

```bash
git add custom/dd-blogs/skills/dd-blogs/SKILL.md
git commit -m "feat(dd-blogs): rewrite SKILL.md for 7-phase workflow"
```

---

## Task 9: Bump plugin.json version

**Files:**
- Modify: `custom/dd-blogs/.claude-plugin/plugin.json`

- [ ] **Step 1: Update version field**

Replace `"version": "1.0.0"` with `"version": "2.0.0"` in `custom/dd-blogs/.claude-plugin/plugin.json`.

Also update `description` field to:

```
"description": "ldnddev brand-tone blog generator — guided Q&A intake, mandatory research, draft review, full index.html + hero + social + sitemap output.",
```

- [ ] **Step 2: Validate JSON**

```bash
python3 -c "import json; json.load(open('custom/dd-blogs/.claude-plugin/plugin.json'))"
```

Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add custom/dd-blogs/.claude-plugin/plugin.json
git commit -m "chore(dd-blogs): bump to 2.0.0"
```

---

## Task 10: Update install.sh to include scripts dir

**Files:**
- Modify: `custom/dd-blogs/install.sh`

- [ ] **Step 1: Replace install.sh**

Overwrite `custom/dd-blogs/install.sh` with:

```bash
#!/usr/bin/env bash
# Codex install path for dd-blogs. Claude Code users: install via plugin.
# Mirrors skills/dd-blogs/ into ${CODEX_HOME:-~/.codex}/skills/dd-blogs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-blogs"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-blogs/SKILL.md" "$TARGET_DIR/SKILL.md"
cp -R "$SCRIPT_DIR/skills/dd-blogs/references" "$TARGET_DIR/references"
cp -R "$SCRIPT_DIR/skills/dd-blogs/scripts" "$TARGET_DIR/scripts"
chmod +x "$TARGET_DIR/scripts/blog_helper.py"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh"

cat <<MSG
Installed dd-blogs skill to: $TARGET_DIR
MSG
```

- [ ] **Step 2: Verify executable bit preserved**

```bash
ls -l custom/dd-blogs/install.sh
```

Expected: `-rwxr-xr-x` (executable). If not, run `chmod +x custom/dd-blogs/install.sh`.

- [ ] **Step 3: Commit**

```bash
git add custom/dd-blogs/install.sh
git commit -m "chore(dd-blogs): install.sh copies scripts dir"
```

---

## Task 11: Rewrite README.md

**Files:**
- Modify: `custom/dd-blogs/README.md`

- [ ] **Step 1: Replace README.md**

Overwrite `custom/dd-blogs/README.md` with:

```markdown
# dd-blogs — ldnddev Blog Generator Skill

Guided blog generator for ldnddev.com. Walks you through a 7-phase workflow — intake, research, plan, draft, review, assemble, summary — and produces a drop-in blog directory.

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-blogs@dd-skills
```

## Install — Codex skill

`bash install.sh` from this directory. See [root README](../../README.md#codex-install-legacy) for context.

## Trigger phrases

- "write a blog post about <topic>"
- "draft an ldnddev blog on <topic>"
- "revise this blog draft" (paste draft)
- Weekly cron blog generation

## Workflow

1. **Intake** — Skill asks: topic, audience, takeaway + CTA, output path, existing blog root, publish date, keywords
2. **Discovery** — Lists existing blogs, runs WebSearch + WebFetch for grounding
3. **Plan** — Locks SEO meta, slug, H2 outline, cross-link targets
4. **Draft** — Writes blog body, validates word count (1800–2200)
5. **Review gate** — You approve or edit; loop until approved
6. **Assemble** — Writes index.html, hero images (or prompts), social.md, sitemap entry
7. **Summary** — Prints all written paths + merge status

## Per-blog output

```
<output_root>/<slug>/
├── index.html         # full HTML doc (head + body + ld+json)
├── hero-lg.webp       # or hero-prompts.md fallback
├── hero-sm.webp
├── social.md          # 3 X + 3 LinkedIn posts
└── sitemap-entry.xml  # also merged into site sitemap if path given
```

## Layout

```
dd-blogs/
├── .claude-plugin/plugin.json
├── install.sh
└── skills/dd-blogs/
    ├── SKILL.md
    ├── scripts/
    │   ├── blog_helper.py
    │   └── test_blog_helper.py
    └── references/
        ├── blog-header.md
        ├── blog-markup.md
        ├── ldjson-template.md
        ├── sitemap-blog.md
        └── social-template.md
```

## Tone formula

60% professional / 20% conversational / 20% personality. Sign-off: "Until next time, Jared Lyvers". Word count: 1800–2200.

## Helper CLI

`scripts/blog_helper.py` provides deterministic ops the skill calls during the workflow:

| Subcommand | Purpose |
|---|---|
| `slug "<title>"` | kebab-case slug |
| `dates YYYY-mm-dd` | JSON: 4 date formats (mmddYYYY, mm-dd-YYYY, YYYY-mm-dd, long) |
| `wordcount <file>` | JSON: count, in_range, min, max |
| `list-blogs <root>` | JSON: existing blogs (slug, title, date, path) |
| `merge-sitemap <sitemap.xml> <slug> <YYYY-mm-dd>` | inserts `<url>` sorted, idempotent, creates .bak |

Run tests: `cd skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v`
```

- [ ] **Step 2: Commit**

```bash
git add custom/dd-blogs/README.md
git commit -m "docs(dd-blogs): rewrite README for new workflow"
```

---

## Task 12: Run full test suite + manual smoke test

**Files:** (verification only)

- [ ] **Step 1: Run full pytest suite**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts && python -m pytest test_blog_helper.py -v
```

Expected: 32 PASS, 0 FAIL.

- [ ] **Step 2: Create smoke-test fixture**

```bash
mkdir -p /tmp/dd-blogs-smoke/existing-blogs
mkdir -p /tmp/dd-blogs-smoke/existing-blogs/sample-old-post
cat > /tmp/dd-blogs-smoke/existing-blogs/sample-old-post/index.html <<'EOF'
<!doctype html>
<html>
<head>
<title>ldnddev, LLC. Insights | Sample Old Post About Drupal</title>
<link rel="canonical" href="https://www.ldnddev.com/blog/sample-old-post" />
<script type="application/ld+json">
{"@type":"BlogPosting","datePublished":"01-15-2026"}
</script>
</head>
<body></body>
</html>
EOF
cat > /tmp/dd-blogs-smoke/sitemap.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap-0.9">
  <url>
    <loc>https://ldnddev.com/blog/sample-old-post/</loc>
    <lastmod>2026-01-15T12:13:00+00:00</lastmod>
    <priority>0.80</priority>
  </url>
</urlset>
EOF
```

- [ ] **Step 3: Smoke-test the helper directly**

```bash
cd custom/dd-blogs/skills/dd-blogs/scripts

python3 blog_helper.py slug "How We Migrated a 200k-Page Drupal Site"
# Expected: how-we-migrated-a-200k-page-drupal-site

python3 blog_helper.py dates 2026-05-16
# Expected: {"mmddYYYY": "05162026", "mm-dd-YYYY": "05-16-2026", "YYYY-mm-dd": "2026-05-16", "long": "May 16, 2026"}

python3 blog_helper.py list-blogs /tmp/dd-blogs-smoke/existing-blogs
# Expected: JSON array with one entry: sample-old-post

python3 blog_helper.py merge-sitemap /tmp/dd-blogs-smoke/sitemap.xml smoke-test-post 2026-05-16
cat /tmp/dd-blogs-smoke/sitemap.xml
# Expected: contains <loc>https://ldnddev.com/blog/smoke-test-post/</loc> sorted after sample-old-post
ls /tmp/dd-blogs-smoke/sitemap.xml.bak
# Expected: backup file exists
```

- [ ] **Step 4: Verify all expected files exist**

```bash
for f in \
  custom/dd-blogs/.claude-plugin/plugin.json \
  custom/dd-blogs/install.sh \
  custom/dd-blogs/README.md \
  custom/dd-blogs/skills/dd-blogs/SKILL.md \
  custom/dd-blogs/skills/dd-blogs/scripts/blog_helper.py \
  custom/dd-blogs/skills/dd-blogs/scripts/test_blog_helper.py \
  custom/dd-blogs/skills/dd-blogs/references/blog-header.md \
  custom/dd-blogs/skills/dd-blogs/references/blog-markup.md \
  custom/dd-blogs/skills/dd-blogs/references/ldjson-template.md \
  custom/dd-blogs/skills/dd-blogs/references/sitemap-blog.md \
  custom/dd-blogs/skills/dd-blogs/references/social-template.md \
; do
  [ -f "$f" ] && echo "OK $f" || echo "MISSING $f"
done
```

Expected: all `OK`.

- [ ] **Step 5: Validate plugin.json + SKILL.md frontmatter**

```bash
python3 -c "import json; v=json.load(open('custom/dd-blogs/.claude-plugin/plugin.json'))['version']; assert v=='2.0.0', v"
head -4 custom/dd-blogs/skills/dd-blogs/SKILL.md
```

Expected: plugin.json validates, SKILL.md starts with frontmatter (`---`, `name: dd-blogs`, `description: ...`, `---`).

- [ ] **Step 6: Cleanup smoke fixture**

```bash
rm -rf /tmp/dd-blogs-smoke
```

- [ ] **Step 7: Final commit (if anything was tweaked in this task)**

If any file changed during smoke testing:

```bash
git add -A
git commit -m "chore(dd-blogs): smoke-test fixes"
```

Otherwise skip this step.

---

## Done Criteria

- All 32 pytest tests pass
- All 11 source files exist and validate
- Helper CLI works for all 5 subcommands against real fixtures
- plugin.json on 2.0.0
- All work committed
