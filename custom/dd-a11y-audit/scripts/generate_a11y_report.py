#!/usr/bin/env python3
"""
Generate client-facing accessibility audit artifacts from axe audit JSON.
Outputs:
- WCAG-AUDIT-REPORT.md
- ACCESSIBILITY-ACTION-PLAN.md
- REMEDIATION-TASKS.csv
- A11Y-CLIENT-REPORT.docx
- index.html
"""

import argparse
import csv
import html
import json
import re
import struct
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from wcag_criteria import criteria_not_run

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
# SAL attributes the framework animates. Produced dashboards must not carry them.
_SAL_ATTR = re.compile(r"""\s+data-sal(?:-[a-z]+)?=(?:"[^"]*"|'[^']*')""")


def load_results(path):
    return json.loads(Path(path).read_text())


def load_brand_config():
    config_path = TEMPLATES_DIR / "brand.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text())


def render_template(template_text, replacements):
    rendered = template_text
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def format_audit_date(timestamp):
    if not timestamp:
        return "—"
    try:
        ts = timestamp.replace("Z", "+00:00") if isinstance(timestamp, str) else timestamp
        return datetime.fromisoformat(ts).strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return str(timestamp)


def score_label(score):
    """Rating for the axe rule pass rate. Not a WCAG conformance claim."""
    if score >= 90:
        return "Strong automated result"
    if score >= 75:
        return "Mixed automated result"
    if score >= 50:
        return "Needs Improvement"
    if score >= 25:
        return "Significant Barriers"
    return "Critical Barriers"


def wcag_target_label(meta):
    """Display string for the scan standard. New runs store wcag_target."""
    if meta.get("wcag_target"):
        return str(meta["wcag_target"])
    level = meta.get("wcag_level") or "AA"
    version = meta.get("wcag_version")
    if version:
        return f"WCAG {version} Level {level}"
    return f"Level {level}"


def severity_label(impact):
    mapping = {
        "critical": "Critical",
        "serious": "Serious",
        "moderate": "Moderate",
        "minor": "Minor",
        None: "Unknown",
    }
    return mapping.get(impact, str(impact).title())


def severity_timeline(impact):
    mapping = {
        "critical": "Immediate (1-2 days)",
        "serious": "Week 1",
        "moderate": "Month 1",
        "minor": "Month 2-3",
    }
    return mapping.get(impact, "Triage")


def owner_for_impact(impact):
    mapping = {
        "critical": "Frontend Development",
        "serious": "Frontend Development",
        "moderate": "Design + Development",
        "minor": "Product / Maintenance",
    }
    return mapping.get(impact, "Accessibility Lead")


def estimate_effort(nodes_count, impact):
    base = {
        "critical": 2.0,
        "serious": 1.5,
        "moderate": 1.0,
        "minor": 0.5,
    }.get(impact, 1.0)
    return round(max(0.5, base * max(1, nodes_count)), 1)


def first_target(violation):
    previews = violation.get("nodes_preview") or []
    if not previews:
        return ""
    target = previews[0].get("target") or []
    return ", ".join(target)


def first_html_preview(violation):
    previews = violation.get("nodes_preview") or []
    if not previews:
        return ""
    return previews[0].get("html", "")


def get_pages(results):
    if results.get("pages"):
        return results["pages"]
    page = dict(results)
    page["page_url"] = results["metadata"]["url"]
    page["page_slug"] = "page"
    return [page]


def _page_pin_map(page):
    shots = page.get("screenshots") or {}
    return shots.get("pin_map") or shots.get("full_page") or ""


def _issue_shot_lookup(page):
    lookup = {}
    for item in (page.get("screenshots") or {}).get("issues", []):
        tid = item.get("task_id")
        if not tid:
            continue
        if item.get("status") and item.get("status") != "captured":
            continue
        if item.get("path"):
            lookup[tid] = item["path"]
    return lookup


def _shot_path_for_task(page, task_id, local_index):
    """Resolve annotated screenshot path for a task.

    Prefer the global task_id (matches multi-page capture + table IDs). Fall back
    to page-local A11Y-00N for older audits that renumbered per page only.
    """
    lookup = _issue_shot_lookup(page)
    if task_id in lookup:
        return lookup[task_id]
    local_id = f"A11Y-{local_index:03d}"
    if local_id != task_id and local_id in lookup:
        return lookup[local_id]
    return ""


_SCOPE_LABEL = {
    "sitewide-chrome": "Sitewide chrome",
    "sitewide-template": "Sitewide template",
    "page": "Page",
}


def scope_label(scope):
    return _SCOPE_LABEL.get(scope or "page", "Page")


def recorded_sc_checked(results):
    """SC tags axe executed, or None when this result did not record them."""
    meta = results.get("metadata") or {}
    if "sc_checked" in meta:
        return set(meta.get("sc_checked") or [])
    found = False
    tags = set()
    for page in get_pages(results):
        page_meta = page.get("metadata") or {}
        if "sc_checked" in page_meta:
            found = True
            tags.update(page_meta.get("sc_checked") or [])
    if not found:
        return None
    return tags


def criteria_gap(results):
    """Return (target label, missing criteria). Missing is None when unrecorded."""
    meta = results.get("metadata") or {}
    checked = recorded_sc_checked(results)
    if checked is None:
        return wcag_target_label(meta), None
    missing = criteria_not_run(meta.get("wcag_level") or "AA", checked)
    return wcag_target_label(meta), missing


