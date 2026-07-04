# dd-seo GSC File-Export Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the `dd-seo` audit ingest a Google Search Console `.zip`/`.csv` UI export via `--gsc <path>` and enrich the existing report + action plan with real performance insights, using zero new dependencies.

**Architecture:** A new pure-stdlib `gsc_import.py` parses the export into normalized rows plus an `insights` block and an `issues` list. `generate_report.py` runs it as one more analysis when `--gsc` is set; results land in `data["sections"]["gsc"]`. Because `build_seo_tasks` already harvests `section["issues"]`, action-plan/CSV wiring is automatic — only argparse, `collect_data`, and one render block change.

**Tech Stack:** Python 3 standard library (`csv`, `zipfile`, `io`, `argparse`, `json`, `re`), pytest 9.

---

## Conventions

- Skill scripts dir: `custom/dd-seo-audit/skills/dd-seo/scripts/`
- New module: `scripts/gsc_import.py`
- Tests dir (new): `custom/dd-seo-audit/tests/` with `conftest.py` inserting the scripts dir on `sys.path`.
- Run tests from repo root: `python3 -m pytest custom/dd-seo-audit/tests/ -v`
- All commits on branch `feature/dd-seo-gsc-import`.

---

## Normalized output contract (built incrementally, tasks 1-4)

`gsc_import.py --json <path>` prints one JSON object to stdout and exits 0:

```json
{
  "source": "file",
  "meta": {"input": "...", "kind": "zip|csv", "reports": ["queries","pages"],
           "rows_parsed": 0, "skipped": 0, "brand_tokens": ["ldnddev"],
           "comparison": false, "min_impressions": 50, "notes": []},
  "rows": [{"query": "...", "page": "...", "clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}],
  "insights": {"striking_distance": [], "low_ctr": [], "top_performers": {}, "trends": {}, "cannibalization": []},
  "issues": [{"severity": "High", "finding": "...", "evidence": "...", "fix": "..."}]
}
```

On unusable input it prints `{"source":"file","error":"...","meta":{...},"rows":[],"insights":{},"issues":[]}` and still exits 0, so `generate_report.py` omits the section and continues.

---

### Task 0: Test scaffolding

**Files:**
- Create: `custom/dd-seo-audit/tests/conftest.py`

- [ ] **Step 1: Create conftest so tests can import the module**

```python
# custom/dd-seo-audit/tests/conftest.py
import os
import sys

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "skills", "dd-seo", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))
```

- [ ] **Step 2: Commit**

```bash
git add custom/dd-seo-audit/tests/conftest.py
git commit -m "test: add dd-seo test scaffolding for gsc_import"
```

---

### Task 1: Parse CSV/ZIP into normalized rows

**Files:**
- Create: `custom/dd-seo-audit/skills/dd-seo/scripts/gsc_import.py`
- Test: `custom/dd-seo-audit/tests/test_gsc_parse.py`

- [ ] **Step 1: Write failing tests**

```python
# custom/dd-seo-audit/tests/test_gsc_parse.py
import io
import zipfile
import gsc_import as g


def test_parse_ctr_percent_string():
    assert g._parse_ctr("3.4%") == 3.4
    assert g._parse_ctr("0.03") == 3.0      # fraction -> percent
    assert g._parse_ctr("12") == 12.0       # already percent
    assert g._parse_ctr("") is None


def test_detect_report_from_header():
    assert g._report_kind(["Top queries", "Clicks", "Impressions", "CTR", "Position"]) == "queries"
    assert g._report_kind(["Top pages", "Clicks", "Impressions", "CTR", "Position"]) == "pages"
    assert g._report_kind(["Date", "Clicks", "Impressions", "CTR", "Position"]) == "dates"
    assert g._report_kind(["Nonsense", "A"]) is None


def test_parse_queries_csv_rows():
    text = "Top queries,Clicks,Impressions,CTR,Position\nred team,10,500,2%,12.3\nbad,x,y,z,w\n"
    rows, kind, skipped = g._parse_csv_text(text)
    assert kind == "queries"
    assert skipped == 1
    assert rows == [{"query": "red team", "page": None,
                     "clicks": 10, "impressions": 500, "ctr": 2.0, "position": 12.3}]


def test_parse_zip_collects_members():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Queries.csv", "Top queries,Clicks,Impressions,CTR,Position\na,1,2,50%,1.0\n")
        z.writestr("Pages.csv", "Top pages,Clicks,Impressions,CTR,Position\nhttps://x/a,1,2,50%,1.0\n")
    result = g.load_export(buf.getvalue(), kind="zip", input_name="e.zip")
    assert set(result["meta"]["reports"]) == {"queries", "pages"}
    assert result["meta"]["rows_parsed"] == 2


def test_non_gsc_csv_returns_error():
    result = g.load_export(b"foo,bar\n1,2\n", kind="csv", input_name="x.csv")
    assert "error" in result
    assert result["rows"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_parse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gsc_import'`

