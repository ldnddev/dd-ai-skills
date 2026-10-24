#!/usr/bin/env python3
"""Build the master overview dashboard from nested child bundles. Does not rewrite children."""

from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PLUGIN_ROOT / "templates"

V1_FOLDERS = (
    ("dd-crawl", "crawl", "Crawl"),
    ("dd-seo", "seo", "SEO"),
    ("dd-site-speed", "speed", "Page speed"),
)


def load_brand() -> dict:
    path = TEMPLATES_DIR / "brand.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "agency_name": "ldnddev, LLC",
        "agency_kicker": "Site Audit",
        "agency_logo": "/assets/imgs/logo-full-black-text.svg",
        "agency_logo_dark": "/assets/imgs/logo-full-white-text.svg",
        "report_title": "Site Audit Overview",
        "report_subtitle": "Cover dashboard for crawl, SEO, and page-speed reports.",
        "downloads_note": "Keep this folder together so relative links work.",
        "footer_text": "Prepared by © ldnddev, LLC — dd-audit",
    }


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _csv_row_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh))
    except OSError:
        return None
    if not rows:
        return 0
    return max(0, len(rows) - 1)


def _read_error(folder: Path) -> str | None:
    for name in ("error.txt", "error.json"):
        path = folder / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if name.endswith(".json"):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    return str(data.get("error") or data.get("message") or text)[:500]
            except json.JSONDecodeError:
                pass
        return text[:500] or None
    return None


def _stats_from_pairs(pairs: list[tuple[str, object]]) -> list[dict]:
    out = []
    for label, value in pairs:
        if value is None or value == "":
            continue
        out.append({"label": label, "value": value})
    return out


def crawl_headlines(data: dict | None) -> list[dict]:
    if not data:
        return []
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    return _stats_from_pairs(
        [
            ("Pages crawled", summary.get("pages_crawled")),
            ("URLs", summary.get("total_urls")),
            ("Broken", summary.get("broken")),
            ("Redirects", summary.get("redirects")),
        ]
    )


def seo_headlines(folder: Path, data: dict | None) -> list[dict]:
    pairs: list[tuple[str, object]] = []
    if data:
        scores = data.get("scores") if isinstance(data.get("scores"), dict) else {}
        overall = scores.get("overall", data.get("overall"))
        if overall is not None:
            pairs.append(("Overall", overall))
    tasks = _csv_row_count(folder / "tasks.csv")
    if tasks is not None:
        pairs.append(("Tasks", tasks))
    reports = []
    for name in ("FULL-AUDIT-REPORT.md", "FULL-AUDIT-REPORT.docx", "ACTION-PLAN.md", "ACTION-PLAN.docx"):
        if (folder / name).is_file():
            reports.append(name)
    if reports:
        pairs.append(("Reports", ", ".join(reports[:3])))
    return _stats_from_pairs(pairs)


def speed_headlines(data: dict | None) -> list[dict]:
    if not data:
        return []
    strat = data.get("strategies") if isinstance(data.get("strategies"), dict) else {}
    pages = data.get("pages") if isinstance(data.get("pages"), list) else []
    if not strat and pages and isinstance(pages[0], dict):
        strat = pages[0].get("strategies") or {}
    mobile = strat.get("mobile") if isinstance(strat.get("mobile"), dict) else {}
    desktop = strat.get("desktop") if isinstance(strat.get("desktop"), dict) else {}
    limits = data.get("limitations")
    n_limits = len(limits) if isinstance(limits, list) else None
    return _stats_from_pairs(
        [
            ("Mobile PSI", mobile.get("performance_score")),
            ("Desktop PSI", desktop.get("performance_score")),
            ("Limitations", n_limits if n_limits else None),
        ]
    )


def inspect_child(parent: Path, module_id: str, folder_name: str, title: str) -> dict:
    folder = parent / folder_name
    index = folder / "index.html"
    data = _load_json(folder / "data.json")
    err = _read_error(folder)
    if not folder.is_dir():
        status = "failed"
        error = err or f"Missing {folder_name}/ (child did not run or was not written here)"
        stats: list[dict] = []
    elif index.is_file():
        status = "ok"
        error = None
        if module_id == "dd-crawl":
            stats = crawl_headlines(data)
        elif module_id == "dd-seo":
            stats = seo_headlines(folder, data)
        else:
            stats = speed_headlines(data)
        if not stats:
            stats = [{"label": "Dashboard", "value": "present"}]
    else:
        status = "failed"
        error = err or f"{folder_name}/index.html not found — child skill did not finish"
        if module_id == "dd-crawl":
            stats = crawl_headlines(data)
        elif module_id == "dd-seo":
            stats = seo_headlines(folder, data)
        else:
            stats = speed_headlines(data)
    return {
        "id": module_id,
        "folder": folder_name,
        "title": title,
        "status": status,
        "href": f"{folder_name}/index.html" if status == "ok" else None,
        "error": error,
        "stats": stats,
        "has_data_json": data is not None,
    }