def _page_has_stored_ids(page):
    for violation in page.get("violations") or []:
        if violation.get("task_id") or violation.get("rollup_task_id"):
            return True
    return False


def _base_row(task_id, page_url, page_slug, scope, seen_on, page_count, shot, pin, source):
    impact = source.get("impact")
    tags = source.get("wcag_tags") or []
    return {
        "task_id": task_id,
        "page_url": page_url,
        "page_slug": page_slug,
        "scope": scope,
        "seen_on": seen_on,
        "page_count": page_count,
        "page_screenshot": pin or "",
        "issue_screenshot": shot or "",
        "priority": severity_label(impact),
        "rule_id": source.get("rule_id") or source.get("id") or "",
        "issue": source.get("description") or source.get("issue") or "",
        "wcag_tags": ", ".join(tags) if isinstance(tags, list) else tags,
        "selector": source.get("selector") or first_target(source),
        "evidence": source.get("html") or source.get("evidence") or first_html_preview(source),
        "fix": source.get("help") or source.get("fix") or "",
        "timeline": severity_timeline(impact),
        "owner": owner_for_impact(impact),
        "estimated_hours": estimate_effort(source.get("nodes_count", 1), impact),
        "nodes_count": source.get("nodes_count", 0),
        "status": "Open",
    }


def _row_from_sitewide(item, pages):
    seen = [page["page_url"] for page in item.get("pages") or [] if page.get("page_url")]
    representative = item.get("representative") or {}
    shot = item.get("issue_screenshot") or ""
    if not shot:
        for page in pages:
            if representative.get("page_slug") and page.get("page_slug") != representative.get("page_slug"):
                continue
            shot = _shot_path_for_task(page, item.get("task_id"), 0)
            if shot:
                break
    return _base_row(
        item.get("task_id") or "",
        "Sitewide",
        "sitewide",
        item.get("scope") or "sitewide-template",
        " | ".join(seen),
        item.get("page_count") or len(seen),
        shot,
        "",
        item,
    )


def build_task_rows(results):
    pages = get_pages(results)
    rows = [_row_from_sitewide(item, pages) for item in results.get("sitewide") or []]
    global_index = 1
    for page in pages:
        stored = _page_has_stored_ids(page)
        if page.get("task_id_start") and not stored:
            global_index = int(page["task_id_start"])
        page_url = page.get("page_url") or page.get("metadata", {}).get("url", "")
        pin = _page_pin_map(page)
        for local_index, violation in enumerate(page.get("violations") or [], start=1):
            if violation.get("rollup_task_id"):
                continue
            if violation.get("task_id"):
                task_id = violation["task_id"]
            else:
                task_id = f"A11Y-{global_index:03d}"
                global_index += 1
            rows.append(_base_row(
                task_id,
                page_url,
                page.get("page_slug", "page"),
                "page",
                "",
                1,
                _shot_path_for_task(page, task_id, local_index),
                pin,
                violation,
            ))
    return rows


def _shot_markdown(row, embed_screenshots):
    path = row.get("issue_screenshot")
    if not path:
        return None
    if embed_screenshots:
        return f"![Annotated issue {row['task_id']}]({path})"
    return f"[Annotated screenshot for {row['task_id']}]({path})"


def _finding_markdown(row, embed_screenshots, level=4):
    marks = "#" * level
    lines = [
        f"{marks} {row['task_id']} — {row['issue']}",
        f"**Severity:** {row['priority']}",
        f"**WCAG Tags:** {row['wcag_tags'] or 'n/a'}",
        f"**Selector:** `{row['selector'] or 'n/a'}`",
        f"**Occurrences:** {row.get('nodes_count', 0)}",
        f"**Fix:** {row['fix']}",
        f"**Evidence:** `{(row.get('evidence') or '')[:180] or 'n/a'}`",
    ]
    shot = _shot_markdown(row, embed_screenshots)
    if shot:
        lines.append(shot)
    lines.append("")
    return lines


def _criteria_markdown(results):
    target, missing = criteria_gap(results)
    lines = ["## Criteria this scan did not run", ""]
    if missing is None:
        lines.extend([
            "This result did not record which success criteria ran.",
            "",
        ])
        return lines
    lines.extend([
        f"These {target} success criteria had no axe rule execute in this scan. "
        "The score is not a conformance claim. Criteria that did run can still fail a manual review.",
        "",
    ])
    if not missing:
        lines.extend([
            "Every success criterion at this level had at least one axe rule execute.",
            "",
        ])
        return lines
    for sc in missing:
        lines.append(f"- {sc['id']} {sc['name']} ({sc['level']})")
    lines.append("")
    return lines


def _sitewide_markdown(results, rows, embed_screenshots):
    sitewide_rows = [row for row in rows if row.get("scope", "page") != "page"]
    if not sitewide_rows:
        return []
    lines = [
        "## Sitewide findings",
        "",
        "The same issue in shared chrome, or the same selector on more than one page, is listed once.",
        "",
    ]
    for row in sitewide_rows:
        lines.extend([
            f"### {row['task_id']} — {row['issue']}",
            f"**Scope:** {scope_label(row['scope'])}",
            f"**Seen on:** {row.get('page_count', 0)} pages",
            f"**Severity:** {row['priority']}",
            f"**WCAG Tags:** {row['wcag_tags'] or 'n/a'}",
            f"**Selector:** `{row['selector'] or 'n/a'}`",
            f"**Fix:** {row['fix']}",
            f"**Evidence:** `{(row.get('evidence') or '')[:180] or 'n/a'}`",
        ])
        if row.get("seen_on"):
            lines.append("**Pages:** " + row["seen_on"].replace(" | ", ", "))
        shot = _shot_markdown(row, embed_screenshots)
        if shot:
            lines.append(shot)
        lines.append("")
    return lines


