#!/usr/bin/env python3
"""
Run single-page or multi-page accessibility audits and generate a combined report set.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from capture_a11y_screenshots import IMPACT_ORDER, is_visual_finding


SCRIPT_DIR = Path(__file__).resolve().parent
A11Y_AUDIT_TYPE = "a11y-audit"


def default_output_dir(url_or_domain):
    parsed = urlparse(url_or_domain if "://" in url_or_domain else f"https://{url_or_domain}")
    domain = (parsed.netloc or parsed.path or "site").lower()
    safe_domain = "".join(ch if ch.isalnum() or ch in ".-" else "-" for ch in domain).strip("-") or "site"
    folder_name = f"{safe_domain}-{A11Y_AUDIT_TYPE}-{date.today().isoformat()}"
    web_root = Path.cwd() / "web"
    candidate = web_root / folder_name
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = web_root / f"{folder_name}-{index}"
        if not candidate.exists():
            return candidate
        index += 1


def slugify_url(url, used_slugs):
    parsed = urlparse(url)
    raw = parsed.path.strip("/") or "home"
    raw = raw.replace("/", "-")
    safe = "".join(ch if ch.isalnum() or ch in ".-_" else "-" for ch in raw).strip("-") or "page"
    slug = safe
    index = 2
    while slug in used_slugs:
        slug = f"{safe}-{index}"
        index += 1
    used_slugs.add(slug)
    return slug


def read_urls_file(path):
    urls = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def read_sitemap(url):
    with urlopen(url) as response:
        content = response.read()
    root = ET.fromstring(content)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [loc.text.strip() for loc in root.findall(".//sm:url/sm:loc", ns) if loc.text]
    if urls:
        return urls
    return [loc.text.strip() for loc in root.findall(".//loc") if loc.text]


def collect_urls(args):
    urls = []
    if args.url:
        urls.append(args.url)
    if args.urls_file:
        urls.extend(read_urls_file(args.urls_file))
    if args.sitemap:
        urls.extend(read_sitemap(args.sitemap))
    deduped = []
    seen = set()
    for url in urls:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
    if args.max_urls:
        deduped = deduped[: args.max_urls]
    return deduped


def prepare_axe_env():
    """Resolve npm latest axe-core once, then reuse that copy for every page."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "axe_audit.py"), "--prepare-axe"],
        capture_output=True,
        text=True,
    )
    if proc.stdout.strip():
        try:
            status = json.loads(proc.stdout)
        except json.JSONDecodeError:
            status = {}
        if status.get("warning"):
            print(status["warning"], file=sys.stderr)
        elif status.get("axe_core"):
            freshness = "current" if status.get("ok") else "installed"
            print(
                f"axe-core {status['axe_core']} ({freshness}); "
                f"@axe-core/playwright {status.get('axe_playwright') or 'unknown'}",
                file=sys.stderr,
            )
    elif proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)
    env = os.environ.copy()
    env["DD_A11Y_SKIP_AXE_UPDATE"] = "1"
    return env


def run_page_audit(url, level, output_json, env=None):
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "axe_audit.py"),
        url,
        "--level",
        level,
        "--json",
        "--output",
        str(output_json),
    ]
    result = subprocess.run(cmd, env=env)
    return result.returncode


def capture_screenshots(
    url,
    input_json,
    screenshots_dir,
    cap=3,
    id_start=1,
    impacts="critical",
    pin_impacts="critical,serious",
    pin_cap=8,
    annotate=True,
    pin_format="jpeg",
):
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "capture_a11y_screenshots.py"),
        url,
        "--input",
        str(input_json),
        "--output-dir",
        str(screenshots_dir),
        "--cap",
        str(cap),
        "--id-start",
        str(id_start),
        "--impacts",
        impacts if impacts is not None else "all",
        "--pin-impacts",
        pin_impacts if pin_impacts is not None else "all",
        "--pin-cap",
        str(pin_cap),
        "--pin-format",
        pin_format,
    ]
    if not annotate:
        cmd.append("--no-annotate")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": True, "message": result.stderr or result.stdout}
    return json.loads(result.stdout)


def page_worst_key(page):
    """Sort key for worst pages first (more critical/serious, lower score)."""
    summary = page.get("summary") or {}
    score = page.get("metadata", {}).get("score")
    if score is None:
        score = 100
    return (
        -(summary.get("critical_violations") or 0),
        -(summary.get("serious_violations") or 0),
        score,
    )


