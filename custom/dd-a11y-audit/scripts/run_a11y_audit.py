#!/usr/bin/env python3
"""
Run single-page or multi-page accessibility audits and generate a combined report set.
"""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


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


def run_page_audit(url, level, output_json):
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
    result = subprocess.run(cmd)
    return result.returncode


def capture_screenshots(url, input_json, screenshots_dir):
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "capture_a11y_screenshots.py"),
        url,
        "--input",
        str(input_json),
        "--output-dir",
        str(screenshots_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": True, "message": result.stderr or result.stdout}
    return json.loads(result.stdout)


def relpath(path, root):
    return str(Path(path).relative_to(root))


def aggregate_pages(pages, root_url, level):
    valid_pages = [page for page in pages if not page.get("error")]
    if not valid_pages:
        return {
            "metadata": {
                "url": root_url,
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "tool": "axe-core",
                "wcag_level": level,
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
    deduped_recs = []
    seen = set()
    for rec in recommendations:
        marker = (rec.get("priority"), rec.get("issue"), rec.get("action"))
        if marker in seen:
            continue
        seen.add(marker)
        deduped_recs.append(rec)

    return {
        "metadata": {
            "url": root_url,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "tool": "axe-core",
            "wcag_level": level,
            "score": avg_score,
            "mode": "multi",
            "page_count": len(valid_pages),
        },
        "summary": summary,
        "principle_counts": principle_counts,
        "pages": pages,
        "recommendations": deduped_recs,
    }


def run_multi_audit(urls, level, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    used_slugs = set()
    page_results = []
    highest_exit = 0

    for url in urls:
        page_slug = slugify_url(url, used_slugs)
        page_dir = pages_dir / page_slug
        screenshots_dir = page_dir / "screenshots"
        page_dir.mkdir(parents=True, exist_ok=True)
        page_json = page_dir / "axe-results.json"

        exit_code = run_page_audit(url, level, page_json)
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

        if not page_data.get("error"):
            shot_data = capture_screenshots(url, page_json, screenshots_dir)
            if not shot_data.get("error"):
                page_data["screenshots"] = {
                    "full_page": relpath(shot_data["full_page"], output_dir) if shot_data.get("full_page") else None,
                    "issues": [
                        {
                            **item,
                            "path": relpath(item["path"], output_dir) if item.get("path") else None,
                        }
                        for item in shot_data.get("issue_screenshots", [])
                    ],
                }
            else:
                page_data["screenshots"] = {"error": True, "message": shot_data.get("message", "")}

        page_json.write_text(json.dumps(page_data, indent=2))

        page_results.append(page_data)

    combined = aggregate_pages(page_results, urls[0], level)
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
    args = parser.parse_args()

    urls = collect_urls(args)
    if not urls:
        parser.error("Provide a URL, --urls-file, or --sitemap.")

    root_reference = args.url or urls[0]
    output_dir = Path(args.output_dir) if args.output_dir else default_output_dir(root_reference)
    output_dir.mkdir(parents=True, exist_ok=True)

    if len(urls) == 1:
        json_path = output_dir / "axe-results.json"
        audit_result = run_page_audit(urls[0], args.level, json_path)
        if audit_result in (0, 2, 3) and json_path.exists():
            screenshots_dir = output_dir / "screenshots"
            shot_data = capture_screenshots(urls[0], json_path, screenshots_dir)
            page_data = json.loads(json_path.read_text())
            if not shot_data.get("error"):
                page_data["screenshots"] = {
                    "full_page": relpath(shot_data["full_page"], output_dir) if shot_data.get("full_page") else None,
                    "issues": [
                        {
                            **item,
                            "path": relpath(item["path"], output_dir) if item.get("path") else None,
                        }
                        for item in shot_data.get("issue_screenshots", [])
                    ],
                }
            else:
                page_data["screenshots"] = {"error": True, "message": shot_data.get("message", "")}
            json_path.write_text(json.dumps(page_data, indent=2))
    else:
        json_path, audit_result = run_multi_audit(urls, args.level, output_dir)

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
    report_result = subprocess.run(report_cmd, capture_output=True, text=True)
    if report_result.returncode != 0:
        print(report_result.stderr or report_result.stdout, file=sys.stderr)
        sys.exit(report_result.returncode)

    print(report_result.stdout.strip())
    sys.exit(audit_result)


if __name__ == "__main__":
    main()