def generate_markdown_report(results, embed_screenshots=False):
    meta = results["metadata"]
    summary = results["summary"]
    score = meta["score"]
    rows = build_task_rows(results)
    pages = get_pages(results)

    lines = [
        "# WCAG Accessibility Audit Report",
        f"<!-- Generated: {meta['timestamp']} -->",
        f"<!-- URL: {meta['url']} -->",
        "",
        "## Executive Summary",
        "",
        f"**Overall Score:** {score}/100 (share of axe rules that passed; not a conformance percentage)",
        f"**Automated rating:** {score_label(score)}",
        f"**WCAG Target:** {wcag_target_label(meta)}",
        f"**axe-core:** {meta.get('axe_core_version') or 'not recorded'}",
        f"**Pages Audited:** {len(pages)}",
        "",
        f"**Critical Issues:** {summary['critical_violations']}",
        f"**Serious Issues:** {summary['serious_violations']}",
        f"**Moderate Issues:** {summary['moderate_violations']}",
        f"**Minor Issues:** {summary['minor_violations']}",
        "",
        "## WCAG Principle Counts",
        "",
        "Counts are failing axe rules mapped from success-criterion tags (1.x perceivable, 2.x operable, 3.x understandable, 4.x robust). A rule can count in more than one principle.",
        "",
        "| Principle | Violations |",
        "|-----------|------------|",
        f"| Perceivable | {results['principle_counts'].get('perceivable', 0)} |",
        f"| Operable | {results['principle_counts'].get('operable', 0)} |",
        f"| Understandable | {results['principle_counts'].get('understandable', 0)} |",
        f"| Robust | {results['principle_counts'].get('robust', 0)} |",
        "",
    ]
    if results.get("sitewide"):
        sitewide_count = len(results["sitewide"])
        lines.append(
            f"**Unique remediation items:** {len(rows)} "
            f"({sitewide_count} sitewide, {len(rows) - sitewide_count} page-only). "
            "Totals above count each page before that rollup."
        )
        lines.append("")
    lines.extend(_criteria_markdown(results))
    lines.extend(_sitewide_markdown(results, rows, embed_screenshots))
    lines.extend(["## Findings", ""])

    page_rows_all = [item for item in rows if item.get("scope", "page") == "page"]
    if not rows:
        lines.extend([
            "No violations were detected by the automated audit.",
            "",
        ])
    else:
        for page in pages:
            page_url = page.get("page_url") or page.get("metadata", {}).get("url", "")
            lines.extend([
                f"### Page: {page_url}",
                f"**Page Score:** {page.get('metadata', {}).get('score', 'n/a')}/100",
                f"**Critical / Serious / Moderate / Minor:** "
                f"{page.get('summary', {}).get('critical_violations', 0)} / "
                f"{page.get('summary', {}).get('serious_violations', 0)} / "
                f"{page.get('summary', {}).get('moderate_violations', 0)} / "
                f"{page.get('summary', {}).get('minor_violations', 0)}",
                "",
            ])
            pin_map = _page_pin_map(page)
            if pin_map:
                if embed_screenshots:
                    lines.extend([f"![Issue pin map]({pin_map})", ""])
                else:
                    lines.extend([f"[Pin map]({pin_map})", ""])
            legend = (page.get("screenshots") or {}).get("pin_legend") or []
            if legend:
                lines.append("**Pin legend:** " + ", ".join(
                    f"#{p['pin']} → {p['task_id']} ({p.get('rule_id', '')})" for p in legend
                ))
                lines.append("")
            rolled = sum(
                1 for item in results.get("sitewide") or []
                if any(entry.get("page_url") == page_url for entry in item.get("pages") or [])
            )
            if rolled:
                lines.append(
                    f"Sitewide findings on this page are listed once above ({rolled})."
                )
                lines.append("")
            page_rows = [item for item in page_rows_all if item["page_url"] == page_url]
            if not page_rows:
                lines.extend(["No page-only violations.", ""])
            for row in page_rows:
                lines.extend(_finding_markdown(row, embed_screenshots, level=4))

    lines.extend([
        "## Recommendations",
        "",
    ])

    for rec in results.get("recommendations", []):
        count_text = f" ({rec.get('count')} occurrences)" if rec.get("count") else ""
        lines.append(f"- **{rec['priority'].title()}**: {rec['issue']}{count_text}. {rec['action']}")

    if not results.get("recommendations"):
        lines.append("- No additional recommendations beyond the findings list.")

    lines.extend([
        "",
        "## Deliverables",
        "",
        "- `WCAG-AUDIT-REPORT.md`",
        "- `ACCESSIBILITY-ACTION-PLAN.md`",
        "- `REMEDIATION-TASKS.csv`",
        "- `A11Y-CLIENT-REPORT.docx`",
        "- `index.html`",
        "",
    ])
    return "\n".join(lines)


def _priority_counts(rows):
    counts = {"Critical": 0, "Serious": 0, "Moderate": 0, "Minor": 0}
    for row in rows:
        if row["priority"] in counts:
            counts[row["priority"]] += 1
    return counts