def inspect_parent(parent: Path) -> dict:
    plan = _load_json(parent / "plan.json") or {}
    modules = [
        inspect_child(parent, mid, folder, title) for mid, folder, title in V1_FOLDERS
    ]
    ok_n = sum(1 for m in modules if m["status"] == "ok")
    failed_n = sum(1 for m in modules if m["status"] == "failed")
    return {
        "primary_url": plan.get("primary_url") or "",
        "domain": plan.get("domain") or parent.name.split("-site-audit-")[0],
        "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "parent": str(parent.resolve()),
        "modules": modules,
        "ok_count": ok_n,
        "failed_count": failed_n,
        "compare_note": (
            "dd-site-compare is required to be installed for dd-audit, "
            "but is not run in v1 (needs confirmed peer URLs)."
        ),
    }


def _stat_dl(stats: list[dict]) -> str:
    if not stats:
        return "<p class='muted'>No headlines extracted — open the child dashboard.</p>"
    rows = []
    for item in stats:
        rows.append(
            "<div class='app-summary__row'>"
            f"<dt>{html.escape(str(item['label']))}</dt>"
            f"<dd>{html.escape(str(item['value']))}</dd>"
            "</div>"
        )
    return "<dl class='app-summary'>" + "".join(rows) + "</dl>"


def _module_card(mod: dict) -> str:
    status = mod["status"]
    badge = "OK" if status == "ok" else "Failed"
    badge_class = "ok" if status == "ok" else "bad"
    if status == "ok" and mod.get("href"):
        action = (
            f"<a class='dd-button -secondary' href='{html.escape(mod['href'])}'>"
            f"Open {html.escape(mod['title'])} dashboard</a>"
        )
    else:
        action = "<p class='muted'>No child dashboard to open.</p>"
    err = ""
    if mod.get("error"):
        err = f"<p class='error'>{html.escape(str(mod['error']))}</p>"
    return (
        "<article class='mod-card'>"
        f"<h3>{html.escape(mod['title'])} "
        f"<span class='badge {badge_class}'>{badge}</span></h3>"
        f"{_stat_dl(mod.get('stats') or [])}"
        f"{err}{action}"
        "</article>"
    )


def render_dashboard(rollup: dict) -> str:
    brand = load_brand()
    template = (TEMPLATES_DIR / "dashboard.html").read_text(encoding="utf-8")
    cards = "\n".join(_module_card(m) for m in rollup.get("modules") or [])
    replacements = {
        "REPORT_TITLE": html.escape(brand.get("report_title", "Site Audit Overview")),
        "REPORT_SUBTITLE": html.escape(brand.get("report_subtitle", "")),
        "AGENCY_NAME": html.escape(brand.get("agency_name", "ldnddev, LLC")),
        "AGENCY_KICKER": html.escape(brand.get("agency_kicker", "Site Audit")),
        "AGENCY_LOGO": html.escape(
            brand.get("agency_logo", "/assets/imgs/logo-full-black-text.svg")
        ),
        "AGENCY_LOGO_DARK": html.escape(
            brand.get("agency_logo_dark", "/assets/imgs/logo-full-white-text.svg")
        ),
        "FOOTER_TEXT": html.escape(brand.get("footer_text", "")),
        "DOWNLOADS_NOTE": html.escape(brand.get("downloads_note", "")),
        "DOMAIN": html.escape(str(rollup.get("domain") or "")),
        "SOURCE_URL": html.escape(str(rollup.get("primary_url") or "")),
        "GENERATED": html.escape(str(rollup.get("generated") or "")),
        "OK_COUNT": html.escape(str(rollup.get("ok_count") or 0)),
        "FAILED_COUNT": html.escape(str(rollup.get("failed_count") or 0)),
        "COMPARE_NOTE": html.escape(str(rollup.get("compare_note") or "")),
        "MODULE_CARDS": cards,
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def assemble(parent: Path) -> dict:
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    rollup = inspect_parent(parent)
    (parent / "data.json").write_text(
        json.dumps(rollup, indent=2) + "\n", encoding="utf-8"
    )
    index = parent / "index.html"
    index.write_text(render_dashboard(rollup), encoding="utf-8")
    rollup["dashboard_html"] = str(index.resolve())
    rollup["data_json"] = str((parent / "data.json").resolve())
    return rollup