def select_annotated_page_slugs(pages, limit=15):
    """Return set of page_slug values that should get annotated issue shots."""
    valid = [p for p in pages if not p.get("error")]
    ranked = sorted(valid, key=page_worst_key)
    return {p.get("page_slug") for p in ranked[: max(0, int(limit))]}


def relpath(path, root):
    return str(Path(path).relative_to(root))


# Shared chrome: header, footer, nav, banner/contentinfo/navigation landmarks,
# and cookie or consent widgets. A repeated main-content selector is a template,
# not chrome. The same rule + selector on two or more URLs rolls up either way.
_CHROME = re.compile(
    r"(?:"
    r"(?:^|[^\w])(?:header|footer|nav)(?:[^\w]|$)"
    r"|role=[\"']?(?:banner|contentinfo|navigation)"
    r"|cookie|consent|gdpr|onetrust|cookiebot|cookieyes"
    r")",
    re.IGNORECASE,
)


def finding_selector_key(violation):
    """Stable identity for the same node across pages. Blank when there is no target."""
    previews = violation.get("nodes_preview") or []
    if not previews:
        return ""
    target = previews[0].get("target") or []
    parts = []
    for item in target:
        if isinstance(item, list):
            parts.extend(str(part) for part in item if part)
        elif item:
            parts.append(str(item))
    return re.sub(r"\s+", " ", " >> ".join(parts)).strip().lower()


def is_chrome_finding(selector, html_snippet):
    return bool(_CHROME.search(f"{selector or ''}\n{html_snippet or ''}"))


def _worst_impact(impacts):
    return min(impacts, key=lambda name: IMPACT_ORDER.get((name or "minor").lower(), 9))


def rollup_repeated(pages):
    """Group the same rule + selector seen on two or more URLs.

    Returns sitewide findings without task ids. Page violations are not removed;
    ``prepare_findings`` marks them so the report lists each group once.
    """
    groups = {}
    for page_index, page in enumerate(pages):
        if page.get("error"):
            continue
        for violation_index, violation in enumerate(page.get("violations") or []):
            selector_key = finding_selector_key(violation)
            if not selector_key:
                continue
            key = (violation.get("id") or "", selector_key)
            groups.setdefault(key, []).append({
                "page_index": page_index,
                "violation_index": violation_index,
                "page_url": page.get("page_url") or "",
                "page_slug": page.get("page_slug") or "",
                "impact": (violation.get("impact") or "minor").lower(),
                "violation": violation,
            })

    sitewide = []
    for (rule_id, selector_key), occurrences in groups.items():
        urls = []
        seen_urls = set()
        for item in occurrences:
            if item["page_url"] in seen_urls:
                continue
            seen_urls.add(item["page_url"])
            urls.append({"page_url": item["page_url"], "page_slug": item["page_slug"]})
        if len(urls) < 2:
            continue
        representative = occurrences[0]["violation"]
        previews = representative.get("nodes_preview") or [{}]
        html_snippet = (previews[0] or {}).get("html", "")
        scope = (
            "sitewide-chrome"
            if is_chrome_finding(selector_key, html_snippet)
            else "sitewide-template"
        )
        sitewide.append({
            "rule_id": rule_id,
            "impact": _worst_impact(item["impact"] for item in occurrences),
            "scope": scope,
            "selector": selector_key,
            "html": html_snippet,
            "description": representative.get("description", ""),
            "help": representative.get("help", ""),
            "wcag_tags": list(representative.get("wcag_tags") or []),
            "nodes_count": representative.get("nodes_count", 1),
            "page_count": len(urls),
            "pages": urls,
            "occurrences": [
                {key: item[key] for key in ("page_index", "violation_index", "page_url", "page_slug", "impact")}
                for item in occurrences
            ],
            "visual": is_visual_finding(representative),
            "issue_screenshot": "",
        })

    sitewide.sort(key=lambda item: (
        0 if item["scope"] == "sitewide-chrome" else 1,
        IMPACT_ORDER.get(item["impact"], 9),
        item["rule_id"],
        item["selector"],
    ))
    return sitewide