def generate_action_plan(results):
    rows = build_task_rows(results)
    pages = get_pages(results)
    counts = _priority_counts(rows)
    lines = [
        "# Accessibility Action Plan",
        f"<!-- URL: {results['metadata']['url']} -->",
        f"<!-- Generated: {results['metadata']['timestamp']} -->",
        "",
        "## Priority Matrix",
        "",
        "Counts are unique remediation items. A repeated chrome or template issue counts once.",
        "",
        "| Priority | Count | Timeline | Owner |",
        "|----------|-------|----------|-------|",
        f"| Critical | {counts['Critical']} | Immediate (1-2 days) | Frontend Development |",
        f"| Serious | {counts['Serious']} | Week 1 | Frontend Development |",
        f"| Moderate | {counts['Moderate']} | Month 1 | Design + Development |",
        f"| Minor | {counts['Minor']} | Month 2-3 | Product / Maintenance |",
        "",
        f"Pages in scope: {len(pages)}",
        "",
        "## Remediation Tasks",
        "",
    ]
    if not rows:
        lines.append("No remediation tasks were generated because no violations were found.")
    else:
        for row in rows:
            lines.extend([
                f"### {row['task_id']} — {row['issue']}",
                f"- Page: {row['page_url']}",
                f"- Scope: {scope_label(row.get('scope'))}",
            ])
            if row.get("seen_on"):
                lines.append(f"- Seen on: {row['seen_on'].replace(' | ', ', ')}")
            lines.extend([
                f"- Owner: {row['owner']}",
                f"- Timeline: {row['timeline']}",
                f"- Estimated effort: {row['estimated_hours']} hours",
                f"- Fix: {row['fix']}",
                f"- Screenshot: {row['issue_screenshot'] or row['page_screenshot'] or 'n/a'}",
                "",
            ])
    return "\n".join(lines)


