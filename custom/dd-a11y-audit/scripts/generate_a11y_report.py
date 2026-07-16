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
import shutil
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"


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


def ensure_brand_asset(output_dir, relative_asset_path):
    for candidate in (TEMPLATES_DIR / relative_asset_path, SKILL_DIR / relative_asset_path):
        if candidate.exists():
            destination = output_dir / relative_asset_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate, destination)
            return relative_asset_path
    return relative_asset_path


def format_audit_date(timestamp):
    if not timestamp:
        return "—"
    try:
        ts = timestamp.replace("Z", "+00:00") if isinstance(timestamp, str) else timestamp
        return datetime.fromisoformat(ts).strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return str(timestamp)


def score_label(score):
    if score >= 90:
        return "AA Compliant"
    if score >= 75:
        return "A Compliant"
    if score >= 50:
        return "Needs Improvement"
    if score >= 25:
        return "Significant Barriers"
    return "Critical Barriers"


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


def principle_score(results, principle):
    total = max(1, results["summary"]["total_violations"])
    count = results["principle_counts"].get(principle, 0)
    return max(0, round(100 - ((count / total) * 35)))


def page_principle_score(page, principle):
    total = max(1, page.get("summary", {}).get("total_violations", 0))
    count = page.get("principle_counts", {}).get(principle, 0)
    return max(0, round(100 - ((count / total) * 35)))


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


def build_task_rows(results):
    rows = []
    global_index = 1
    for page in get_pages(results):
        page_url = page.get("page_url") or page.get("metadata", {}).get("url", "")
        page_slug = page.get("page_slug", "page")
        page_screenshot = page.get("screenshots", {}).get("full_page")
        screenshot_lookup = {
            item.get("task_id"): item.get("path")
            for item in page.get("screenshots", {}).get("issues", [])
            if item.get("task_id")
        }
        for local_index, violation in enumerate(page.get("violations", []), start=1):
            local_task_id = f"A11Y-{local_index:03d}"
            rows.append({
                "task_id": f"A11Y-{global_index:03d}",
                "page_url": page_url,
                "page_slug": page_slug,
                "page_screenshot": page_screenshot or "",
                "issue_screenshot": screenshot_lookup.get(local_task_id, "") or "",
                "priority": severity_label(violation.get("impact")),
                "rule_id": violation.get("id", ""),
                "issue": violation.get("description", ""),
                "wcag_tags": ", ".join(violation.get("wcag_tags", [])),
                "selector": first_target(violation),
                "evidence": first_html_preview(violation),
                "fix": violation.get("help", ""),
                "timeline": severity_timeline(violation.get("impact")),
                "owner": owner_for_impact(violation.get("impact")),
                "estimated_hours": estimate_effort(violation.get("nodes_count", 1), violation.get("impact")),
                "status": "Open",
            })
            global_index += 1
    return rows