- [ ] **Step 3: Implement the parser**

```python
#!/usr/bin/env python3
"""
Google Search Console file-export importer.

Parses a GSC UI export (.zip full Performance export, or a single .csv report)
into normalized rows + derived insights for the dd-seo audit pipeline. Pure
standard library — no auth, no network. Distinct from gsc_checker.py (API).

Usage:
    python3 gsc_import.py path/to/export.zip --json
    python3 gsc_import.py path/to/Queries.csv --url https://example.com --json
    python3 gsc_import.py export.zip --brand "acme,acme corp" --min-impressions 100 --json
"""

import argparse
import csv
import io
import json
import re
import sys
import zipfile

MIN_IMPRESSIONS_DEFAULT = 50

_HEADER_MAP = {
    "top queries": "queries", "query": "queries", "queries": "queries",
    "top pages": "pages", "page": "pages", "pages": "pages",
    "date": "dates",
    "country": "countries",
    "device": "devices",
    "search appearance": "appearance",
}


def _parse_int(value):
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def _parse_float(value):
    try:
        return round(float(str(value).replace(",", "").strip()), 1)
    except (ValueError, TypeError):
        return None


def _parse_ctr(value):
    """Return CTR as a percent float. '3.4%' -> 3.4; '0.03' -> 3.0; '12' -> 12.0."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    pct = s.endswith("%")
    s = s.rstrip("%").strip()
    try:
        num = float(s)
    except ValueError:
        return None
    if not pct and num <= 1:
        num *= 100
    return round(num, 2)


def _report_kind(header):
    if not header:
        return None
    return _HEADER_MAP.get(str(header[0]).strip().lower())


def _dimension_key(kind):
    return {"queries": "query", "pages": "page", "dates": "date",
            "countries": "country", "devices": "device", "appearance": "appearance"}.get(kind)


def _parse_csv_text(text):
    """Return (rows, kind, skipped) for one CSV report. rows use the normalized shape."""
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return [], None, 0
    kind = _report_kind(header)
    if kind is None:
        return [], None, 0
    dim = _dimension_key(kind)
    rows, skipped = [], 0
    for raw in reader:
        if not raw or len(raw) < 5:
            skipped += 1
            continue
        clicks = _parse_int(raw[1])
        impressions = _parse_int(raw[2])
        ctr = _parse_ctr(raw[3])
        position = _parse_float(raw[4])
        if None in (clicks, impressions, position):
            skipped += 1
            continue
        row = {"query": None, "page": None,
               "clicks": clicks, "impressions": impressions,
               "ctr": ctr if ctr is not None else 0.0, "position": position}
        if dim in ("query", "page"):
            row[dim] = str(raw[0]).strip()
        else:
            row[dim] = str(raw[0]).strip()
        rows.append(row)
    return rows, kind, skipped


def _empty_result(input_name, kind):
    return {"source": "file",
            "meta": {"input": input_name, "kind": kind, "reports": [],
                     "rows_parsed": 0, "skipped": 0, "brand_tokens": [],
                     "comparison": False, "min_impressions": MIN_IMPRESSIONS_DEFAULT,
                     "notes": []},
            "rows": [], "insights": {}, "issues": []}


def load_export(data_bytes, kind, input_name):
    """Parse raw bytes of a .zip or .csv GSC export into the base result dict."""
    result = _empty_result(input_name, kind)
    reports = {}
    all_rows = []
    total_skipped = 0

    if kind == "zip":
        try:
            zf = zipfile.ZipFile(io.BytesIO(data_bytes))
        except zipfile.BadZipFile:
            result["error"] = f"{input_name} is not a valid ZIP archive"
            return result
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            text = zf.read(name).decode("utf-8-sig", errors="replace")
            rows, rkind, skipped = _parse_csv_text(text)
            total_skipped += skipped
            if rkind:
                reports[rkind] = rows
                all_rows.extend(rows)
    else:
        text = data_bytes.decode("utf-8-sig", errors="replace")
        rows, rkind, skipped = _parse_csv_text(text)
        total_skipped += skipped
        if rkind:
            reports[rkind] = rows
            all_rows.extend(rows)

    if not reports:
        result["error"] = f"{input_name} does not look like a Google Search Console export"
        return result

    result["_reports"] = reports          # internal, stripped before JSON emit
    result["rows"] = all_rows
    result["meta"]["reports"] = sorted(reports.keys())
    result["meta"]["rows_parsed"] = len(all_rows)
    result["meta"]["skipped"] = total_skipped
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_parse.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add custom/dd-seo-audit/skills/dd-seo/scripts/gsc_import.py custom/dd-seo-audit/tests/test_gsc_parse.py
git commit -m "feat(dd-seo): parse GSC csv/zip exports into normalized rows"
```

