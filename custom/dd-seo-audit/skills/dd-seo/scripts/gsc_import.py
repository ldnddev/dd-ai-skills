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
