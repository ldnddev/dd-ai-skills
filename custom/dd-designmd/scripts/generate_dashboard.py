#!/usr/bin/env python3
"""Build light Framework dashboard for dd-designmd outputs."""

from __future__ import annotations

import html
import json
import re
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
        "agency_kicker": "Design System Extract",
        "agency_logo": "/assets/imgs/logo-full-black-text.svg",
        "agency_logo_dark": "/assets/imgs/logo-full-white-text.svg",
        "report_title": "Semantic Design System",
        "report_subtitle": "Evidence-bound tokens from a live URL.",
        "downloads_note": "Download the design brief and token files.",
        "footer_text": "Prepared by © ldnddev, LLC",
    }


def render_template(template_text: str, replacements: dict) -> str:
    rendered = template_text
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered


def _is_hex(value: str) -> bool:
    return bool(re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$", (value or "").strip()))


def _swatches_html(token_doc: dict, signals: dict, limit: int = 16) -> str:
    items = []
    # Prefer palette / brand tokens that are hex
    tokens = token_doc.get("tokens") or {}
    for key, body in tokens.items():
        if not key.startswith("color."):
            continue
        val = str(body.get("value") or "").strip()
        if _is_hex(val):
            items.append((key, val))
        if len(items) >= limit:
            break
    if len(items) < 4:
        for c in (signals.get("colors") or [])[:limit]:
            val = str(c.get("value") or "")
            if _is_hex(val) and all(val != v for _, v in items):
                items.append((f"raw.{len(items)+1}", val))
            if len(items) >= limit:
                break
    if not items:
        return "<li class='muted'>No hex colors extracted.</li>"
    out = []
    for name, val in items:
        out.append(
            "<li class='swatch'>"
            f"<span class='swatch__chip' style='background:{html.escape(val)}' "
            f"title='{html.escape(val)}' role='img' aria-label='Color {html.escape(val)}'></span>"
            f"<div class='swatch__meta'><div class='swatch__name'>{html.escape(name)}</div>"
            f"<div class='swatch__value'>{html.escape(val)}</div></div></li>"
        )
    return "\n".join(out)


def _chips(values: list[str], empty: str = "None found") -> str:
    if not values:
        return f"<li class='muted'>{html.escape(empty)}</li>"
    return "\n".join(
        f"<li><span class='chip'>{html.escape(v)}</span></li>" for v in values
    )


def _token_rows(token_doc: dict, limit: int = 40) -> str:
    tokens = token_doc.get("tokens") or {}
    # Prefer non-palette first
    keys = sorted(tokens.keys(), key=lambda k: (k.startswith("color.palette."), k))
    rows = []
    for key in keys[:limit]:
        body = tokens[key]
        val = str(body.get("value") or "")
        if len(val) > 120:
            val = val[:117] + "…"
        ev = str(body.get("evidence") or "")
        rows.append(
            f"<tr class='dd-data-table__row'>"
            f"<th scope='row' class='dd-data-table__td'><code>{html.escape(key)}</code></th>"
            f"<td class='dd-data-table__td'><code>{html.escape(val)}</code></td>"
            f"<td class='dd-data-table__td'>{html.escape(ev)}</td>"
            f"</tr>"
        )
    if not rows:
        return (
            "<tr class='dd-data-table__row -empty'>"
            "<td class='dd-data-table__td' colspan='3'>No tokens emitted.</td></tr>"
        )
    return "\n".join(rows)


def _framework_rows() -> str:
    mapping = [
        ("Site header / primary nav", "dd-header or gap", "Confirm against markup"),
        ("Hero / top banner", "dd-hero or gap", ""),
        ("Card grids / feature blocks", "dd-card or gap", ""),
        ("Footer", "dd-footer or gap", ""),
        ("Buttons / CTAs", "Framework button patterns or gap", ""),
        ("Forms", "Framework form patterns or gap", ""),
        ("Alerts / banners", "dd-alert / banner or gap", ""),
    ]
    return "\n".join(
        f"<tr class='dd-data-table__row'>"
        f"<td class='dd-data-table__td'>{html.escape(a)}</td>"
        f"<td class='dd-data-table__td'><code>{html.escape(b)}</code></td>"
        f"<td class='dd-data-table__td'>{html.escape(c)}</td>"
        f"</tr>"
        for a, b, c in mapping
    )


def _open_questions() -> str:
    qs = [
        "Semantic roles (primary vs accent) need human validation beyond frequency.",
        "Runtime-only styles may be missing in static mode — re-run with --deep if needed.",
        "Component anatomy should be refined from full HTML inventory.",
        "Dark mode: only document if media/class evidence exists.",
    ]
    return "\n".join(f"<li>{html.escape(q)}</li>" for q in qs)


def _download_links(filenames: list[tuple[str, str]]) -> str:
    """filenames: list of (label, filename)"""
    parts = []
    for label, filename in filenames:
        if not filename:
            continue
        parts.append(
            f'<div class="dd-section__item dd-u-1-1 dd-u-md-12-24 l-box">'
            f'<a class="dd-button -secondary" href="{html.escape(filename)}" download>'
            f"{html.escape(label)}"
            f'<span class="visually-hidden"> — download {html.escape(filename)}</span>'
            f"</a></div>"
        )
    return "\n".join(parts) if parts else "<p class='muted'>No downloadable files.</p>"


def default_web_dir(domain: str, project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    folder = f"{domain}-designmd-{date.today().isoformat()}"
    web = root / "web" / folder
    if not web.exists():
        return web
    i = 2
    while True:
        candidate = root / "web" / f"{folder}-{i}"
        if not candidate.exists():
            return candidate
        i += 1


def build_dashboard(
    output_dir: Path,
    *,
    domain: str,
    primary_url: str,
    mode: str,
    evidence_mode: str,
    pages_scanned: int,
    token_doc: dict,
    signals: dict,
    file_basenames: dict[str, str],
) -> Path:
    """
    file_basenames keys: design_md, tokens_json, tokens_css, evidence_json
    values: filenames relative to output_dir (for hrefs)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    brand = load_brand()
    tokens = token_doc.get("tokens") or {}
    fonts = [f["value"] for f in (signals.get("font_families") or [])[:6]]
    sizes = [f["value"] for f in (signals.get("font_sizes") or [])[:10]]
    spaces = [s["value"] for s in (signals.get("spacing_values") or [])[:12]]
    radii = [r["value"] for r in (signals.get("radii") or [])[:8]]
    primary_font = fonts[0] if fonts else "system-ui, sans-serif"

    downloads = [
        ("Design brief (Markdown)", file_basenames.get("design_md", "")),
        ("Tokens (JSON)", file_basenames.get("tokens_json", "")),
        ("Tokens (CSS)", file_basenames.get("tokens_css", "")),
        ("Pipeline evidence (JSON)", file_basenames.get("evidence_json", "")),
    ]

    generated = (token_doc.get("meta") or {}).get("generated") or ""
    replacements = {
        "REPORT_TITLE": html.escape(brand.get("report_title", "Semantic Design System")),
        "REPORT_SUBTITLE": html.escape(brand.get("report_subtitle", "")),
        "AGENCY_NAME": html.escape(brand.get("agency_name", "ldnddev, LLC")),
        "AGENCY_KICKER": html.escape(brand.get("agency_kicker", "Design System Extract")),
        "AGENCY_LOGO": html.escape(brand.get("agency_logo", "/assets/imgs/logo-full-black-text.svg")),
        "AGENCY_LOGO_DARK": html.escape(
            brand.get("agency_logo_dark", "/assets/imgs/logo-full-white-text.svg")
        ),
        "FOOTER_TEXT": html.escape(brand.get("footer_text", "")),
        "DOWNLOADS_NOTE": html.escape(brand.get("downloads_note", "")),
        "DOMAIN": html.escape(domain),
        "SOURCE_URL": html.escape(primary_url),
        "GENERATED": html.escape(str(generated)),
        "CRAWL_MODE": html.escape(mode),
        "EVIDENCE_MODE": html.escape(evidence_mode),
        "PAGE_COUNT": html.escape(str(pages_scanned)),
        "TOKEN_COUNT": html.escape(str(len(tokens))),
        "COLOR_SWATCHES": _swatches_html(token_doc, signals),
        "FONT_CHIPS": _chips(fonts, "No font-family rules extracted"),
        "SIZE_CHIPS": _chips(sizes, "No font-size rules extracted"),
        "SPACE_CHIPS": _chips(spaces, "No spacing lengths extracted"),
        "RADIUS_CHIPS": _chips(radii, "No border-radius rules extracted"),
        "PRIMARY_FONT": html.escape(primary_font),
        "TOKEN_ROWS": _token_rows(token_doc),
        "FRAMEWORK_ROWS": _framework_rows(),
        "OPEN_QUESTIONS": _open_questions(),
        "DOWNLOAD_LINKS": _download_links(downloads),
    }

    template_path = TEMPLATES_DIR / "dashboard.html"
    html_doc = render_template(template_path.read_text(encoding="utf-8"), replacements)
    index_path = output_dir / "index.html"
    index_path.write_text(html_doc, encoding="utf-8")
    return index_path
