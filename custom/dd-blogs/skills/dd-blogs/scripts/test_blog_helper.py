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


def test_wordcount_directory_errors():
    with tempfile.TemporaryDirectory() as tmp:
        code, _, err = run("wordcount", tmp)
        assert code != 0
        assert "director" in err.lower()


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


def test_merge_sitemap_malformed_xml_errors():
    with tempfile.TemporaryDirectory() as tmp:
        sm = Path(tmp) / "sitemap.xml"
        sm.write_text("<not-xml")
        code, _, err = run("merge-sitemap", str(sm), "x", "2026-05-16")
        assert code != 0
        assert "parse" in err.lower() or "xml" in err.lower()


def test_merge_sitemap_idempotent_preserves_original_backup():
    """Backup must remain the pre-merge original even after a no-op re-run."""
    with tempfile.TemporaryDirectory() as tmp:
        sm = Path(tmp) / "sitemap.xml"
        sm.write_text(POPULATED_SITEMAP)
        bak = sm.with_suffix(".xml.bak")
        run("merge-sitemap", str(sm), "new-post", "2026-05-16")
        first_bak = bak.read_text()
        assert first_bak == POPULATED_SITEMAP
        run("merge-sitemap", str(sm), "new-post", "2026-05-16")
        assert bak.read_text() == first_bak