---

### Task 2: Striking-distance + low-CTR insights → issues

**Files:**
- Modify: `scripts/gsc_import.py` (add benchmark table + two insight functions)
- Test: `custom/dd-seo-audit/tests/test_gsc_insights_core.py`

- [ ] **Step 1: Write failing tests**

```python
# custom/dd-seo-audit/tests/test_gsc_insights_core.py
import gsc_import as g


def _row(q=None, p=None, clicks=0, impr=0, ctr=0.0, pos=0.0):
    return {"query": q, "page": p, "clicks": clicks, "impressions": impr, "ctr": ctr, "position": pos}


def test_expected_ctr_monotonic():
    assert g._expected_ctr(1) > g._expected_ctr(5) > g._expected_ctr(15)


def test_striking_distance_selects_pos_11_to_20():
    rows = [_row(q="a", impr=500, pos=12.0), _row(q="b", impr=500, pos=8.0),
            _row(q="c", impr=10, pos=15.0), _row(q="d", impr=500, pos=20.0)]
    out = g.striking_distance(rows, min_impressions=50)
    got = {r["query"] for r in out}
    assert got == {"a", "d"}          # b too high a rank, c too few impressions


def test_low_ctr_flags_below_half_expected():
    # position 3 expected ~11%; 1% actual is well under half
    rows = [_row(q="under", impr=1000, ctr=1.0, pos=3.0),
            _row(q="fine", impr=1000, ctr=12.0, pos=3.0)]
    out = g.low_ctr(rows, min_impressions=50)
    got = {r["query"] for r in out}
    assert got == {"under"}


def test_core_issues_have_task_fields():
    rows = [_row(q="a", p="https://x/a", impr=4200, ctr=0.8, pos=12.0)]
    issues = g.core_issues(g.striking_distance(rows, 50), g.low_ctr(rows, 50))
    assert issues and all({"severity", "finding", "evidence", "fix"} <= set(i) for i in issues)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_insights_core.py -v`
Expected: FAIL — `AttributeError: module 'gsc_import' has no attribute '_expected_ctr'`

- [ ] **Step 3: Implement benchmark + insight functions**

Add to `gsc_import.py` (above `load_export`):

```python
# Expected organic CTR by position (percent). Static industry benchmark; no network.
_CTR_BENCHMARK = {1: 27.0, 2: 15.0, 3: 11.0, 4: 8.0, 5: 7.0,
                  6: 5.0, 7: 4.0, 8: 3.2, 9: 2.8, 10: 2.5}
_LOW_CTR_RATIO = 0.5   # actual must be <= half of expected to flag


def _expected_ctr(position):
    p = int(round(position))
    if p <= 1:
        return _CTR_BENCHMARK[1]
    if p in _CTR_BENCHMARK:
        return _CTR_BENCHMARK[p]
    return 1.5 if p <= 20 else 0.8


def _label(row):
    return row.get("query") or row.get("page") or "(unknown)"


def striking_distance(rows, min_impressions):
    hits = [r for r in rows
            if r.get("query") is not None
            and 10 < r["position"] <= 20
            and r["impressions"] >= min_impressions]
    return sorted(hits, key=lambda r: r["impressions"], reverse=True)


def low_ctr(rows, min_impressions):
    hits = []
    for r in rows:
        if r.get("query") is None and r.get("page") is None:
            continue
        if r["position"] > 20 or r["impressions"] < min_impressions:
            continue
        expected = _expected_ctr(r["position"])
        if r["ctr"] <= expected * _LOW_CTR_RATIO:
            hits.append(r)
    return sorted(hits, key=lambda r: r["impressions"], reverse=True)


def core_issues(striking, low):
    issues = []
    for r in striking[:25]:
        issues.append({
            "severity": "High",
            "finding": f"Striking-distance query '{_label(r)}' at position {r['position']}",
            "evidence": f"{r['impressions']} impressions, {r['ctr']}% CTR, position {r['position']}",
            "fix": "Strengthen on-page relevance and internal links for this query to reach page one.",
        })
    for r in low[:25]:
        exp = _expected_ctr(r["position"])
        issues.append({
            "severity": "Medium",
            "finding": f"Low CTR for '{_label(r)}' (pos {r['position']})",
            "evidence": f"{r['ctr']}% CTR vs ~{exp}% expected, {r['impressions']} impressions",
            "fix": "Rewrite the title tag and meta description to improve click-through.",
        })
    return issues
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_insights_core.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add custom/dd-seo-audit/skills/dd-seo/scripts/gsc_import.py custom/dd-seo-audit/tests/test_gsc_insights_core.py
git commit -m "feat(dd-seo): striking-distance + low-CTR insights for GSC import"
```

