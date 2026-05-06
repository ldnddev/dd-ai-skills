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
    source = SKILL_DIR / relative_asset_path
    if not source.exists():
        return relative_asset_path
    destination = output_dir / relative_asset_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return relative_asset_path


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


def build_dashboard(path, results, rows):
    template_path = TEMPLATES_DIR / "dashboard.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Dashboard template not found: {template_path}")

    brand = load_brand_config()
    logo_path = ensure_brand_asset(path.parent, brand.get("agency_logo", "assets/agency-logo.svg"))
    score = results["metadata"]["score"]
    pages = get_pages(results)
    download_links = [
        ("WCAG Audit Report", "WCAG-AUDIT-REPORT.md"),
        ("Accessibility Action Plan", "ACCESSIBILITY-ACTION-PLAN.md"),
        ("Remediation Tasks CSV", "REMEDIATION-TASKS.csv"),
        ("Client DOCX Report", "A11Y-CLIENT-REPORT.docx"),
        ("Raw axe Results JSON", "axe-results.json"),
    ]
    downloads = "".join(
        (
            '<a class="download-link" href="{href}">'
            '<div class="download-label">{label}</div>'
            '<div class="download-file">{filename}</div>'
            '</a>'
        ).format(
            href=html.escape(filename),
            label=html.escape(label),
            filename=html.escape(filename),
        )
        for label, filename in download_links
    )
    cards = []
    for row in rows:
        screenshot_cell = "n/a"
        if row["issue_screenshot"]:
            screenshot_cell = (
                f'<a href="{html.escape(row["issue_screenshot"])}">Issue</a>'
            )
        elif row["page_screenshot"]:
            screenshot_cell = (
                f'<a href="{html.escape(row["page_screenshot"])}">Page</a>'
            )
        cards.append(
            f"""
            <tr>
              <td>{html.escape(row['task_id'])}</td>
              <td>{html.escape(row['page_url'])}</td>
              <td><span class="priority-pill">{html.escape(row['priority'])}</span></td>
              <td>{html.escape(row['issue'])}</td>
              <td>{html.escape(row['owner'])}</td>
              <td>{html.escape(row['timeline'])}</td>
              <td>{html.escape(row['selector'])}</td>
              <td>{screenshot_cell}</td>
            </tr>
            """
        )
    table_rows = "".join(cards) or "<tr><td colspan='8'>No violations found.</td></tr>"
    page_sections = []
    for page in pages:
        page_url = page.get("page_url") or page.get("metadata", {}).get("url", "")
        full_page = page.get("screenshots", {}).get("full_page")
        image = f'<img class="page-preview" src="{html.escape(full_page)}" alt="Screenshot of {html.escape(page_url)}">' if full_page else ""
        page_sections.append(
            f"""
            <article class="page-card">
              <div class="meta-label">Audited Page</div>
              <div class="meta-value">{html.escape(page_url)}</div>
              <div class="meta-value">Score: {html.escape(str(page.get('metadata', {}).get('score', 'n/a')))} / 100</div>
              {image}
            </article>
            """
        )
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
            "AUDIT_URL": html.escape(results["metadata"]["url"]),
            "AUDIT_DATE": html.escape(results["metadata"]["timestamp"]),
            "WCAG_TARGET": html.escape(f"Level {results['metadata']['wcag_level']}"),
            "SCORE_VALUE": html.escape(f"{score}"),
            "SCORE_RATING": html.escape(score_label(score)),
            "CRITICAL_COUNT": html.escape(str(results["summary"]["critical_violations"])),
            "SERIOUS_COUNT": html.escape(str(results["summary"]["serious_violations"])),
            "MODERATE_COUNT": html.escape(str(results["summary"]["moderate_violations"])),
            "MINOR_COUNT": html.escape(str(results["summary"]["minor_violations"])),
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
            "PAGE_SUMMARY_SECTIONS": "".join(page_sections),
            "FOOTER_TEXT": html.escape(
                brand.get(
                    "footer_text",
                    "Prepared by the accessibility audit team.",
                )
            ),
            "DOWNLOAD_LINKS": downloads,
            "TASK_ROWS": table_rows,
            "DISPLAY_FONT": brand.get("display_font", "Georgia, serif"),
            "BODY_FONT": brand.get("body_font", "Arial, sans-serif"),
            "UI_FONT": brand.get("ui_font", "Arial, sans-serif"),
            "BRAND_BG": brand.get("brand_bg", "#f5f1e8"),
            "BRAND_BG_TOP": brand.get("brand_bg_top", "#efe6d6"),
            "BRAND_SURFACE": brand.get("brand_surface", "#fffdf8"),
            "BRAND_TEXT": brand.get("brand_text", "#1e1e1b"),
            "BRAND_MUTED": brand.get("brand_muted", "#665f57"),
            "BRAND_ACCENT": brand.get("brand_accent", "#b24c2a"),
            "BRAND_ACCENT_2": brand.get("brand_accent_2", "#2d6a4f"),
            "BRAND_LINE": brand.get("brand_line", "#dbcdb6"),
            "BRAND_SHADOW": brand.get("brand_shadow", "rgba(0,0,0,.06)"),
            "BRAND_GLOW_1": brand.get("brand_glow_1", "rgba(182, 90, 46, 0.14)"),
            "BRAND_GLOW_2": brand.get("brand_glow_2", "rgba(15, 118, 110, 0.12)"),
            "HERO_BG_1": brand.get("hero_bg_1", "#f7efe3"),
            "HERO_BG_2": brand.get("hero_bg_2", "#f3e5d9"),
            "TABLE_HEAD_BG": brand.get("table_head_bg", "#f3eadb"),
            "PRIORITY_BG": brand.get("priority_bg", "#f8e0d7"),
            "PRIORITY_TEXT": brand.get("priority_text", "#8d3f1e"),
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