def prepare_findings(pages):
    """Assign task ids after rollup. Sitewide ids come first. Mutates ``pages``."""
    sitewide = rollup_repeated(pages)
    number = 1
    for item in sitewide:
        item["task_id"] = f"A11Y-{number:03d}"
        number += 1
        for occurrence in item["occurrences"]:
            violation = pages[occurrence["page_index"]]["violations"][occurrence["violation_index"]]
            violation["rollup_task_id"] = item["task_id"]
            violation["needs_crop"] = False
        representative = item["occurrences"][0]
        violation = pages[representative["page_index"]]["violations"][representative["violation_index"]]
        violation["task_id"] = item["task_id"]
        violation["sitewide_representative"] = True
        violation["needs_crop"] = True
        item["representative"] = {
            "page_url": representative["page_url"],
            "page_slug": representative["page_slug"],
            "page_index": representative["page_index"],
        }
    for page in pages:
        if page.get("error"):
            continue
        page["task_id_start"] = number
        for violation in page.get("violations") or []:
            if violation.get("rollup_task_id"):
                continue
            violation["task_id"] = f"A11Y-{number:03d}"
            number += 1
    return sitewide


def attach_sitewide_screenshots(sitewide, pages):
    """Copy the representative page's crop onto the sitewide finding."""
    by_slug = {page.get("page_slug"): page for page in pages}
    for item in sitewide:
        representative = item.get("representative") or {}
        page = by_slug.get(representative.get("page_slug"))
        if not page:
            continue
        for shot in (page.get("screenshots") or {}).get("issues") or []:
            if shot.get("task_id") != item.get("task_id"):
                continue
            if shot.get("status") == "captured" and shot.get("path"):
                item["issue_screenshot"] = shot["path"]
                break


def normalize_screenshots(shot_data, output_dir):
    """Map capture stdout into page_data['screenshots'] with relative paths."""
    if shot_data.get("error"):
        return {"error": True, "message": shot_data.get("message", "")}

    def rel(p):
        return relpath(p, output_dir) if p else None

    pin_map = shot_data.get("pin_map") or shot_data.get("full_page")  # transition
    issues = shot_data.get("issue_screenshots") or shot_data.get("issues") or []
    return {
        "pin_map": rel(pin_map) if pin_map else None,
        "full_page": rel(pin_map) if pin_map else None,  # alias for one release
        "pin_legend": shot_data.get("pin_legend") or [],
        "issues": [
            {
                **item,
                "path": rel(item["path"]) if item.get("path") else None,
            }
            for item in issues
        ],
    }


def aggregate_pages(pages, root_url, level):
    valid_pages = [page for page in pages if not page.get("error")]
    if not valid_pages:
        return {
            "metadata": {
                "url": root_url,
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "tool": "axe-core",
                "wcag_version": "2.2",
                "wcag_level": level,
                "wcag_target": f"WCAG 2.2 Level {level}",
                "score": 0.0,
                "mode": "multi",
                "page_count": len(pages),
            },
            "summary": {
                "total_violations": 0,
                "total_passes": 0,
                "total_incomplete": 0,
                "total_inapplicable": 0,
                "critical_violations": 0,
                "serious_violations": 0,
                "moderate_violations": 0,
                "minor_violations": 0,
            },
            "principle_counts": {
                "perceivable": 0,
                "operable": 0,
                "understandable": 0,
                "robust": 0,
            },
            "pages": pages,
            "recommendations": [],
        }

    summary_keys = [
        "total_violations",
        "total_passes",
        "total_incomplete",
        "total_inapplicable",
        "critical_violations",
        "serious_violations",
        "moderate_violations",
        "minor_violations",
    ]
    principle_keys = ["perceivable", "operable", "understandable", "robust"]

    summary = {key: 0 for key in summary_keys}
    principle_counts = {key: 0 for key in principle_keys}
    recommendations = []

    for page in valid_pages:
        for key in summary_keys:
            summary[key] += page["summary"].get(key, 0)
        for key in principle_keys:
            principle_counts[key] += page["principle_counts"].get(key, 0)
        recommendations.extend(page.get("recommendations", []))

    avg_score = round(sum(page["metadata"]["score"] for page in valid_pages) / len(valid_pages), 1)
    engine_meta = {}
    for page in valid_pages:
        meta = page.get("metadata") or {}
        if meta.get("axe_core_version"):
            engine_meta = meta
            break
    deduped_recs = []
    seen = set()
    for rec in recommendations:
        marker = (rec.get("priority"), rec.get("issue"), rec.get("action"))
        if marker in seen:
            continue
        seen.add(marker)
        deduped_recs.append(rec)

    sc_checked = set()
    saw_sc = False
    for page in valid_pages:
        page_meta = page.get("metadata") or {}
        if "sc_checked" in page_meta:
            saw_sc = True
            sc_checked.update(page_meta.get("sc_checked") or [])

    metadata = {
        "url": root_url,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "tool": engine_meta.get("tool") or "axe-core",
        "axe_core_version": engine_meta.get("axe_core_version"),
        "wcag_version": engine_meta.get("wcag_version") or "2.2",
        "wcag_level": level,
        "wcag_target": engine_meta.get("wcag_target") or f"WCAG 2.2 Level {level}",
        "wcag_tags": engine_meta.get("wcag_tags"),
        "score": avg_score,
        "score_method": engine_meta.get("score_method"),
        "mode": "multi",
        "page_count": len(valid_pages),
    }
    if saw_sc:
        metadata["sc_checked"] = sorted(sc_checked)

    return {
        "metadata": metadata,
        "summary": summary,
        "principle_counts": principle_counts,
        "pages": pages,
        "recommendations": deduped_recs,
    }


