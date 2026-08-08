#!/usr/bin/env python3
"""
Orchestrate semantic design-system extraction for dd-designmd.

Usage:
  python3 run_designmd.py https://www.ldnddev.com
  python3 run_designmd.py https://a.com https://a.com/about --force
  python3 run_designmd.py --urls-file urls.txt --deep   # deep reserved

Writes to CWD (default):
  {domain}-design.md
  {domain}-tokens.json
  {domain}-tokens.css
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from domain_util import domain_from_url, normalize_url  # noqa: E402
from emit_tokens import build_token_doc, tokens_to_css  # noqa: E402
from extract_css import collect_css_for_page  # noqa: E402
from extract_design_signals import extract_signals  # noqa: E402
from fetch_pages import collect_urls, fetch_html  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _table(rows: list[tuple[str, str, str]]) -> str:
    lines = [
        "| Name | Value | Evidence |",
        "|------|-------|----------|",
    ]
    for name, value, evidence in rows:
        v = str(value).replace("|", "\\|").replace("\n", " ")
        e = str(evidence).replace("|", "\\|")
        lines.append(f"| `{name}` | `{v}` | {e} |")
    return "\n".join(lines)


def render_design_md(
    *,
    domain: str,
    primary_url: str,
    pages: list[dict],
    mode: str,
    evidence_mode: str,
    signals: dict,
    token_doc: dict,
) -> str:
    scanned = []
    for p in pages:
        if p.get("error"):
            scanned.append(f"- `{p.get('url')}` — error: {p.get('error')}")
        else:
            scanned.append(
                f"- `{p.get('final_url') or p.get('url')}` "
                f"(status {p.get('status')})"
            )

    token_rows = []
    for key, body in (token_doc.get("tokens") or {}).items():
        # Prefer semantic-ish keys in the main table (skip long palette dump in MD? include top)
        token_rows.append((key, body.get("value", ""), body.get("evidence", "")))

    # Split semantic candidates vs palette
    semantic = [r for r in token_rows if not r[0].startswith("color.palette.")]
    palette = [r for r in token_rows if r[0].startswith("color.palette.")][:12]

    colors_raw = signals.get("colors") or []
    fonts = signals.get("font_families") or []
    sizes = signals.get("font_sizes") or []
    spaces = signals.get("spacing_values") or []
    radii = signals.get("radii") or []
    shadows = signals.get("shadows") or []
    bps = signals.get("breakpoints") or []

    md = f"""# {domain} — Semantic Design System

## Meta

| Field | Value |
|-------|-------|
| Primary URL | {primary_url} |
| Domain | {domain} |
| Generated | {_now()} |
| Crawl mode | {mode} |
| Evidence mode | {evidence_mode} |
| Pages scanned | {len(pages)} |
| Confidence | Medium — static CSS/HTML extraction; semantic names are provisional promotions of measured values |

### Pages scanned

{chr(10).join(scanned) if scanned else "- (none)"}

## Product / brand snapshot

Content below is limited to what appears on the scanned pages and measured CSS.  
**No invented mission, voice, or brand guidelines.** If the site does not state brand principles, this section stays factual (title/product surface only).

- **Document title / surface:** see scanned page HTML `<title>` and visible H1s in implementation notes appendix when available.
- **Official brand story:** only include if present on-page; otherwise: *not stated on scanned pages*.

## Foundations

### Color (raw, measured)

Top colors by CSS occurrence (not a brand book):

{_table([(f"raw.color.{i:02d}", c['value'], f"count={c['count']}") for i, c in enumerate(colors_raw[:16], 1)]) if colors_raw else "_No colors extracted._"}

### Typography (raw, measured)

**Families**

{_table([(f"raw.font.family.{i:02d}", f['value'], f"count={f['count']}") for i, f in enumerate(fonts[:8], 1)]) if fonts else "_No font-family rules extracted._"}

**Sizes**

{_table([(f"raw.font.size.{i:02d}", f['value'], f"count={f['count']}") for i, f in enumerate(sizes[:12], 1)]) if sizes else "_No font-size rules extracted._"}

### Spacing (raw lengths seen in layout props)

