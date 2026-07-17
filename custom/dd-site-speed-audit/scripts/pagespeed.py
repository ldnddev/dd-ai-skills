#!/usr/bin/env python3
"""
Fetch performance data from Google PageSpeed Insights API v5.

Pure stdlib (urllib). No API key required; optional key raises rate limits.

Usage:
    python3 pagespeed.py https://example.com
    python3 pagespeed.py https://example.com --strategy desktop --json
    python3 pagespeed.py https://example.com --api-key "$PAGESPEED_API_KEY"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PSI_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Current CWV thresholds (lab/field guidance as of 2026)
CWV_THRESHOLDS = {
    "LCP": {"good": 2500, "poor": 4000, "unit": "ms", "label": "Largest Contentful Paint"},
    "INP": {"good": 200, "poor": 500, "unit": "ms", "label": "Interaction to Next Paint"},
    "CLS": {"good": 0.1, "poor": 0.25, "unit": "", "label": "Cumulative Layout Shift"},
    "FCP": {"good": 1800, "poor": 3000, "unit": "ms", "label": "First Contentful Paint"},
    "TTFB": {"good": 800, "poor": 1800, "unit": "ms", "label": "Time to First Byte"},
    "SI": {"good": 3400, "poor": 5800, "unit": "ms", "label": "Speed Index"},
    "TBT": {"good": 200, "poor": 600, "unit": "ms", "label": "Total Blocking Time"},
}

PSI_FIELD_MAP = {
    "LARGEST_CONTENTFUL_PAINT_MS": "LCP",
    "INTERACTION_TO_NEXT_PAINT": "INP",
    "CUMULATIVE_LAYOUT_SHIFT_SCORE": "CLS",
    "FIRST_CONTENTFUL_PAINT_MS": "FCP",
    "EXPERIMENTAL_TIME_TO_FIRST_BYTE": "TTFB",
}

LAB_MAP = {
    "largest-contentful-paint": "LCP",
    "interaction-to-next-paint": "INP",
    "cumulative-layout-shift": "CLS",
    "first-contentful-paint": "FCP",
    "server-response-time": "TTFB",
    "speed-index": "SI",
    "total-blocking-time": "TBT",
}

DIAGNOSTIC_IDS = [
    "dom-size",
    "total-byte-weight",
    "render-blocking-resources",
    "uses-responsive-images",
    "uses-webp-images",
    "modern-image-formats",
    "font-display",
    "unused-javascript",
    "unused-css-rules",
    "bootup-time",
    "mainthread-work-breakdown",
    "third-party-summary",
    "uses-long-cache-ttl",
    "uses-text-compression",
    "uses-rel-preconnect",
    "redirects",
]


def _rate_metric(label: str, value: float) -> str:
    thresholds = CWV_THRESHOLDS.get(label, {})
    good = thresholds.get("good", float("inf"))
    poor = thresholds.get("poor", float("inf"))
    if value <= good:
        return "good"
    if value <= poor:
        return "needs-improvement"
    return "poor"


def _normalize_cls(value: float) -> float:
    # Field CLS sometimes arrives as hundredths of a score (e.g. 5 → 0.05)
    if value > 1:
        return round(value / 100.0, 3)
    return round(value, 3)


def get_pagespeed(
    url: str,
    strategy: str = "mobile",
    api_key: str | None = None,
    timeout: int = 90,
) -> dict:
    """Fetch PageSpeed Insights data for a single strategy."""
    result = {
        "url": url,
        "strategy": strategy,
        "performance_score": None,
        "metrics": {},
        "lab_metrics": {},
        "field_metrics": {},
        "opportunities": [],
        "diagnostics": [],
        "field_data_available": False,
        "lighthouse_version": None,
        "fetch_time": None,
        "error": None,
    }

    params = {
        "url": url,
        "strategy": strategy,
        "category": "performance",
    }
    if api_key:
        params["key"] = api_key

    request_url = f"{PSI_API}?{urllib.parse.urlencode(params)}"
    max_retries = 3
    data = None

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                request_url,
                headers={"User-Agent": "dd-site-speed/1.1 (+https://ldnddev.com)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                data = json.loads(body)
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(
                    f"  [pagespeed] Rate limited ({strategy}). Retrying in {wait_time}s…",
                    file=sys.stderr,
                )
                time.sleep(wait_time)
                continue
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
                err_json = json.loads(err_body)
                msg = err_json.get("error", {}).get("message") or err_body[:200]
            except Exception:
                msg = str(exc)
            result["error"] = f"API error HTTP {exc.code}: {msg}"
            return result
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            result["error"] = f"Request failed: {exc.reason}"
            return result
        except TimeoutError:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            result["error"] = f"API request timed out ({timeout}s)"
            return result
        except json.JSONDecodeError as exc:
            result["error"] = f"Failed to parse API response: {exc}"
            return result

    if data is None:
        result["error"] = "No data returned from PageSpeed Insights"
        return result

    lighthouse = data.get("lighthouseResult", {})
    result["lighthouse_version"] = lighthouse.get("lighthouseVersion")
    result["fetch_time"] = lighthouse.get("fetchTime")

    categories = lighthouse.get("categories", {})
    perf = categories.get("performance", {})
    score = perf.get("score")
    if score is not None:
        result["performance_score"] = int(round(score * 100))

    # Field data (CrUX)
    loading = data.get("loadingExperience", {})
    crux_metrics = loading.get("metrics", {}) or {}
    if crux_metrics:
        result["field_data_available"] = True
        for api_name, label in PSI_FIELD_MAP.items():
            metric_data = crux_metrics.get(api_name)
            if not metric_data:
                continue
            percentile = metric_data.get("percentile")
            category = (metric_data.get("category") or "").lower()
            thresholds = CWV_THRESHOLDS.get(label, {})
            value = percentile
            if label == "CLS" and value is not None:
                value = _normalize_cls(float(value))
            rating = category.replace("fast", "good").replace("average", "needs-improvement").replace("slow", "poor")
            if not rating and value is not None:
                rating = _rate_metric(label, float(value))
            result["field_metrics"][label] = {
                "value": value,
                "unit": thresholds.get("unit", ""),
                "label": thresholds.get("label", label),
                "rating": rating or "unknown",
                "source": "field",
            }

    # Lab metrics (Lighthouse)
    audits = lighthouse.get("audits", {}) or {}
    for audit_id, label in LAB_MAP.items():
        audit = audits.get(audit_id, {})
        if audit.get("numericValue") is None:
            continue
        value = float(audit["numericValue"])
        thresholds = CWV_THRESHOLDS.get(label, {})
        if label == "CLS":
            value = round(value, 3)
        else:
            value = round(value)
        result["lab_metrics"][label] = {
            "value": value,
            "unit": thresholds.get("unit", ""),
            "label": thresholds.get("label", label),
            "rating": _rate_metric(label, value),
            "source": "lab",
            "display": audit.get("displayValue") or "",
        }

    # Prefer field for primary CWV display when available; else lab
    for label in ("LCP", "INP", "CLS", "FCP", "TTFB", "SI", "TBT"):
        if label in result["field_metrics"]:
            result["metrics"][label] = result["field_metrics"][label]
        elif label in result["lab_metrics"]:
            result["metrics"][label] = result["lab_metrics"][label]

    # Opportunities
    for audit_id, audit in audits.items():
        details = audit.get("details") or {}
        if details.get("type") != "opportunity":
            continue
        savings_ms = details.get("overallSavingsMs") or 0
        savings_bytes = details.get("overallSavingsBytes") or 0
        if (savings_ms and savings_ms > 50) or (savings_bytes and savings_bytes > 1024):
            result["opportunities"].append({
                "id": audit_id,
                "title": audit.get("title", audit_id),
                "description": (audit.get("description") or "")[:400],
                "savings_ms": round(savings_ms) if savings_ms else 0,
                "savings_bytes": round(savings_bytes) if savings_bytes else 0,
                "score": audit.get("score"),
                "display": audit.get("displayValue") or "",
            })
    result["opportunities"].sort(
        key=lambda x: (x.get("savings_ms") or 0, x.get("savings_bytes") or 0),
        reverse=True,
    )

    # Diagnostics (failed or partial)
    for diag_id in DIAGNOSTIC_IDS:
        diag = audits.get(diag_id, {})
        if not diag:
            continue
        score_val = diag.get("score")
        if score_val is None:
            continue
        if score_val < 1:
            result["diagnostics"].append({
                "id": diag_id,
                "title": diag.get("title", diag_id),
                "score": round(score_val * 100),
                "display": diag.get("displayValue") or "",
                "description": (diag.get("description") or "")[:300],
            })

    return result


def get_pagespeed_both(
    url: str,
    api_key: str | None = None,
    strategies: list[str] | None = None,
) -> dict:
    """Run PSI for one or more strategies and return a combined record."""
    strategies = strategies or ["mobile", "desktop"]
    combined = {
        "url": url,
        "strategies": {},
        "error": None,
    }
    errors = []
    for strategy in strategies:
        print(f"  [pagespeed] Fetching {strategy} for {url}…", file=sys.stderr)
        data = get_pagespeed(url, strategy=strategy, api_key=api_key)
        combined["strategies"][strategy] = data
        if data.get("error"):
            errors.append(f"{strategy}: {data['error']}")
        # Be polite between strategies on free tier
        if strategy != strategies[-1]:
            time.sleep(1.5)
    if errors and all(
        combined["strategies"].get(s, {}).get("error") for s in strategies
    ):
        combined["error"] = "; ".join(errors)
    return combined


def _print_human(result: dict) -> None:
    if result.get("error") and not result.get("strategies"):
        print(f"Error: {result['error']}")
        sys.exit(1)

    if "strategies" in result:
        print(f"PageSpeed Insights — {result['url']}")
        print("=" * 50)
        for strategy, data in result["strategies"].items():
            print(f"\n## {strategy.upper()}")
            if data.get("error"):
                print(f"  Error: {data['error']}")
                continue
            score = data.get("performance_score")
            print(f"  Performance Score: {score}/100")
            src = "Field (CrUX)" if data.get("field_data_available") else "Lab (Lighthouse)"
            print(f"  Primary data: {src}")
            for name, metric in (data.get("metrics") or {}).items():
                unit = metric.get("unit") or ""
                value = metric.get("value")
                if unit == "ms" and isinstance(value, (int, float)) and value >= 1000:
                    display = f"{value / 1000:.1f}s"
                elif unit == "ms":
                    display = f"{value}ms"
                else:
                    display = str(value)
                print(f"  {name}: {display} ({metric.get('rating')})")
            if data.get("opportunities"):
                print("  Top opportunities:")
                for opp in data["opportunities"][:5]:
                    print(f"    - {opp['title']} (~{opp['savings_ms']}ms)")
        return

    # Single-strategy human output
    if result.get("error"):
        print(f"Error: {result['error']}")
        sys.exit(1)
    print(f"PageSpeed Insights — {result['url']} ({result['strategy']})")
    print(f"Score: {result.get('performance_score')}/100")
    for name, metric in (result.get("metrics") or {}).items():
        print(f"  {name}: {metric.get('value')}{metric.get('unit', '')} ({metric.get('rating')})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Get Core Web Vitals from PageSpeed Insights")
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument(
        "--strategy",
        "-s",
        default="both",
        choices=["mobile", "desktop", "both"],
        help="Analysis strategy (default: both)",
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("PAGESPEED_API_KEY") or os.environ.get("PSI_API_KEY"),
        help="Google PageSpeed API key (optional; also PAGESPEED_API_KEY / PSI_API_KEY env)",
    )
    parser.add_argument("--timeout", type=int, default=90, help="HTTP timeout seconds")
    args = parser.parse_args()

    if args.strategy == "both":
        result = get_pagespeed_both(args.url, api_key=args.api_key)
    else:
        result = get_pagespeed(
            args.url, strategy=args.strategy, api_key=args.api_key, timeout=args.timeout
        )

    if args.json:
        print(json.dumps(result, indent=2))
        return
    _print_human(result)


if __name__ == "__main__":
    main()