def run_multi_audit(
    urls,
    level,
    output_dir,
    screenshot_cap=3,
    no_screenshots=False,
    screenshot_mode="light",
    annotated_pages=None,
    impacts="critical,serious",
    pin_impacts="critical,serious",
    pin_cap=8,
    pin_format="jpeg",
    env=None,
):
    """Two-phase multi-page audit: axe all pages, roll up repeats, then visual crops."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    used_slugs = set()
    page_results = []
    highest_exit = 0

    # Phase 1 — axe only, then roll repeated chrome and templates into one finding.
    for url in urls:
        page_slug = slugify_url(url, used_slugs)
        page_dir = pages_dir / page_slug
        page_dir.mkdir(parents=True, exist_ok=True)
        page_json = page_dir / "axe-results.json"

        exit_code = run_page_audit(url, level, page_json, env=env)
        highest_exit = max(highest_exit, exit_code)

        if not page_json.exists():
            page_results.append({
                "page_url": url,
                "page_slug": page_slug,
                "error": True,
                "message": "Audit did not produce a JSON output file.",
            })
            continue

        page_data = json.loads(page_json.read_text())
        page_data["page_url"] = url
        page_data["page_slug"] = page_slug
        page_data["artifacts"] = {
            "audit_json": relpath(page_json, output_dir),
        }
        page_results.append(page_data)

    sitewide = prepare_findings(page_results)
    for page_data in page_results:
        if page_data.get("error"):
            continue
        page_json = pages_dir / page_data["page_slug"] / "axe-results.json"
        page_json.write_text(json.dumps(page_data, indent=2))

    # Phase 2 — visual crops. Sitewide representatives are shot on their first page.
    if not no_screenshots and screenshot_mode != "off":
        full = screenshot_mode == "full"
        ann_impacts = "all" if full else impacts
        pin_imp = "all" if full else pin_impacts
        ann_cap = screenshot_cap
        pcap = 12 if full else pin_cap
        annotate_slugs = None
        if not full and annotated_pages is not None:
            annotate_slugs = select_annotated_page_slugs(page_results, limit=annotated_pages)
            for item in sitewide:
                if not item.get("visual"):
                    continue
                slug = (item.get("representative") or {}).get("page_slug")
                if slug:
                    annotate_slugs.add(slug)

        for page_data in page_results:
            if page_data.get("error"):
                continue
            url = page_data["page_url"]
            page_slug = page_data["page_slug"]
            page_dir = pages_dir / page_slug
            page_json = page_dir / "axe-results.json"
            screenshots_dir = page_dir / "screenshots"
            id_start = int(page_data.get("task_id_start") or 1)
            do_annotate = annotate_slugs is None or page_slug in annotate_slugs
            if not do_annotate:
                page_data["screenshots"] = {
                    "pin_map": None,
                    "full_page": None,
                    "pin_legend": [],
                    "issues": [],
                }
                page_data["screenshot_annotated"] = False
                page_json.write_text(json.dumps(page_data, indent=2))
                continue
            shot_data = capture_screenshots(
                url,
                page_json,
                screenshots_dir,
                cap=ann_cap,
                id_start=id_start,
                impacts=ann_impacts,
                pin_impacts=pin_imp,
                pin_cap=pcap,
                annotate=do_annotate,
                pin_format="png" if full else pin_format,
            )
            page_data["screenshots"] = normalize_screenshots(shot_data, output_dir)
            page_data["screenshot_annotated"] = bool(do_annotate)
            page_json.write_text(json.dumps(page_data, indent=2))
        attach_sitewide_screenshots(sitewide, page_results)

    combined = aggregate_pages(page_results, urls[0], level)
    combined["sitewide"] = sitewide
    if not no_screenshots:
        combined.setdefault("metadata", {})["screenshot_mode"] = screenshot_mode
    combined_json = output_dir / "axe-results.json"
    combined_json.write_text(json.dumps(combined, indent=2))
    return combined_json, highest_exit


def main():
    parser = argparse.ArgumentParser(description="Run accessibility audit and generate report artifacts")
    parser.add_argument("url", nargs="?", help="URL to audit")
    parser.add_argument("--urls-file", help="Text file with one URL per line")
    parser.add_argument("--sitemap", help="Sitemap URL to expand into multiple pages")
    parser.add_argument("--max-urls", type=int, help="Limit the number of URLs processed")
    parser.add_argument("--level", choices=["A", "AA", "AAA"], default="AA")
    parser.add_argument("--output-dir", help="Directory for generated artifacts")
    parser.add_argument(
        "--screenshot-mode",
        choices=["light", "full", "off"],
        default="light",
        help=(
            "light (default): visual crops, critical and serious, cap 3 page-only "
            "per page; full: all impacts, cap 12 page-only; off: no screenshots. "
            "Repeated chrome is one sitewide crop either way."
        ),
    )
    parser.add_argument(
        "--screenshot-cap",
        type=int,
        default=None,
        help="Max page-only visual crops per page (default: 3 light, 12 full)",
    )
    parser.add_argument(
        "--annotated-pages",
        type=int,
        default=None,
        help="Only crop the N worst pages. Default: every page.",
    )
    parser.add_argument(
        "--no-screenshots",
        action="store_true",
        help="Skip screenshot capture entirely (alias for --screenshot-mode off)",
    )
    parser.add_argument(
        "--embed-screenshots",
        action="store_true",
        help="Embed PNGs in DOCX/Markdown (default: link to files only, keeps reports small)",
    )
    args = parser.parse_args()

    urls = collect_urls(args)
    if not urls:
        parser.error("Provide a URL, --urls-file, or --sitemap.")

    mode = "off" if args.no_screenshots else args.screenshot_mode
    if args.screenshot_cap is not None:
        cap = args.screenshot_cap
    else:
        cap = 12 if mode == "full" else 3

    root_reference = args.url or urls[0]
    audit_env = prepare_axe_env()
    output_dir = Path(args.output_dir) if args.output_dir else default_output_dir(root_reference)
    output_dir.mkdir(parents=True, exist_ok=True)

    if len(urls) == 1:
        json_path = output_dir / "axe-results.json"
        audit_result = run_page_audit(urls[0], args.level, json_path, env=audit_env)
        if audit_result in (0, 2, 3) and json_path.exists() and mode != "off":
            screenshots_dir = output_dir / "screenshots"
            full = mode == "full"
            shot_data = capture_screenshots(
                urls[0],
                json_path,
                screenshots_dir,
                cap=cap,
                impacts="all" if full else "critical,serious",
                pin_impacts="all" if full else "critical,serious",
                pin_cap=12 if full else 8,
                annotate=True,
                pin_format="png",
            )
            page_data = json.loads(json_path.read_text())
            page_data["screenshots"] = normalize_screenshots(shot_data, output_dir)
            page_data["screenshot_annotated"] = True
            page_data.setdefault("metadata", {})["screenshot_mode"] = mode
            json_path.write_text(json.dumps(page_data, indent=2))
    else:
        json_path, audit_result = run_multi_audit(
            urls,
            args.level,
            output_dir,
            screenshot_cap=cap,
            no_screenshots=(mode == "off"),
            screenshot_mode=mode,
            annotated_pages=args.annotated_pages,
            env=audit_env,
        )

    if audit_result not in (0, 2, 3):
        sys.exit(audit_result)

    report_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "generate_a11y_report.py"),
        "--input",
        str(json_path),
        "--output-dir",
        str(output_dir),
    ]
    if args.embed_screenshots:
        report_cmd.append("--embed-screenshots")
    report_result = subprocess.run(report_cmd, capture_output=True, text=True)
    if report_result.returncode != 0:
        print(report_result.stderr or report_result.stdout, file=sys.stderr)
        sys.exit(report_result.returncode)

    print(report_result.stdout.strip())
    sys.exit(audit_result)


if __name__ == "__main__":
    main()