---

### Task 3: Top performers + branded split

**Files:**
- Modify: `scripts/gsc_import.py`
- Test: `custom/dd-seo-audit/tests/test_gsc_insights_top.py`

- [ ] **Step 1: Write failing tests**

```python
# custom/dd-seo-audit/tests/test_gsc_insights_top.py
import gsc_import as g


def test_brand_token_from_url():
    assert g.brand_tokens_from_url("https://www.ldnddev.com/x") == ["ldnddev"]
    assert g.brand_tokens_from_url("") == []


def test_top_performers_branded_split():
    reports = {
        "queries": [
            {"query": "ldnddev pricing", "page": None, "clicks": 30, "impressions": 100, "ctr": 30.0, "position": 1.0},
            {"query": "web design", "page": None, "clicks": 10, "impressions": 900, "ctr": 1.1, "position": 8.0},
        ],
        "pages": [
            {"query": None, "page": "https://x/a", "clicks": 40, "impressions": 1000, "ctr": 4.0, "position": 3.0},
        ],
    }
    out = g.top_performers(reports, brand_tokens=["ldnddev"], top_n=10)
    assert out["top_queries"][0]["query"] == "ldnddev pricing"
    assert out["top_pages"][0]["page"] == "https://x/a"
    assert out["branded"]["branded_clicks"] == 30
    assert out["branded"]["nonbranded_clicks"] == 10
    assert out["branded"]["branded_share_pct"] == 75.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_insights_top.py -v`
Expected: FAIL — `AttributeError: ... 'brand_tokens_from_url'`

- [ ] **Step 3: Implement**

Add to `gsc_import.py`:

```python
def brand_tokens_from_url(url):
    if not url:
        return []
    m = re.search(r"https?://([^/]+)", url) or re.search(r"^([^/]+)", url)
    host = (m.group(1) if m else url).lower()
    host = host.split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 2:
        return [parts[-2]]          # registrable label; good enough for common TLDs
    return parts[:1]


def top_performers(reports, brand_tokens, top_n=10):
    queries = reports.get("queries", [])
    pages = reports.get("pages", [])
    top_queries = sorted(queries, key=lambda r: r["clicks"], reverse=True)[:top_n]
    top_pages = sorted(pages, key=lambda r: r["clicks"], reverse=True)[:top_n]

    branded = {}
    if brand_tokens and queries:
        toks = [t.lower() for t in brand_tokens if t]
        b_clicks = sum(r["clicks"] for r in queries
                       if any(t in (r.get("query") or "").lower() for t in toks))
        total = sum(r["clicks"] for r in queries)
        nb_clicks = total - b_clicks
        branded = {
            "branded_clicks": b_clicks,
            "nonbranded_clicks": nb_clicks,
            "branded_share_pct": round(100 * b_clicks / total, 1) if total else 0.0,
        }
    return {"top_queries": top_queries, "top_pages": top_pages, "branded": branded}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_insights_top.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add custom/dd-seo-audit/skills/dd-seo/scripts/gsc_import.py custom/dd-seo-audit/tests/test_gsc_insights_top.py
git commit -m "feat(dd-seo): top-performers + branded split for GSC import"
```

---

### Task 4: Cannibalization + comparison-trends + CLI assembly

**Files:**
- Modify: `scripts/gsc_import.py` (add `cannibalization`, `trends`, `build_result`, `main`)
- Test: `custom/dd-seo-audit/tests/test_gsc_cli.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_cli.py -v`
Expected: FAIL — `AttributeError: ... 'cannibalization'`

- [ ] **Step 3: Implement cannibalization, trends, build_result, main**

Add to `gsc_import.py`:

