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