def write_csv(path, rows):
    fieldnames = [
        "task_id", "page_url", "page_slug", "scope", "seen_on", "page_count",
        "page_screenshot", "issue_screenshot",
        "priority", "rule_id", "issue", "wcag_tags", "selector",
        "evidence", "fix", "timeline", "owner", "estimated_hours", "nodes_count", "status",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def paragraph_xml(text):
    escaped = html.escape(text)
    return (
        "<w:p><w:r><w:t xml:space=\"preserve\">"
        f"{escaped}"
        "</w:t></w:r></w:p>"
    )


def _png_size(path):
    """Read PNG width/height from IHDR; fall back to 600x400."""
    try:
        with open(path, "rb") as handle:
            sig = handle.read(8)
            if sig != b"\x89PNG\r\n\x1a\n":
                return 600, 400
            length, ctype = struct.unpack(">I4s", handle.read(8))
            if ctype != b"IHDR" or length < 8:
                return 600, 400
            w, h = struct.unpack(">II", handle.read(8))
            return w, h
    except OSError:
        return 600, 400


def _png_extent_emu(path, max_width_in=6.0):
    w, h = _png_size(path)
    if w <= 0 or h <= 0:
        w, h = 600, 400
    max_cx = int(max_width_in * 914400)
    cx = max_cx
    cy = int(max_cx * (h / w))
    return cx, cy


def image_paragraph_xml(rid, cx, cy, doc_pr_id=1):
    return (
        f"<w:p><w:r><w:drawing>"
        f'<wp:inline distT="0" distB="0" distL="0" distR="0" '
        f'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        f'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        f'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        f'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="{doc_pr_id}" name="Picture {doc_pr_id}"/>'
        f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f"<pic:pic><pic:nvPicPr><pic:cNvPr id=\"0\" name=\"image\"/><pic:cNvPicPr/></pic:nvPicPr>"
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
        f"</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
    )


def _resolve_shot_path(rel_path, base_dir):
    """Resolve a screenshot path relative to base_dir (JSON parent)."""
    if not rel_path:
        return None
    candidate = Path(rel_path)
    if not candidate.is_absolute():
        candidate = Path(base_dir) / candidate
    if candidate.is_file():
        return candidate
    return None


def build_docx(path, results, rows, base_dir=None, embed_screenshots=False):
    body = []
    meta = results["metadata"]
    summary = results["summary"]
    utc_now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    pages = get_pages(results)
    base = Path(base_dir) if base_dir else Path(".")
    # Collect (rid, media_name, abs_path) for images that exist on disk (opt-in embed).
    media_files = []
    doc_pr_id = 1
    next_img = 1

    def register_image(rel_path):
        nonlocal next_img
        abs_path = _resolve_shot_path(rel_path, base)
        if not abs_path:
            return None, None
        rid = f"rId{next_img}"
        suffix = abs_path.suffix.lower().lstrip(".") or "png"
        media_name = f"image{next_img}.{suffix}"
        media_files.append((rid, media_name, abs_path))
        next_img += 1
        return rid, abs_path

    def append_image_or_path(label, rel_path):
        nonlocal doc_pr_id
        if embed_screenshots:
            rid, abs_path = register_image(rel_path)
            if rid:
                cx, cy = _png_extent_emu(abs_path)
                body.append(paragraph_xml(label))
                body.append(image_paragraph_xml(rid, cx, cy, doc_pr_id=doc_pr_id))
                doc_pr_id += 1
                return
        if rel_path:
            body.append(paragraph_xml(f"{label} {rel_path}"))

    body.append(paragraph_xml("Accessibility Audit Client Report"))
    body.append(paragraph_xml(f"URL: {meta['url']}"))
    body.append(paragraph_xml(f"Generated: {meta['timestamp']}"))
    body.append(paragraph_xml(f"Overall score: {meta['score']}/100 ({score_label(meta['score'])})"))
    body.append(paragraph_xml(f"WCAG target: {wcag_target_label(meta)}"))
    body.append(paragraph_xml(f"axe-core: {meta.get('axe_core_version') or 'not recorded'}"))
    body.append(paragraph_xml(f"Pages audited: {len(pages)}"))
    body.append(paragraph_xml(
        f"Critical: {summary['critical_violations']}, Serious: {summary['serious_violations']}, "
        f"Moderate: {summary['moderate_violations']}, Minor: {summary['minor_violations']}"
    ))
    target, missing = criteria_gap(results)
    body.append(paragraph_xml("Criteria this scan did not run"))
    if missing is None:
        body.append(paragraph_xml("This result did not record which success criteria ran."))
    else:
        body.append(paragraph_xml(
            f"These {target} success criteria had no axe rule execute in this scan. "
            "The score is not a conformance claim."
        ))
        if not missing:
            body.append(paragraph_xml(
                "Every success criterion at this level had at least one axe rule execute."
            ))
        for sc in missing or []:
            body.append(paragraph_xml(f"{sc['id']} {sc['name']} ({sc['level']})"))
    body.append(paragraph_xml(" "))
    sitewide_rows = [item for item in rows if item.get("scope", "page") != "page"]
    if sitewide_rows:
        body.append(paragraph_xml("Sitewide findings"))
        body.append(paragraph_xml(
            "The same issue in shared chrome, or the same selector on more than one page, is listed once."
        ))
        for row in sitewide_rows:
            body.append(paragraph_xml(
                f"{row['task_id']} | {scope_label(row['scope'])} | {row['priority']} | {row['issue']} | "
                f"Seen on {row.get('page_count', 0)} pages"
            ))
            if row.get("seen_on"):
                body.append(paragraph_xml(row["seen_on"].replace(" | ", ", ")))
            body.append(paragraph_xml(f"Fix: {row['fix']}"))
            if row["issue_screenshot"]:
                append_image_or_path("Annotated issue screenshot:", row["issue_screenshot"])
    if not rows:
        body.append(paragraph_xml("No automated violations were detected."))
    else:
        for page in pages:
            page_url = page.get("page_url") or page.get("metadata", {}).get("url", "")
            body.append(paragraph_xml(f"Page: {page_url}"))
            pin_map = _page_pin_map(page)
            if pin_map:
                append_image_or_path("Pin map:", pin_map)
            page_rows = [
                item for item in rows
                if item.get("scope", "page") == "page" and item["page_url"] == page_url
            ]
            if not page_rows:
                body.append(paragraph_xml("No page-only violations."))
            for row in page_rows:
                body.append(paragraph_xml(
                    f"{row['task_id']} | {row['priority']} | {row['issue']} | "
                    f"Owner: {row['owner']} | Timeline: {row['timeline']}"
                ))
                body.append(paragraph_xml(f"Fix: {row['fix']}"))
                if row["issue_screenshot"]:
                    append_image_or_path("Annotated issue screenshot:", row["issue_screenshot"])

    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        f"<w:body>{''.join(body)}"
        "<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"1440\" "
        "w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" w:header=\"708\" "
        "w:footer=\"708\" w:gutter=\"0\"/></w:sectPr></w:body></w:document>"
    )

    media_defaults = ""
    if media_files:
        exts = {Path(name).suffix.lower().lstrip(".") for _, name, _ in media_files}
        chunks = []
        if "png" in exts:
            chunks.append('  <Default Extension="png" ContentType="image/png"/>\n')
        if "jpg" in exts or "jpeg" in exts:
            chunks.append('  <Default Extension="jpg" ContentType="image/jpeg"/>\n')
            chunks.append('  <Default Extension="jpeg" ContentType="image/jpeg"/>\n')
        media_defaults = "".join(chunks)
    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
{media_defaults}  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

    # word/document.xml.rels — image relationships for embedded PNGs
    doc_rels_items = []
    for rid, media_name, _abs in media_files:
        doc_rels_items.append(
            f'<Relationship Id="{rid}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="media/{media_name}"/>'
        )
    document_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(doc_rels_items)}'
        "</Relationships>"
    )

    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Accessibility Audit Client Report</dc:title>
  <dc:creator>Codex a11y skill</dc:creator>
  <cp:lastModifiedBy>Codex a11y skill</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{utc_now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{utc_now}</dcterms:modified>
</cp:coreProperties>"""

    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex a11y skill</Application>
</Properties>"""

    with ZipFile(path, "w", ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("docProps/core.xml", core)
        docx.writestr("docProps/app.xml", app)
        docx.writestr("word/document.xml", document_xml)
        if media_files:
            docx.writestr("word/_rels/document.xml.rels", document_rels)
            for _rid, media_name, abs_path in media_files:
                docx.write(str(abs_path), f"word/media/{media_name}")


# --- dd-framework component builders -------------------------------------
# axe severity → dd-badge tone. The badge LABEL keeps the axe word (Critical /
# Serious / Moderate / Minor) so meaning never rides on color alone (1.4.1);
# only the color class is remapped. 'minor' → plain neutral badge (no class).
_SEVERITY_MOD = {
    "critical": "-critical",
    "serious": "-warning",
    "moderate": "-info",
    "minor": "",
}

_DOWNLOAD_FORMATS = {
    "md": "Markdown", "csv": "CSV", "docx": "DOCX", "json": "JSON", "pdf": "PDF",
}


def _badge(impact, label):
    """dd-badge pill. Meaning is carried by the label text, not color (1.4.1)."""
    mod = _SEVERITY_MOD.get((impact or "").lower(), "")
    cls = f"dd-badge {mod}" if mod else "dd-badge"
    return (f'<span class="{cls}"><span class="dd-badge__label">'
            f'{html.escape(str(label))}</span></span>')


def _render_severity_bars(summary):
    """Server-rendered dd-bar-chart rows. Label + count text is the accessible
    truth; the track/fill are decorative (aria-hidden). Widths are proportional
    to the largest count so the client width-calc JS is no longer needed."""
    order = [
        ("critical", "Critical", summary.get("critical_violations", 0)),
        ("serious", "Serious", summary.get("serious_violations", 0)),
        ("moderate", "Moderate", summary.get("moderate_violations", 0)),
        ("minor", "Minor", summary.get("minor_violations", 0)),
    ]
    top = max((c for _, _, c in order), default=0) or 1
    rows = []
    for _impact, label, count in order:
        pct = round((count / top) * 100)
        rows.append(
            f'<li class="dd-bar-chart__row">'
            f'<span class="dd-bar-chart__label">{label}</span>'
            f'<span class="dd-bar-chart__track" aria-hidden="true">'
            f'<span class="dd-bar-chart__fill" style="inline-size: {pct}%"></span></span>'
            f'<span class="dd-bar-chart__value">{count}</span>'
            f'</li>'
        )
    return "\n".join(rows)


def _render_page_cards(pages):
    """dd-card grid — one card per audited page. The URL is the card <h3> title.

    Cards link to the live page. They do not embed a full-page capture.
    A legacy pin map, when present, is decorative (alt="") and reached via
    its own link. No data-sal attributes. Audit dashboards do not animate.
    """
    cards = []
    for page in pages:
        page_url = page.get("page_url") or page.get("metadata", {}).get("url", "")
        shot = _page_pin_map(page)
        score_val = page.get("metadata", {}).get("score", "n/a")
        esc_url = html.escape(page_url)
        image = ""
        links = [
            f'<div class="dd-card__link">'
            f'<a href="{esc_url}" class="dd-button -secondary">'
            f'Open page<span class="visually-hidden"> {esc_url}</span></a></div>'
        ]
        if shot:
            esc_shot = html.escape(shot)
            image = (
                f'<div class="dd-card__image">'
                f'<img src="{esc_shot}" alt="" class="dd-image" loading="lazy"></div>'
            )
            links.append(
                f'<div class="dd-card__link">'
                f'<a href="{esc_shot}" class="dd-button -secondary">View pin map'
                f'<span class="visually-hidden"> of accessibility issues on {esc_url}</span></a></div>'
            )
        extra = f'<div class="dd-card__links dd-g">{"".join(links)}</div>'
        cards.append(
            f'<div class="dd-card__item l-box dd-u-1-1 dd-u-md-12-24">'
            f'<div class="dd-card__body dd-g">'
            f'{image}'
            f'<div class="dd-card__copy l-box">'
            f'<div class="dd-card__title"><h3>{esc_url}</h3></div>'
            f'<div class="dd-card__sub-title"><strong>Score: {html.escape(str(score_val))} / 100</strong></div>'
            f'{extra}'
            f'</div></div></div>'
        )
    if not cards:
        return (
            '<div class="dd-card__item l-box dd-u-1-1"><div class="dd-card__body">'
            '<div class="dd-card__copy l-box">'
            '<p class="muted">No page previews available for this audit.</p>'
            '</div></div></div>'
        )
    return "\n".join(cards)


def _render_task_rows(rows):
    if not rows:
        return (
            '<tr class="dd-data-table__row -empty">'
            '<td class="dd-data-table__td" colspan="8">'
            'No violations found — page is clean.</td></tr>'
        )
    out = []
    for r in rows:
        priority = r["priority"]
        if r.get("scope", "page") != "page":
            count = r.get("page_count") or 0
            page_cell = f"{scope_label(r['scope'])} ({count} pages)"
        else:
            page_cell = r["page_url"]
        # Screenshot cell needs a unique, context-bearing accessible name
        # (2.4.4/2.5.3) — the visible word ("Annotated"/"Pin map") is a substring of it.
        if r.get("issue_screenshot"):
            shot = (
                f'<a href="{html.escape(r["issue_screenshot"])}">Annotated'
                f'<span class="visually-hidden"> screenshot for {html.escape(r["task_id"])}</span></a>'
            )
        elif r.get("page_screenshot"):
            shot = (
                f'<a href="{html.escape(r["page_screenshot"])}">Pin map'
                f'<span class="visually-hidden"> for {html.escape(r["task_id"])}</span></a>'
            )
        else:
            shot = '<span class="muted">n/a</span>'
        out.append(
            f'<tr class="dd-data-table__row">'
            f'<th scope="row" class="dd-data-table__td">{html.escape(r["task_id"])}</th>'
            f'<td class="dd-data-table__td">{html.escape(page_cell)}</td>'
            f'<td class="dd-data-table__td">{_badge(priority.lower(), priority)}</td>'
            f'<td class="dd-data-table__td">{html.escape(r["issue"])}</td>'
            f'<td class="dd-data-table__td">{html.escape(r["owner"])}</td>'
            f'<td class="dd-data-table__td">{html.escape(r["timeline"])}</td>'
            f'<td class="dd-data-table__td app-selector">{html.escape(r["selector"])}</td>'
            f'<td class="dd-data-table__td">{shot}</td>'
            f'</tr>'
        )
    return "\n".join(out)


def _render_download_links(links):
    out = []
    for label, filename in links:
        fmt = _DOWNLOAD_FORMATS.get(filename.rsplit(".", 1)[-1].lower(), "File")
        text = f"{html.escape(label)} ({fmt})"
        out.append(
            f'<div class="dd-section__item dd-u-1-1 dd-u-lg-8-24 l-box">'
            f'<a href="{html.escape(filename)}" download class="dd-button -secondary" '
            f'aria-label="Download {text}">{text}</a></div>'
        )
    return "\n".join(out)


def _render_criteria_section(results):
    target, missing = criteria_gap(results)
    if missing is None:
        body = "<p>This result did not record which success criteria ran.</p>"
    else:
        intro = (
            f"<p>These {html.escape(target)} success criteria had no axe rule execute in this scan. "
            "The score is not a conformance claim. Criteria that did run can still fail a manual review.</p>"
        )
        if not missing:
            body = intro + "<p>Every success criterion at this level had at least one axe rule execute.</p>"
        else:
            items = "\n".join(
                f"<li>{html.escape(sc['id'])} {html.escape(sc['name'])} ({html.escape(sc['level'])})</li>"
                for sc in missing
            )
            body = intro + f"<ul>\n{items}\n</ul>"
    return (
        '<section class="dd-section" id="criteria-not-run" tabindex="-1" aria-labelledby="criteria-label">'
        '<div class="dd-section__content">'
        '<h2 class="dd-section__title l-box" id="criteria-label">Criteria this scan did not run</h2>'
        '<div class="dd-section__items dd-g"><div class="dd-section__item dd-u-1-1 l-box">'
        f"{body}"
        "</div></div></div></section>"
    )


def _render_sitewide_section(rows):
    sitewide = [row for row in rows if row.get("scope", "page") != "page"]
    if not sitewide:
        return ""
    body_rows = []
    for row in sitewide:
        if row.get("issue_screenshot"):
            shot = (
                f'<a href="{html.escape(row["issue_screenshot"])}">Annotated'
                f'<span class="visually-hidden"> screenshot for {html.escape(row["task_id"])}</span></a>'
            )
        else:
            shot = '<span class="muted">n/a</span>'
        page_links = []
        for url in (row.get("seen_on") or "").split(" | "):
            if not url:
                continue
            esc = html.escape(url)
            page_links.append(f'<li><a href="{esc}">{esc}</a></li>')
        count = row.get("page_count") or len(page_links)
        if page_links:
            pages_cell = (
                f"<details><summary>{count} pages</summary><ul>{''.join(page_links)}</ul></details>"
            )
        else:
            pages_cell = html.escape(str(count))
        body_rows.append(
            "<tr class=\"dd-data-table__row\">"
            f"<th scope=\"row\" class=\"dd-data-table__td\">{html.escape(row['task_id'])}</th>"
            f"<td class=\"dd-data-table__td\">{html.escape(scope_label(row['scope']))}</td>"
            f"<td class=\"dd-data-table__td\">{html.escape(row['priority'])}</td>"
            f"<td class=\"dd-data-table__td\">{html.escape(row['issue'])}</td>"
            f"<td class=\"dd-data-table__td\">{pages_cell}</td>"
            f"<td class=\"dd-data-table__td app-selector\">{html.escape(row['selector'])}</td>"
            f"<td class=\"dd-data-table__td\">{shot}</td>"
            "</tr>"
        )
    table = (
        '<div class="dd-data-table"><div class="dd-data-table__scroll" data-label="Sitewide findings, scrollable">'
        '<table class="dd-data-table__table">'
        '<caption class="dd-data-table__caption visually-hidden">'
        "Repeated chrome and template issues, listed once</caption>"
        "<thead><tr>"
        '<th scope="col" class="dd-data-table__th">ID</th>'
        '<th scope="col" class="dd-data-table__th">Scope</th>'
        '<th scope="col" class="dd-data-table__th">Priority</th>'
        '<th scope="col" class="dd-data-table__th">Issue</th>'
        '<th scope="col" class="dd-data-table__th">Pages</th>'
        '<th scope="col" class="dd-data-table__th">Selector</th>'
        '<th scope="col" class="dd-data-table__th">Screenshot</th>'
        "</tr></thead><tbody>"
        + "\n".join(body_rows)
        + "</tbody></table></div></div>"
    )
    return (
        '<section class="dd-section" id="sitewide" tabindex="-1" aria-labelledby="sitewide-label">'
        '<div class="dd-section__content">'
        '<h2 class="dd-section__title l-box" id="sitewide-label">Sitewide findings</h2>'
        '<div class="dd-section__items dd-g"><div class="dd-section__item dd-u-1-1 l-box">'
        "<p>The same issue in shared chrome, or the same selector on more than one page, is listed once.</p>"
        f"{table}"
        "</div></div></div></section>"
    )


def _inject_dashboard_sections(html_doc, results, rows):
    """Insert criteria and sitewide sections into the dashboard shell."""
    criteria = _render_criteria_section(results)
    sitewide = _render_sitewide_section(rows)
    nav = '<li><a href="#criteria-not-run">Criteria not run</a></li>'
    if sitewide:
        nav += '<li><a href="#sitewide">Sitewide findings</a></li>'
    pages_link = '<li><a href="#pages">Page Previews</a></li>'
    if pages_link in html_doc:
        html_doc = html_doc.replace(pages_link, nav + pages_link, 1)
    pages_section = '<section class="dd-section" id="pages"'
    if pages_section in html_doc:
        html_doc = html_doc.replace(pages_section, criteria + sitewide + pages_section, 1)
    return html_doc


def build_dashboard(path, results, rows):
    template_path = TEMPLATES_DIR / "dashboard.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Dashboard template not found: {template_path}")

    brand = load_brand_config()
    logo_path = brand.get("agency_logo", "/assets/imgs/logo-full-black-text.svg")
    logo_dark_path = brand.get("agency_logo_dark", "/assets/imgs/logo-full-white-text.svg")
    score = results["metadata"]["score"]
    summary = results["summary"]
    pages = get_pages(results)
    download_links = [
        ("WCAG Audit Report", "WCAG-AUDIT-REPORT.md"),
        ("Accessibility Action Plan", "ACCESSIBILITY-ACTION-PLAN.md"),
        ("Remediation Tasks", "REMEDIATION-TASKS.csv"),
        ("Client Report", "A11Y-CLIENT-REPORT.docx"),
        ("Raw axe Results", "axe-results.json"),
    ]
    total_issues = summary.get("total_violations", (
        summary["critical_violations"]
        + summary["serious_violations"]
        + summary["moderate_violations"]
        + summary["minor_violations"]
    ))
    html_doc = render_template(
        template_path.read_text(encoding="utf-8"),
        {
            "REPORT_TITLE": html.escape(brand.get("report_title", "Accessibility Audit Dashboard")),
            "REPORT_SUBTITLE": html.escape(
                brand.get(
                    "report_subtitle",
                    "Client-facing audit summary with downloadable remediation artifacts.",
                )
            ),
            "AGENCY_NAME": html.escape(brand.get("agency_name", "Accessibility Audit Team")),
            "AGENCY_KICKER": html.escape(brand.get("agency_kicker", "Accessibility Audit")),
            "AGENCY_LOGO": html.escape(logo_path),
            "AGENCY_LOGO_DARK": html.escape(logo_dark_path),
            "AUDIT_URL": html.escape(results["metadata"]["url"]),
            "AUDIT_DATE": html.escape(format_audit_date(results["metadata"]["timestamp"])),
            "WCAG_TARGET": html.escape(wcag_target_label(results["metadata"])),
            "AXE_VERSION": html.escape(str(results["metadata"].get("axe_core_version") or "not recorded")),
            "SCORE_VALUE": html.escape(f"{score}"),
            "SCORE_RATING": html.escape(score_label(score)),
            "CRITICAL_COUNT": html.escape(str(summary["critical_violations"])),
            "SERIOUS_COUNT": html.escape(str(summary["serious_violations"])),
            "MODERATE_COUNT": html.escape(str(summary["moderate_violations"])),
            "MINOR_COUNT": html.escape(str(summary["minor_violations"])),
            "TOTAL_ISSUES": html.escape(str(total_issues)),
            "TASK_COUNT": html.escape(str(len(rows))),
            "DOWNLOADS_NOTE": html.escape(
                brand.get(
                    "downloads_note",
                    "Use these links to review the dashboard data and download the packaged report files.",
                )
            ),
            "TASKS_NOTE": html.escape(
                brand.get(
                    "tasks_note",
                    "These issues are prioritized for remediation planning and implementation tracking.",
                )
            ),
            "SEVERITY_BARS": _render_severity_bars(summary),
            "PAGE_CARDS": _render_page_cards(pages),
            "FOOTER_TEXT": html.escape(
                brand.get(
                    "footer_text",
                    "Prepared by the accessibility audit team.",
                )
            ),
            "DOWNLOAD_LINKS": _render_download_links(download_links),
            "TASK_ROWS": _render_task_rows(rows),
        },
    )
    html_doc = _inject_dashboard_sections(html_doc, results, rows)
    Path(path).write_text(_SAL_ATTR.sub("", html_doc), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate accessibility audit deliverables from audit JSON")
    parser.add_argument("--input", required=True, help="Path to axe audit JSON")
    parser.add_argument("--output-dir", default=".", help="Directory for generated artifacts")
    parser.add_argument(
        "--embed-screenshots",
        action="store_true",
        help="Embed images in DOCX/Markdown (default: path links only for smaller reports)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = load_results(args.input)
    rows = build_task_rows(results)

    md_report = output_dir / "WCAG-AUDIT-REPORT.md"
    action_plan = output_dir / "ACCESSIBILITY-ACTION-PLAN.md"
    csv_path = output_dir / "REMEDIATION-TASKS.csv"
    docx_path = output_dir / "A11Y-CLIENT-REPORT.docx"
    html_path = output_dir / "index.html"

    md_report.write_text(
        generate_markdown_report(results, embed_screenshots=args.embed_screenshots),
        encoding="utf-8",
    )
    action_plan.write_text(generate_action_plan(results), encoding="utf-8")
    write_csv(csv_path, rows)
    build_docx(
        docx_path,
        results,
        rows,
        base_dir=Path(args.input).resolve().parent,
        embed_screenshots=args.embed_screenshots,
    )
    build_dashboard(html_path, results, rows)

    artifacts = {
        "report_markdown": str(md_report),
        "action_plan_markdown": str(action_plan),
        "remediation_csv": str(csv_path),
        "client_docx": str(docx_path),
        "dashboard_html": str(html_path),
    }
    print(json.dumps(artifacts, indent=2))


if __name__ == "__main__":
    main()