```python
def cannibalization(rows):
    by_query = {}
    for r in rows:
        q, p = r.get("query"), r.get("page")
        if not q or not p:
            continue
        by_query.setdefault(q, {})[p] = {"clicks": r["clicks"], "position": r["position"]}
    out = []
    for q, pages in by_query.items():
        if len(pages) >= 2:
            out.append({"query": q,
                        "pages": [{"page": p, **meta} for p, meta in pages.items()]})
    return sorted(out, key=lambda x: len(x["pages"]), reverse=True)


def trends(base):
    """Comparison exports are not represented in the single-period reports we parse.
    When absent, record why and return an empty dict (per approved spec)."""
    if not base["meta"].get("comparison"):
        base["meta"]["notes"].append("No comparison/time data in export — trends skipped.")
        return {}
    return {}


def build_result(base, brand_tokens, min_impressions):
    reports = base.pop("_reports", {})
    rows = base["rows"]
    base["meta"]["brand_tokens"] = brand_tokens
    base["meta"]["min_impressions"] = min_impressions

    sd = striking_distance(rows, min_impressions)
    lc = low_ctr(rows, min_impressions)
    base["insights"] = {
        "striking_distance": sd,
        "low_ctr": lc,
        "top_performers": top_performers(reports, brand_tokens),
        "trends": trends(base),
        "cannibalization": cannibalization(rows),
    }
    base["issues"] = core_issues(sd, lc)
    return base


def _read_input(path):
    with open(path, "rb") as f:
        data = f.read()
    kind = "zip" if path.lower().endswith(".zip") else "csv"
    return data, kind


def main():
    parser = argparse.ArgumentParser(description="Import a Google Search Console file export")
    parser.add_argument("path", help="Path to a GSC .zip or .csv export")
    parser.add_argument("--url", default="", help="Audited URL (for brand-token derivation)")
    parser.add_argument("--brand", default="", help="Comma-separated brand tokens (override)")
    parser.add_argument("--min-impressions", type=int, default=MIN_IMPRESSIONS_DEFAULT)
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    args = parser.parse_args()

    try:
        data_bytes, kind = _read_input(args.path)
    except OSError as exc:
        print(json.dumps({"source": "file", "error": str(exc),
                          "rows": [], "insights": {}, "issues": [],
                          "meta": {"input": args.path}}))
        return

    base = load_export(data_bytes, kind, args.path)
    if "error" in base:
        base.pop("_reports", None)
        print(json.dumps(base))
        return

    brand = [t.strip() for t in args.brand.split(",") if t.strip()]
    if not brand:
        brand = brand_tokens_from_url(args.url)
    result = build_result(base, brand, args.min_impressions)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the full parser/insight suite**

Run: `python3 -m pytest custom/dd-seo-audit/tests/ -v`
Expected: PASS (all tasks 1-4 tests green)

- [ ] **Step 5: Commit**

```bash
git add custom/dd-seo-audit/skills/dd-seo/scripts/gsc_import.py custom/dd-seo-audit/tests/test_gsc_cli.py
git commit -m "feat(dd-seo): cannibalization, trends stub, and gsc_import CLI"
```

---

### Task 5: Wire `--gsc` into generate_report.py

**Files:**
- Modify: `scripts/generate_report.py` — `collect_data` (line 352), analyses list (line ~374), `main()` argparse (line 1606)
- Test: `custom/dd-seo-audit/tests/test_generate_report_wiring.py`

- [ ] **Step 1: Write failing test**

```python
# custom/dd-seo-audit/tests/test_generate_report_wiring.py
import inspect
import generate_report as r


def test_collect_data_accepts_gsc_params():
    sig = inspect.signature(r.collect_data)
    assert "gsc_path" in sig.parameters
    assert "brand" in sig.parameters
    assert "min_impressions" in sig.parameters


def test_main_defines_gsc_flag():
    src = inspect.getsource(r.main)
    assert "--gsc" in src
    assert "gsc_path" in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_generate_report_wiring.py -v`
Expected: FAIL — `AssertionError` (params/flag absent)

- [ ] **Step 3: Edit `collect_data` signature (line 352)**

Change:
```python
def collect_data(url: str) -> dict:
```
to:
```python
def collect_data(url: str, gsc_path: str = None, brand: str = None,
                 min_impressions: int = 50) -> dict:
```

- [ ] **Step 4: Append the GSC analysis after the `if html_path:` block (after line ~394)**

Insert immediately before `for name, script, args in analyses:`:
```python
    if gsc_path:
        gsc_args = [gsc_path, "--url", url, "--min-impressions", str(min_impressions)]
        if brand:
            gsc_args += ["--brand", brand]
        analyses.append(("gsc", "gsc_import.py", gsc_args))