{_table([(f"raw.space.{i:02d}", s['value'], f"count={s['count']}") for i, s in enumerate(spaces[:16], 1)]) if spaces else "_No spacing lengths extracted._"}

### Radius

{_table([(f"raw.radius.{i:02d}", r['value'], f"count={r['count']}") for i, r in enumerate(radii[:10], 1)]) if radii else "_No border-radius rules extracted._"}

### Elevation / shadow

{_table([(f"raw.shadow.{i:02d}", s['value'][:80], f"count={s['count']}") for i, s in enumerate(shadows[:8], 1)]) if shadows else "_No box-shadow rules extracted._"}

### Motion

_Not extracted in static mode unless present as CSS transitions/animations in a future pass. Mark as missing if not listed in appendix evidence samples._

### Breakpoints

{_table([(f"raw.breakpoint.{i:02d}", b['value'], f"count={b['count']}") for i, b in enumerate(bps[:12], 1)]) if bps else "_No @media queries extracted._"}

## Semantic tokens

Provisional semantic names mapped from **measured** CSS. Rank/order is frequency-based, **not** an official brand scale.

### Core semantic candidates

{_table(semantic[:40]) if semantic else "_No tokens emitted._"}

### Palette ranks (frequency)

{_table(palette) if palette else "_No palette ranks._"}

Machine-readable dump: `{domain}-tokens.json` and `{domain}-tokens.css`.

## Components

Inventory is **observation-oriented**. Each item should be refined by the Design System Lead agent using page HTML structure. Static pipeline seeds common chrome patterns when class/CSS evidence exists.

| Component | Observation | Evidence basis | States/variants (if observed) |
|-----------|-------------|----------------|--------------------------------|
| Button / CTA | Present if button/link button styles exist in CSS/HTML | CSS class/button selectors | hover/focus if rules found |
| Navigation | Header/nav links collected for crawl | HTML `<nav>` / header links | — |
| Form controls | Input/label styles if present | CSS form selectors | — |
| Card / surface | Card-like padding+radius clusters | CSS radius + spacing co-occurrence | — |
| Footer | Footer region if present | HTML footer | — |

Agent must expand this table with concrete class names and anatomy from scanned HTML. Do not invent components not present.

## Patterns / page templates

Describe only templates actually scanned (home, pricing, etc.). For each page URL, note primary layout regions observed (header, hero, main, footer).

| Page | Pattern notes |
|------|----------------|
| (fill from scanned URLs) | Header / main / footer composition |

## Iconography & media

- Report icon fonts or SVG systems only if CSS/HTML references them (e.g. Font Awesome content codes, `<svg>` usage).
- Do not invent an icon library.

## Do / Don’t

| Do | Don’t |
|----|-------|
| Reuse measured tokens from `{domain}-tokens.css` as a starting point | Treat frequency rank as official brand hierarchy without validation |
| Cite CSS/HTML evidence when adding tokens | Invent brand mission, personality, or palette not on-site |
| Map components honestly to Framework gaps | Propose a full rebrand |
| Keep a11y/SEO work in their own skills | Score a11y or SEO inside this document |

## Implementation notes

- Extraction mode: **{evidence_mode}**
- CSS custom properties found: {len(signals.get("css_variables") or [])}
- Inferred stack hints (low confidence unless clear): class naming, known CMS markers in HTML if present — agent should note WordPress/theme/utility CSS only with evidence.
- Deep Playwright sampling: {"enabled" if evidence_mode == "deep" else "not run"}

## ldnddev Framework mapping

Always present. Map **observed** UI to Framework components; use “no match / gap” when appropriate.

| Observed UI | Framework map | Notes |
|-------------|---------------|-------|
| Site header / primary nav | `dd-header` or gap | Confirm against actual markup |
| Hero / top banner | `dd-hero` or gap | |
| Card grids / feature blocks | `dd-card` or gap | |
| Footer | `dd-footer` or gap | |
| Buttons / CTAs | Framework button patterns or gap | |
| Forms | Framework form patterns or gap | |
| Alerts / banners | `dd-alert` / banner or gap | |

Load `dd-framework` for authoring details; do not duplicate full component specs here.

