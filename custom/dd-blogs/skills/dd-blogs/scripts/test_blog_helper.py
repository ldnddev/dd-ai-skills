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