```

- [ ] **Step 5: Add argparse flags + thread through in `main()` (line 1606)**

After the `--output-dir` argument, add:
```python
    parser.add_argument("--gsc", dest="gsc_path", default=None,
                        help="Path to a Google Search Console .zip/.csv export to enrich the audit")
    parser.add_argument("--brand", default=None,
                        help="Comma-separated brand tokens for the branded/non-branded split")
    parser.add_argument("--min-impressions", type=int, default=50,
                        help="Impression threshold for GSC striking-distance/low-CTR (default 50)")
```
Change:
```python
    data = collect_data(args.url)
```
to:
```python
    data = collect_data(args.url, gsc_path=args.gsc_path, brand=args.brand,
                        min_impressions=args.min_impressions)
```

- [ ] **Step 6: Run wiring test + confirm no regression in help**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_generate_report_wiring.py -v`
Expected: PASS (2 passed)
Run: `python3 custom/dd-seo-audit/skills/dd-seo/scripts/generate_report.py --help`
Expected: help text lists `--gsc`, `--brand`, `--min-impressions`

- [ ] **Step 7: Commit**

```bash
git add custom/dd-seo-audit/skills/dd-seo/scripts/generate_report.py custom/dd-seo-audit/tests/test_generate_report_wiring.py
git commit -m "feat(dd-seo): add --gsc/--brand/--min-impressions to generate_report"
```

---

### Task 6: Render the "Google Search Console" dashboard section

**Files:**
- Modify: `scripts/generate_report.py` — add `render_gsc_section`, call it in `_render_detailed_sections` (line 857)
- Test: `custom/dd-seo-audit/tests/test_gsc_render.py`

- [ ] **Step 1: Write failing test**

```python
# custom/dd-seo-audit/tests/test_gsc_render.py
import generate_report as r


def _gsc():
    return {
        "insights": {
            "striking_distance": [{"query": "web design", "page": None,
                                   "impressions": 900, "ctr": 1.0, "position": 12.0}],
            "low_ctr": [], "cannibalization": [],
            "top_performers": {"top_queries": [], "top_pages": [], "branded": {}},
            "trends": {},
        },
        "meta": {"rows_parsed": 1, "notes": []},
    }


def test_render_gsc_section_has_accessible_table():
    html = r.render_gsc_section(_gsc())
    assert "<table" in html
    assert "<caption" in html
    assert 'scope="col"' in html
    assert "web design" in html


def test_render_gsc_section_empty_on_error():
    assert r.render_gsc_section({"error": "bad file"}) == ""
    assert r.render_gsc_section({}) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_render.py -v`
Expected: FAIL — `AttributeError: ... 'render_gsc_section'`

- [ ] **Step 3: Implement `render_gsc_section` (add near other render fns, before `_render_detailed_sections` at line 857)**

```python
def render_gsc_section(gsc: dict) -> str:
    """Accessible HTML for the Search Console insight tables. Empty string if unusable."""
    if not gsc or gsc.get("error"):
        return ""
    ins = gsc.get("insights") or {}
    if not ins:
        return ""

    def _table(caption, cols, rows):
        if not rows:
            return ""
        head = "".join(f'<th scope="col">{html_lib.escape(c)}</th>' for c in cols)
        body = ""
        for row in rows[:100]:
            body += "<tr>" + "".join(
                f"<td>{html_lib.escape(str(c))}</td>" for c in row) + "</tr>"
        return (f'<table class="data-table"><caption>{html_lib.escape(caption)}</caption>'
                f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")

    blocks = []
    sd = ins.get("striking_distance") or []
    blocks.append(_table(
        "Striking-distance queries (position 11-20)",
        ["Query", "Impressions", "CTR %", "Position"],
        [[r.get("query") or r.get("page"), r["impressions"], r["ctr"], r["position"]] for r in sd]))

    lc = ins.get("low_ctr") or []
    blocks.append(_table(
        "Low click-through outliers",
        ["Query / Page", "Impressions", "CTR %", "Position"],
        [[r.get("query") or r.get("page"), r["impressions"], r["ctr"], r["position"]] for r in lc]))

    tp = ins.get("top_performers") or {}
    blocks.append(_table(
        "Top queries by clicks",
        ["Query", "Clicks", "Impressions", "Position"],
        [[r.get("query"), r["clicks"], r["impressions"], r["position"]] for r in tp.get("top_queries", [])]))

    can = ins.get("cannibalization") or []
    blocks.append(_table(
        "Query cannibalization (one query, multiple pages)",
        ["Query", "Competing pages"],
        [[c["query"], ", ".join(p["page"] for p in c["pages"])] for c in can]))

    branded = tp.get("branded") or {}
    if branded:
        blocks.append(
            f'<p><strong>Branded share:</strong> {branded.get("branded_share_pct", 0)}% '
            f'({branded.get("branded_clicks", 0)} branded vs '
            f'{branded.get("nonbranded_clicks", 0)} non-branded clicks)</p>')

    for note in (gsc.get("meta", {}).get("notes") or []):
        blocks.append(f'<p style="color:var(--muted)">{html_lib.escape(note)}</p>')

    body = "".join(b for b in blocks if b)
    return body or ""
```

