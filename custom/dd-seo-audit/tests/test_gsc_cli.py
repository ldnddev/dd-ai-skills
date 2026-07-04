# custom/dd-seo-audit/tests/test_gsc_cli.py
import io
import json
import subprocess
import sys
import os
import zipfile
import gsc_import as g

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "skills", "dd-seo", "scripts", "gsc_import.py")


def test_cannibalization_detects_multi_page_query():
    rows = [
        {"query": "shoes", "page": "https://x/a", "clicks": 5, "impressions": 100, "ctr": 5.0, "position": 4.0},
        {"query": "shoes", "page": "https://x/b", "clicks": 3, "impressions": 80, "ctr": 3.0, "position": 9.0},
        {"query": "hats", "page": "https://x/c", "clicks": 2, "impressions": 50, "ctr": 4.0, "position": 6.0},
    ]
    out = g.cannibalization(rows)
    assert len(out) == 1 and out[0]["query"] == "shoes" and len(out[0]["pages"]) == 2


def test_build_result_strips_internal_and_has_insights():
    reports = {"queries": [{"query": "web design", "page": None, "clicks": 1,
                            "impressions": 900, "ctr": 1.0, "position": 12.0}]}
    base = {"source": "file", "meta": {"input": "x", "kind": "csv", "reports": ["queries"],
            "rows_parsed": 1, "skipped": 0, "brand_tokens": [], "comparison": False,
            "min_impressions": 50, "notes": []},
            "rows": reports["queries"], "insights": {}, "issues": [], "_reports": reports}
    out = g.build_result(base, brand_tokens=[], min_impressions=50)
    assert "_reports" not in out
    assert "striking_distance" in out["insights"]
    assert out["issues"]              # the pos-12 row is striking-distance


def test_cli_emits_json_for_zip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Queries.csv", "Top queries,Clicks,Impressions,CTR,Position\nweb design,1,900,1%,12.0\n")
    p = tmp_path / "export.zip"
    p.write_bytes(buf.getvalue())
    res = subprocess.run([sys.executable, SCRIPT, str(p), "--json"],
                         capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["source"] == "file"
    assert data["meta"]["rows_parsed"] == 1


def test_cli_bad_file_is_graceful(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("foo,bar\n1,2\n")
    res = subprocess.run([sys.executable, SCRIPT, str(p), "--json"],
                         capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert "error" in data and data["rows"] == []
