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