## Open questions & missing evidence

- Semantic roles (primary vs accent) need human validation beyond frequency.
- Runtime-only styles (CSS-in-JS injected after load) may be missing in static mode — re-run with `--deep` if available.
- Component anatomy incomplete until HTML class inventory is expanded by the agent.
- Dark mode: only document if media/class evidence exists.

## Appendix — evidence samples

```json
{json.dumps(signals.get("evidence_samples") or {}, indent=2)}
```
"""
    return md


def run(
    urls: list[str],
    *,
    force: bool = False,
    max_extra: int = 8,
    deep: bool = False,
    output_dir: Path | None = None,
) -> dict:
    out_dir = output_dir or Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)

    multi = len(urls) > 1
    if multi:
        plan = [normalize_url(u) for u in urls][:25]
        mode = "multi-list"
    else:
        plan = collect_urls(urls[0], None, expand_nav=True, max_extra=max_extra)
        mode = "single+nav"

    domain = domain_from_url(plan[0])
    primary = plan[0]

    md_path = out_dir / f"{domain}-design.md"
    json_path = out_dir / f"{domain}-tokens.json"
    css_path = out_dir / f"{domain}-tokens.css"

    if not force:
        existing = [p for p in (md_path, json_path, css_path) if p.exists()]
        if existing:
            names = ", ".join(p.name for p in existing)
            raise SystemExit(
                f"Refusing to overwrite existing files: {names}. "
                "Re-run with --force after confirmation, or remove them."
            )

    pages = [fetch_html(u) for u in plan]
    css_blocks = []
    for page in pages:
        if page.get("html") and not page.get("error"):
            css_blocks.append(collect_css_for_page(page))

    css_payload = {"domain": domain, "css": css_blocks}
    signals = extract_signals(css_payload)
    token_doc = build_token_doc(signals, primary, domain)

    evidence_mode = "deep" if deep else "static"
    if deep:
        # Placeholder: deep mode reserved; do not invent Playwright data here.
        token_doc.setdefault("meta", {})["deep_note"] = (
            "Deep mode requested but Playwright capture is optional and not "
            "executed in this orchestrator build; static evidence only."
        )

    md = render_design_md(
        domain=domain,
        primary_url=primary,
        pages=pages,
        mode=mode,
        evidence_mode=evidence_mode,
        signals=signals,
        token_doc=token_doc,
    )

    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(token_doc, indent=2) + "\n", encoding="utf-8")
    css_path.write_text(tokens_to_css(token_doc), encoding="utf-8")

    # Side evidence for agents
    evidence_path = out_dir / f"{domain}-designmd-evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "domain": domain,
                "primary_url": primary,
                "mode": mode,
                "evidence_mode": evidence_mode,
                "urls": plan,
                "pages": [
                    {
                        "url": p.get("url"),
                        "final_url": p.get("final_url"),
                        "status": p.get("status"),
                        "error": p.get("error"),
                        "html_bytes": len(p.get("html") or ""),
                    }
                    for p in pages
                ],
                "signals": signals,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "domain": domain,
        "design_md": str(md_path.resolve()),
        "tokens_json": str(json_path.resolve()),
        "tokens_css": str(css_path.resolve()),
        "evidence_json": str(evidence_path.resolve()),
        "pages_scanned": len(pages),
        "mode": mode,
    }


def main():
    parser = argparse.ArgumentParser(description="Extract semantic design system from URL(s)")
    parser.add_argument("urls", nargs="*", help="URL(s)")
    parser.add_argument("--urls-file", help="File with one URL per line")
    parser.add_argument("--max-extra", type=int, default=8, help="Nav expand cap for single URL")
    parser.add_argument("--force", action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--deep", action="store_true", help="Request deep evidence mode (Playwright optional)")
    parser.add_argument("--output-dir", default=".", help="Output directory (default CWD)")
    args = parser.parse_args()

    urls = list(args.urls or [])
    if args.urls_file:
        for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    if not urls:
        parser.error("Provide URL(s) or --urls-file")

    result = run(
        urls,
        force=args.force,
        max_extra=args.max_extra,
        deep=args.deep,
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