def generate_markdown_report(results):
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
        f"**Overall Score:** {score}/100",
        f"**Compliance Rating:** {score_label(score)}",
        f"**WCAG Target:** Level {meta['wcag_level']}",
        f"**Pages Audited:** {len(pages)}",
        "",
        f"**Critical Issues:** {summary['critical_violations']}",
        f"**Serious Issues:** {summary['serious_violations']}",
        f"**Moderate Issues:** {summary['moderate_violations']}",
        f"**Minor Issues:** {summary['minor_violations']}",
        "",
        "## WCAG Principle Scores",
        "",
        "| Principle | Score | Violations |",
        "|-----------|-------|------------|",
        f"| Perceivable | {principle_score(results, 'perceivable')}% | {results['principle_counts'].get('perceivable', 0)} |",
        f"| Operable | {principle_score(results, 'operable')}% | {results['principle_counts'].get('operable', 0)} |",
        f"| Understandable | {principle_score(results, 'understandable')}% | {results['principle_counts'].get('understandable', 0)} |",
        f"| Robust | {principle_score(results, 'robust')}% | {results['principle_counts'].get('robust', 0)} |",
        "",
        "## Findings",
        "",
    ]

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
            full_page = page.get("screenshots", {}).get("full_page")
            if full_page:
                lines.extend([
                    f"![Full page screenshot]({full_page})",
                    "",
                ])
            for local_index, violation in enumerate(page.get("violations", []), start=1):
                local_task_id = f"A11Y-{local_index:03d}"
                shot_lookup = {
                    item.get("task_id"): item.get("path")
                    for item in page.get("screenshots", {}).get("issues", [])
                    if item.get("task_id")
                }
                row = next(
                    item for item in rows
                    if item["page_url"] == page_url and item["rule_id"] == violation.get("id")
                    and item["selector"] == first_target(violation)
                )
                lines.extend([
                    f"#### {row['task_id']} — {row['issue']}",
                    f"**Severity:** {row['priority']}",
                    f"**WCAG Tags:** {row['wcag_tags'] or 'n/a'}",
                    f"**Selector:** `{row['selector'] or 'n/a'}`",
                    f"**Occurrences:** {violation.get('nodes_count', 0)}",
                    f"**Fix:** {row['fix']}",
                    f"**Evidence:** `{row['evidence'][:180] or 'n/a'}`",
                ])
                if shot_lookup.get(local_task_id):
                    lines.append(f"![Issue screenshot]({shot_lookup[local_task_id]})")
                lines.append("")

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


def generate_action_plan(results):
    summary = results["summary"]
    rows = build_task_rows(results)
    pages = get_pages(results)
    lines = [
        "# Accessibility Action Plan",
        f"<!-- URL: {results['metadata']['url']} -->",
        f"<!-- Generated: {results['metadata']['timestamp']} -->",
        "",
        "## Priority Matrix",
        "",
        "| Priority | Count | Timeline | Owner |",
        "|----------|-------|----------|-------|",
        f"| Critical | {summary['critical_violations']} | Immediate (1-2 days) | Frontend Development |",
        f"| Serious | {summary['serious_violations']} | Week 1 | Frontend Development |",
        f"| Moderate | {summary['moderate_violations']} | Month 1 | Design + Development |",
        f"| Minor | {summary['minor_violations']} | Month 2-3 | Product / Maintenance |",
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
        "task_id", "page_url", "page_slug", "page_screenshot", "issue_screenshot",
        "priority", "rule_id", "issue", "wcag_tags", "selector",
        "evidence", "fix", "timeline", "owner", "estimated_hours", "status",
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


def build_docx(path, results, rows):
    body = []
    meta = results["metadata"]
    summary = results["summary"]
    utc_now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    pages = get_pages(results)
    body.append(paragraph_xml("Accessibility Audit Client Report"))
    body.append(paragraph_xml(f"URL: {meta['url']}"))
    body.append(paragraph_xml(f"Generated: {meta['timestamp']}"))
    body.append(paragraph_xml(f"Overall score: {meta['score']}/100 ({score_label(meta['score'])})"))
    body.append(paragraph_xml(f"Pages audited: {len(pages)}"))
    body.append(paragraph_xml(
        f"Critical: {summary['critical_violations']}, Serious: {summary['serious_violations']}, "
        f"Moderate: {summary['moderate_violations']}, Minor: {summary['minor_violations']}"
    ))
    body.append(paragraph_xml(" "))
    if not rows:
        body.append(paragraph_xml("No automated violations were detected."))
    else:
        for page in pages:
            page_url = page.get("page_url") or page.get("metadata", {}).get("url", "")
            body.append(paragraph_xml(f"Page: {page_url}"))
            full_page = page.get("screenshots", {}).get("full_page")
            if full_page:
                body.append(paragraph_xml(f"Full page screenshot: {full_page}"))
            for row in [item for item in rows if item["page_url"] == page_url]:
                body.append(paragraph_xml(
                    f"{row['task_id']} | {row['priority']} | {row['issue']} | "
                    f"Owner: {row['owner']} | Timeline: {row['timeline']}"
                ))
                body.append(paragraph_xml(f"Fix: {row['fix']}"))
                if row["issue_screenshot"]:
                    body.append(paragraph_xml(f"Issue screenshot: {row['issue_screenshot']}"))

    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        f"<w:body>{''.join(body)}"
        "<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"1440\" "
        "w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" w:header=\"708\" "
        "w:footer=\"708\" w:gutter=\"0\"/></w:sectPr></w:body></w:document>"
    )

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

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


