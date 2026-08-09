#!/usr/bin/env python3
"""Framework dashboard for dd-crawl results."""

from __future__ import annotations

import html
import json
import shutil
from datetime import date
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PLUGIN_ROOT / "templates"


def load_brand() -> dict:
    path = TEMPLATES_DIR / "brand.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "agency_name": "ldnddev, LLC",
        "agency_kicker": "Site Crawl",
        "agency_logo": "assets/imgs/logo-full-black-text.svg",
        "agency_logo_dark": "assets/imgs/logo-full-white-text.svg",
        "report_title": "Site Crawl Report",
        "report_subtitle": "URL inventory and broken-link check.",
        "downloads_note": "Download CSV/JSON inventories.",
        "footer_text": "Prepared by © ldnddev, LLC",
    }


def render_template(text: str, rep: dict) -> str:
    out = text
    for k, v in rep.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def copy_assets(output_dir: Path) -> None:
    src = TEMPLATES_DIR / "assets"
    dst = output_dir / "assets"
    if not src.is_dir():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def default_web_dir(domain: str, project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    folder = f"{domain}-crawl-{date.today().isoformat()}"
    web = root / "web" / folder
    if not web.exists():
        return web
    i = 2
    while True:
        c = root / "web" / f"{folder}-{i}"
        if not c.exists():
            return c
        i += 1


def _row(url: str, m: dict, css: str = "") -> str:
    st = m.get("status")
    st_disp = html.escape(str(st if st is not None else "-"))
    cls = f' class="dd-data-table__row {css}"' if css else ' class="dd-data-table__row"'
    return (
        f"<tr{cls}>"
        f'<td class="dd-data-table__td url-cell"><a href="{html.escape(url)}" '
        f'target="_blank" rel="noopener noreferrer">{html.escape(url)}</a></td>'
        f'<td class="dd-data-table__td">{html.escape(str(m.get("type") or ""))}</td>'
        f'<td class="dd-data-table__td"><strong>{st_disp}</strong></td>'
        f'<td class="dd-data-table__td">{html.escape(str(m.get("note") or ""))}</td>'
        f'<td class="dd-data-table__td url-cell">{html.escape(str(m.get("found_on") or ""))}</td>'
        f"</tr>"
    )


def _rows_from_list(items: list[dict], row_class: str = "") -> str:
    if not items:
        return (
            '<tr class="dd-data-table__row -empty">'
            '<td class="dd-data-table__td" colspan="5">None.</td></tr>'
        )
    return "\n".join(_row(i["url"], i, row_class) for i in items)


def _downloads(files: list[tuple[str, str]]) -> str:
    parts = []
    for label, name in files:
        if not name:
            continue
        parts.append(
            f'<div class="dd-section__item dd-u-1-1 dd-u-md-12-24 l-box">'
            f'<a class="dd-button -secondary" href="{html.escape(name)}" download>'
            f"{html.escape(label)}"
            f'<span class="visually-hidden"> — {html.escape(name)}</span></a></div>'
        )
    return "\n".join(parts) if parts else "<p class='muted'>No files.</p>"


def build_dashboard(output_dir: Path, data: dict, file_basenames: dict[str, str]) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    copy_assets(output_dir)
    brand = load_brand()
    meta = data.get("meta") or {}
    summary = data.get("summary") or {}
    urls = data.get("urls") or []
    chrome = data.get("chrome") or []

    broken = [u for u in urls + chrome if u.get("is_broken")]
    redirects = [u for u in urls + chrome if u.get("is_redirect") and not u.get("is_broken")]

    spa = (
        '<p class="muted"><strong>Note:</strong> This crawler does not execute JavaScript. '
        "SPA routes only injected client-side may be missing.</p>"
    )

    robots = "respected" if summary.get("robots_used") else "not loaded / override"
    if summary.get("robots_blocked_count"):
        robots += f" ({summary['robots_blocked_count']} blocked)"

    excl = meta.get("options", {}).get("excluded") or "none"

    rep = {
        "REPORT_TITLE": html.escape(brand.get("report_title", "Site Crawl Report")),
        "REPORT_SUBTITLE": html.escape(brand.get("report_subtitle", "")),
        "AGENCY_NAME": html.escape(brand.get("agency_name", "ldnddev, LLC")),
        "AGENCY_KICKER": html.escape(brand.get("agency_kicker", "Site Crawl")),
        "AGENCY_LOGO": html.escape(brand.get("agency_logo", "assets/imgs/logo-full-black-text.svg")),
        "AGENCY_LOGO_DARK": html.escape(
            brand.get("agency_logo_dark", "assets/imgs/logo-full-white-text.svg")
        ),
        "FOOTER_TEXT": html.escape(brand.get("footer_text", "")),
        "DOWNLOADS_NOTE": html.escape(brand.get("downloads_note", "")),
        "BASE_URL": html.escape(str(meta.get("base_url") or "")),
        "GENERATED": html.escape(str(meta.get("generated") or "")),
        "PAGES_CRAWLED": html.escape(str(summary.get("pages_crawled", 0))),
        "ELAPSED": html.escape(f"{summary.get('elapsed_s', 0)}s"),
        "ROBOTS_NOTE": html.escape(robots),
        "MAX_PAGES_HIT": html.escape("yes" if summary.get("max_pages_hit") else "no"),
        "EXCLUDED": html.escape(str(excl)),
        "TOTAL": html.escape(str(summary.get("total_urls", len(urls)))),
        "INTERNAL": html.escape(str(summary.get("internal", 0))),
        "EXTERNAL": html.escape(str(summary.get("external", 0))),
        "REDIRECTS": html.escape(str(summary.get("redirects", len(redirects)))),
        "BROKEN": html.escape(str(summary.get("broken", len(broken)))),
        "CHROME": html.escape(str(summary.get("chrome_urls", len(chrome)))),
        "SPA_NOTE": spa,
        "BROKEN_ROWS": _rows_from_list(broken, "row-bad"),
        "REDIRECT_ROWS": _rows_from_list(redirects, "row-redir"),
        "ALL_ROWS": _rows_from_list(urls),
        "CHROME_ROWS": _rows_from_list(chrome),
        "DOWNLOAD_LINKS": _downloads([
            ("All URLs (CSV)", file_basenames.get("all_csv", "")),
            ("Broken URLs (CSV)", file_basenames.get("broken_csv", "")),
            ("Full data (JSON)", file_basenames.get("data_json", "")),
        ]),
    }

    html_doc = render_template(
        (TEMPLATES_DIR / "dashboard.html").read_text(encoding="utf-8"), rep
    )
    index = output_dir / "index.html"
    index.write_text(html_doc, encoding="utf-8")
    return index