- [ ] **Step 4: Call it inside `_render_detailed_sections` (line 857)**

After the `env_fixes` block appends (near line ~900, after the environment blocks), add:
```python
    gsc = data["sections"].get("gsc", {})
    gsc_html = render_gsc_section(gsc)
    if gsc_html:
        blocks.append(_details_block("gsc", "Google Search Console", None, gsc_html))
```

- [ ] **Step 5: Run render test**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_render.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add custom/dd-seo-audit/skills/dd-seo/scripts/generate_report.py custom/dd-seo-audit/tests/test_gsc_render.py
git commit -m "feat(dd-seo): render accessible Search Console section in report"
```

---

### Task 7: End-to-end integration + no-regression guard

**Files:**
- Test: `custom/dd-seo-audit/tests/test_gsc_end_to_end.py`

- [ ] **Step 1: Write the integration test (offline — patches network analyses)**

```python
# custom/dd-seo-audit/tests/test_gsc_end_to_end.py
import io
import zipfile
import generate_report as r


def _make_zip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Queries.csv",
                   "Top queries,Clicks,Impressions,CTR,Position\n"
                   "web design,2,4200,0.8%,12.0\n")
        z.writestr("Pages.csv",
                   "Top pages,Clicks,Impressions,CTR,Position\n"
                   "https://example.com/x,2,4200,0.8%,12.0\n")
    p = tmp_path / "gsc.zip"
    p.write_bytes(buf.getvalue())
    return str(p)


def test_gsc_issues_flow_into_tasks(tmp_path):
    gsc_path = _make_zip(tmp_path)
    # Run only the gsc analysis via the same runner generate_report uses.
    gsc_result = r.run_script("gsc_import.py",
                              [gsc_path, "--url", "https://example.com", "--min-impressions", "50"])
    data = {"url": "https://example.com", "domain": "example.com",
            "sections": {"gsc": gsc_result}, "environment_fixes": []}
    rows = r.build_seo_tasks(data)
    findings = " ".join(row["finding"] for row in rows)
    assert "Striking-distance" in findings         # GSC issue reached the task list
    assert any(row["category"] == "gsc" for row in rows)


def test_render_section_appears(tmp_path):
    gsc_path = _make_zip(tmp_path)
    gsc_result = r.run_script("gsc_import.py", [gsc_path, "--url", "https://example.com"])
    html = r.render_gsc_section(gsc_result)
    assert "Striking-distance queries" in html
```

- [ ] **Step 2: Run it (should pass once tasks 1-6 are done)**

Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_end_to_end.py -v`
Expected: PASS (2 passed)

- [ ] **Step 3: Run the whole suite**

Run: `python3 -m pytest custom/dd-seo-audit/tests/ -v`
Expected: PASS (all tests green)

- [ ] **Step 4: Commit**

```bash
git add custom/dd-seo-audit/tests/test_gsc_end_to_end.py
git commit -m "test(dd-seo): end-to-end GSC enrichment + task-flow guard"
```

---

### Task 8: Accessibility review of the rendered section

**Files:**
- Modify (only if the review flags issues): `scripts/generate_report.py` `render_gsc_section`

- [ ] **Step 1: Generate a sample section and review it**

Dispatch the `dd-a11y:accessibility-lead` agent on the `render_gsc_section` output (a rendered
sample table). Provide it the HTML from `test_gsc_render.py`'s `render_gsc_section(_gsc())`.
Ask specifically: table semantics (caption, `scope`), heading order within `_details_block`,
and color-only meaning. Target: WCAG 2.2 AA.

- [ ] **Step 2: Apply any fixes it returns**

Apply returned fixes to `render_gsc_section` only. Re-run:
Run: `python3 -m pytest custom/dd-seo-audit/tests/test_gsc_render.py -v`
Expected: PASS

- [ ] **Step 3: Commit (only if changes were made)**