def copy_framework_assets(output_dir):
    """Copy compiled framework CSS/JS + favicon/imgs into the report bundle."""
    src = TEMPLATES_DIR / "assets"
    if not src.is_dir():
        return
    dst = Path(output_dir) / "assets"
    for sub in ("css", "js", "favicon", "imgs"):
        candidate = src / sub
        if candidate.is_dir():
            shutil.copytree(candidate, dst / sub, dirs_exist_ok=True)


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
    """dd-card grid — one card per audited page. The URL is the card <h3> title
    (M1); the screenshot is illustrative → alt="" (1.1.1), reached via a
    self-describing link (2.4.4/2.5.3)."""
    cards = []
    for page in pages:
        page_url = page.get("page_url") or page.get("metadata", {}).get("url", "")
        shot = page.get("screenshots", {}).get("full_page")
        score_val = page.get("metadata", {}).get("score", "n/a")
        esc_url = html.escape(page_url)
        image = ""
        extra = ""
        if shot:
            esc_shot = html.escape(shot)
            image = (
                f'<div class="dd-card__image">'
                f'<img src="{esc_shot}" alt="" class="dd-image" loading="lazy"></div>'
            )
            extra = (
                f'<div class="dd-card__links dd-g"><div class="dd-card__link">'
                f'<a href="{esc_shot}" class="dd-button -secondary">View screenshot'
                f'<span class="visually-hidden"> of {esc_url}</span></a></div></div>'
            )
        else:
            extra = '<p class="muted">No screenshot captured for this page.</p>'
        cards.append(
            f'<div class="dd-card__item l-box dd-u-1-1 dd-u-md-12-24" data-aos="fade-up">'
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
        # Screenshot cell needs a unique, context-bearing accessible name
        # (2.4.4/2.5.3) — the visible word ("Issue"/"Page") is a substring of it.
        if r.get("issue_screenshot"):
            shot = (
                f'<a href="{html.escape(r["issue_screenshot"])}">Issue'
                f'<span class="visually-hidden"> screenshot for {html.escape(r["task_id"])}</span></a>'
            )
        elif r.get("page_screenshot"):
            shot = (
                f'<a href="{html.escape(r["page_screenshot"])}">Page'
                f'<span class="visually-hidden"> screenshot for {html.escape(r["task_id"])}</span></a>'
            )
        else:
            shot = '<span class="muted">n/a</span>'
        out.append(
            f'<tr class="dd-data-table__row">'
            f'<th scope="row" class="dd-data-table__td">{html.escape(r["task_id"])}</th>'
            f'<td class="dd-data-table__td">{html.escape(r["page_url"])}</td>'
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


def build_dashboard(path, results, rows):
    template_path = TEMPLATES_DIR / "dashboard.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Dashboard template not found: {template_path}")

    brand = load_brand_config()
    logo_path = ensure_brand_asset(
        path.parent, brand.get("agency_logo", "assets/imgs/logo-full-black-text.svg")
    )
    logo_dark_path = ensure_brand_asset(
        path.parent, brand.get("agency_logo_dark", "assets/imgs/logo-full-white-text.svg")
    )
    copy_framework_assets(path.parent)
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
            "WCAG_TARGET": html.escape(f"Level {results['metadata']['wcag_level']}"),
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
    Path(path).write_text(html_doc, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate accessibility audit deliverables from audit JSON")
    parser.add_argument("--input", required=True, help="Path to axe audit JSON")
    parser.add_argument("--output-dir", default=".", help="Directory for generated artifacts")
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

    md_report.write_text(generate_markdown_report(results), encoding="utf-8")
    action_plan.write_text(generate_action_plan(results), encoding="utf-8")
    write_csv(csv_path, rows)
    build_docx(docx_path, results, rows)
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