```bash
git add custom/dd-seo-audit/skills/dd-seo/scripts/generate_report.py
git commit -m "fix(dd-seo): a11y refinements to Search Console section"
```

---

### Task 9: Documentation + version bump

**Files:**
- Modify: `skills/dd-seo/SKILL.md`
- Modify: `skills/dd-seo/resources/skills/seo-audit.md`
- Modify: `skills/dd-seo/resources/skills/seo-page.md`
- Modify: `README.md`
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Document the flag in SKILL.md**

Under the full/page audit description, add:
```markdown
### Google Search Console enrichment (optional)

Pass a GSC UI export to enrich the audit with real performance data:

    python3 <SKILL_DIR>/scripts/generate_report.py <url> --gsc path/to/export.zip

Accepts the full Performance `.zip` or a single report `.csv`. Adds a "Google
Search Console" section (striking-distance queries, low-CTR outliers, top
performers, branded split, cannibalization) and folds the top opportunities
into `ACTION-PLAN.md` and `tasks.csv`. Optional: `--brand "term1,term2"`,
`--min-impressions N` (default 50). No credentials required.
```

- [ ] **Step 2: Add a one-line note to seo-audit.md and seo-page.md**

Append to each, under their evidence/collection section:
```markdown
- If the user supplies a Google Search Console export (`.zip`/`.csv`), pass it via
  `generate_report.py --gsc <path>` to enrich findings with real query/click data.
```

- [ ] **Step 3: Add a line to README.md feature list**

In the dd-seo description area of `custom/dd-seo-audit/README.md`, add:
```markdown
- **Google Search Console enrichment** — pass `--gsc <export.zip|.csv>` to fold real
  striking-distance, low-CTR, branded-split, and cannibalization insights into the audit.
```

- [ ] **Step 4: Bump plugin version**

In `custom/dd-seo-audit/.claude-plugin/plugin.json`, change `"version": "1.0.3"` to `"version": "1.1.0"`.

- [ ] **Step 5: Run full suite once more**

Run: `python3 -m pytest custom/dd-seo-audit/tests/ -v`
Expected: PASS (all green)

- [ ] **Step 6: Commit**

```bash
git add custom/dd-seo-audit/skills/dd-seo/SKILL.md \
        custom/dd-seo-audit/skills/dd-seo/resources/skills/seo-audit.md \
        custom/dd-seo-audit/skills/dd-seo/resources/skills/seo-page.md \
        custom/dd-seo-audit/README.md \
        custom/dd-seo-audit/.claude-plugin/plugin.json
git commit -m "docs(dd-seo): document --gsc enrichment + bump to 1.1.0"
```

---

## Self-Review

**Spec coverage:**
- `--gsc` flag, zip + single csv → Tasks 1, 5 ✓
- Zero new deps (stdlib only) → Task 1 (csv/zipfile/io) ✓
- Striking-distance → Task 2 ✓
- Low-CTR outliers + benchmark → Task 2 ✓
- Top performers + branded split (auto from domain + `--brand`) → Tasks 3, 5 ✓
- Trends (comparison-if-present-else-skip) → Task 4 (`trends` records skip note; single-period reports carry no comparison columns, matching spec's "silently skip + note") ✓
- Cannibalization → Task 4 ✓
- Report section + ACTION-PLAN/tasks.csv via `issues` → Tasks 2, 6, 7 ✓
- Error handling (non-GSC, partial, empty, malformed, large-table cap 100) → Tasks 1, 4, 6 ✓
- Privacy/local-only → inherent (no network in gsc_import) ✓
- A11y WCAG 2.2 AA table semantics → Tasks 6, 8 ✓
- Docs + version bump → Task 9 ✓

**Placeholder scan:** No TBD/TODO; every code step shows full code. ✓

**Type consistency:** `load_export` returns dict with `_reports`; `build_result` pops `_reports` and fills `insights`/`issues`. Row shape `{query,page,clicks,impressions,ctr,position}` consistent across all functions. `core_issues` emits `{severity,finding,evidence,fix}` — exactly the keys `build_seo_tasks` reads from `section["issues"]`. Section key `"gsc"` consistent in collect_data append, render call, and tests. ✓

**Note on trends:** Per the approved spec, trends require a comparison export. The single-period Queries/Pages CSVs GSC emits do not carry before/after columns, so `trends` returns `{}` and records a note. Full comparison-column parsing is intentionally minimal here (stub that degrades gracefully); if a future export format exposes comparison columns in these files, extend `_parse_csv_text` + `trends`. This matches "comparison export if present, else skip."
