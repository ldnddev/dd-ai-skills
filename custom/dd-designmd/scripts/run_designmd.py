#!/usr/bin/env python3
"""
Orchestrate semantic design-system extraction for dd-designmd.

Usage:
  python3 run_designmd.py https://www.ldnddev.com
  python3 run_designmd.py https://a.com https://a.com/about --force
  python3 run_designmd.py --urls-file urls.txt --web
  python3 run_designmd.py --urls-file urls.txt --deep   # deep reserved

Writes to CWD (default), or web/<domain>-designmd-YYYY-MM-DD/ with --web:
  index.html               (Framework dashboard; always with --web, optional with --dashboard)
  {domain}-design.md
  {domain}-tokens.json
  {domain}-tokens.css
"""

from __future__ import annotations

import argparse
import json
import re
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
from generate_dashboard import build_dashboard, default_web_dir  # noqa: E402

# Required `{domain}-design.md` headings. Must match
# skills/dd-designmd/references/design-doc-template.md.
REQUIRED_MD_HEADINGS = [
    "## Meta",
    "## Overview",
    "## Logo & brand mark",
    "## Foundations",
    "## Layout & Spacing",
    "## Elevation & Shapes",
    "## Semantic tokens",
    "## Color usage rules",
    "## Components",
    "## Interactive states",
    "## Patterns / page templates",
    "## Iconography & media",
    "## Content & copy patterns",
    "## Focus & keyboard",
    "## Do / Don’t",
    "## Implementation notes",
    "## ldnddev Framework mapping",
    "## Agent instructions",
    "## Open questions & missing evidence",
    "## Appendix — evidence samples",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def missing_required_headings(md: str) -> list[str]:
    return [h for h in REQUIRED_MD_HEADINGS if h not in md]


def _strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _html_surface(html: str) -> dict[str, str]:
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.I | re.S)
    h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", html or "", re.I | re.S)
    meta_m = re.search(
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']+)["\']',
        html or "",
        re.I,
    )
    if not meta_m:
        meta_m = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:description|og:description)["\']',
            html or "",
            re.I,
        )
    return {
        "title": _strip_tags(title_m.group(1)) if title_m else "",
        "h1": _strip_tags(h1_m.group(1)) if h1_m else "",
        "meta_description": _strip_tags(meta_m.group(1)) if meta_m else "",
    }


def _attr(tag: str, name: str) -> str:
    m = re.search(rf"""{name}\s*=\s*["']([^"']+)["']""", tag, re.I)
    return m.group(1) if m else ""


def _extract_logos(html: str) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for tag in re.findall(r"<img\b[^>]*>", html or "", re.I):
        blob = " ".join(
            [_attr(tag, "src"), _attr(tag, "class"), _attr(tag, "alt"), _attr(tag, "id")]
        )
        if re.search(r"logo|brand|wordmark", blob, re.I):
            src = _attr(tag, "src") or blob[:80]
            if src not in seen:
                seen.add(src)
                alt = _attr(tag, "alt")
                hits.append(f"img `{src}`" + (f' alt="{alt}"' if alt else ""))
    for tag in re.findall(r"<link\b[^>]*>", html or "", re.I):
        rel = _attr(tag, "rel").lower()
        if "icon" in rel:
            href = _attr(tag, "href")
            if href and href not in seen:
                seen.add(href)
                hits.append(f"icon `{href}` ({rel})")
    return hits[:8]


def _extract_copy_samples(html: str) -> dict[str, list[str]]:
    headings: list[str] = []
    for m in re.finditer(r"<h([1-3])\b[^>]*>(.*?)</h\1>", html or "", re.I | re.S):
        text = _strip_tags(m.group(2))
        if text and text not in headings:
            headings.append(f"H{m.group(1)}: {text}")
        if len(headings) >= 8:
            break
    ctas: list[str] = []
    for m in re.finditer(r"<button\b[^>]*>(.*?)</button>", html or "", re.I | re.S):
        text = _strip_tags(m.group(1))
        if text and text not in ctas:
            ctas.append(text)
        if len(ctas) >= 8:
            break
    if len(ctas) < 8:
        for m in re.finditer(
            r"<a\b[^>]*class=['\"][^'\"]*\b(?:btn|button|cta)[^'\"]*['\"][^>]*>(.*?)</a>",
            html or "",
            re.I | re.S,
        ):
            text = _strip_tags(m.group(1))
            if text and text not in ctas:
                ctas.append(text)
            if len(ctas) >= 8:
                break
    return {"headings": headings, "ctas": ctas}


def _generation_constraint_rows(signals: dict) -> list[tuple[str, str, str]]:
    """Provisional Do/Don't seeds from measured presence/absence."""
    rows: list[tuple[str, str, str]] = []
    gradients = signals.get("gradients") or []
    shadows = signals.get("shadows") or []
    radii = signals.get("radii") or []

    if not gradients:
        rows.append(
            (
                "Gradients",
                "Do not introduce gradients unless Open questions override this — none extracted from static CSS",
                "no linear/radial/conic-gradient hits",
            )
        )
    else:
        rows.append(
            (
                "Gradients",
                "Reuse only documented gradient recipes; do not invent new ones",
                f"{len(gradients)} gradient sample(s) extracted",
            )
        )

    if not shadows:
        rows.append(
            (
                "Shadows / elevation",
                "Keep surfaces flat; do not add drop shadows",
                "no box-shadow rules extracted",
            )
        )
    else:
        rows.append(
            (
                "Shadows / elevation",
                "Use only documented shadow tokens; do not stack extra elevation",
                f"{len(shadows)} box-shadow value(s)",
            )
        )

    if radii and all(
        str(r.get("value") or "").strip() in {"0", "0px", "none"} for r in radii
    ):
        rows.append(
            (
                "Radius",
                "Keep corners square (0 radius)",
                "all extracted border-radius values are 0",
            )
        )
    elif radii:
        rows.append(
            (
                "Radius",
                "Use only documented radius tokens; do not mix a new rounding language",
                f"{len(radii)} border-radius value(s)",
            )
        )

    rows.append(
        (
            "Status / error",
            "Never rely on color alone for errors or success. Pair status text with the documented non-color indicator (icon, prefix, or border) if one is observed; if none is observed, still include text plus a color token — never color-only.",
            "agent must confirm from HTML; default is text + color",
        )
    )
    rows.append(
        (
            "New visual effects",
            "Do not add glassmorphism, mesh backgrounds, glow, or decorative blur unless evidenced above",
            "common AI generation mistake",
        )
    )

    focus_rules = signals.get("focus_rules") or []
    outlines = signals.get("outlines") or []
    if not focus_rules and not outlines:
        rows.append(
            (
                "Focus ring",
                "Do not invent a decorative focus glow. Record the observed outline; if none extracted, keep a visible default outline and mark as Open question — never `outline: none` without a replacement.",
                "no :focus / outline rules extracted",
            )
        )
    else:
        rows.append(
            (
                "Focus ring",
                "Reuse only the documented focus treatment (token + offset). Do not restyle :focus as a marketing flourish.",
                f"{len(focus_rules)} :focus block(s), {len(outlines)} outline value(s)",
            )
        )

    hovers = (signals.get("interactions") or {}).get("hover") or []
    if not hovers:
        rows.append(
            (
                "Hover",
                "Do not invent hover scale, glow, or underline. If no :hover rules extracted, keep the resting state.",
                "no :hover rules extracted",
            )
        )
    else:
        rows.append(
            (
                "Hover",
                "Reuse only documented hover treatments from Interactive states — no extra translate/scale/shadow.",
                f"{len(hovers)} :hover sample(s)",
            )
        )
    rows.append(
        (
            "Color roles",
            "Use each color token only for the role in Color usage rules. Do not use brand fill as body text or canvas as a heading color.",
            "see Color usage rules",
        )
    )
    return rows


def _color_usage_hint(key: str) -> tuple[str, str]:
    """Provisional use / do-not-use from the token name. Agent must confirm."""
    known = {
        "color.bg.canvas": (
            "Page / canvas background",
            "Body text or icons",
        ),
        "color.text.primary": (
            "Body and heading text on canvas",
            "Large filled backgrounds",
        ),
        "color.text.muted": (
            "Helper, caption, or de-emphasized text",
            "Primary headings or primary CTAs",
        ),
        "color.brand.primary": (
            "Primary actions, links, or accents",
            "Body copy or full-page fills unless observed",
        ),
        "color.brand.secondary": (
            "Secondary accent",
            "Default body text",
        ),
        "color.border.subtle": (
            "Borders and dividers",
            "Text",
        ),
        "color.bg.surface": (
            "Raised or nested surface",
            "Primary body text",
        ),
    }
    if key in known:
        return known[key]
    if key.startswith("color.bg."):
        return ("Background / surface", "Small text unless contrast is evidenced")
    if key.startswith("color.text."):
        return ("Text on canvas/surface", "Large fills")
    if key.startswith("color.brand."):
        return (
            "Accent / action",
            "Body copy or full-page fills unless observed",
        )
    if key.startswith("color.border."):
        return ("Borders / dividers", "Text")
    return (
        "*agent: assign from evidence*",
        "*agent: assign from evidence*",
    )


def _color_usage_table(token_doc: dict) -> str:
    rows: list[tuple[str, ...]] = []
    for key, body in (token_doc.get("tokens") or {}).items():
        if not key.startswith("color.") or key.startswith("color.palette."):
            continue
        use, forbid = _color_usage_hint(key)
        rows.append(
            (
                f"`{key}`",
                str(body.get("value") or ""),
                use,
                forbid,
                str(body.get("evidence") or ""),
            )
        )
    if not rows:
        return "_No semantic color tokens yet. Agent: fill from measured palette only — do not invent roles._"
    return _plain_table(
        ["Token", "Value", "Use for", "Do not use for", "Evidence"],
        rows,
    )


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


def _plain_table(headers: list[str], rows: list[tuple[str, ...]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["------"] * len(headers)) + "|",
    ]
    for row in rows:
        cells = [str(c).replace("|", "\\|").replace("\n", " ") for c in row]
        lines.append("| " + " | ".join(cells) + " |")
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
    max_widths = signals.get("max_widths") or []
    displays = signals.get("displays") or []
    grid_templates = signals.get("grid_templates") or []
    paddings = signals.get("paddings") or []
    gaps = signals.get("gaps") or []
    z_indexes = signals.get("z_indexes") or []
    focus_rules = signals.get("focus_rules") or []
    outlines = signals.get("outlines") or []
    interactions = signals.get("interactions") or {}

    primary_surface = None
    surface_lines = []
    for p in pages:
        html = p.get("html") or ""
        if not html:
            continue
        surface = _html_surface(html)
        if primary_surface is None:
            primary_surface = surface
        url = p.get("final_url") or p.get("url")
        bits = []
        if surface["title"]:
            bits.append(f"title: {surface['title']}")
        if surface["h1"]:
            bits.append(f"H1: {surface['h1']}")
        if surface["meta_description"] and primary_surface is surface:
            bits.append(f"meta: {surface['meta_description']}")
        if bits:
            surface_lines.append(f"- `{url}` — {'; '.join(bits)}")
    if primary_surface is None:
        primary_surface = {"title": "", "h1": "", "meta_description": ""}

    product_seed = (
        primary_surface.get("meta_description")
        or primary_surface.get("h1")
        or primary_surface.get("title")
        or "*not stated on scanned pages — fill only from on-page copy.*"
    )
    constraint_md = _plain_table(
        ["Constraint", "Rule", "Evidence"],
        _generation_constraint_rows(signals),
    )
    pattern_md = _plain_table(
        ["Page", "Pattern notes"],
        [
            (
                p.get("final_url") or p.get("url") or "",
                "Header / main / footer composition — agent to complete",
            )
            for p in pages
        ],
    ) if pages else "_No pages scanned._"

    logo_hits: list[str] = []
    heading_samples: list[str] = []
    cta_samples: list[str] = []
    for p in pages:
        html = p.get("html") or ""
        if not html:
            continue
        for hit in _extract_logos(html):
            if hit not in logo_hits:
                logo_hits.append(hit)
        copy = _extract_copy_samples(html)
        for h in copy["headings"]:
            if h not in heading_samples:
                heading_samples.append(h)
        for c in copy["ctas"]:
            if c not in cta_samples:
                cta_samples.append(c)
    logo_md = "\n".join(f"- {h}" for h in logo_hits[:10]) or (
        "- *No logo/icon assets detected in img alt/class/src or link rel=icon.*"
    )
    heading_md = "\n".join(f"- {h}" for h in heading_samples[:8]) or (
        "- *No H1–H3 copy extracted.*"
    )
    cta_md = "\n".join(f"- {c}" for c in cta_samples[:8]) or (
        "- *No button / CTA label copy extracted.*"
    )
    color_usage_md = _color_usage_table(token_doc)

    def _state_table(state: str) -> str:
        samples = interactions.get(state) or []
        if not samples:
            return f"_No `:{state}` rules extracted._"
        return _table(
            [
                (f"raw.{state}.{i:02d}", s["value"][:80], f"count={s['count']}")
                for i, s in enumerate(samples[:8], 1)
            ]
        )

    inter_summary_rows: list[tuple[str, ...]] = []
    for state in ("hover", "focus", "active", "disabled", "loading", "visited"):
        if state == "focus":
            inter_summary_rows.append(
                (
                    "focus",
                    "See **Focus & keyboard** — do not invent a second ring here",
                    f"{len(focus_rules)} :focus block(s)",
                )
            )
        elif state == "loading":
            inter_summary_rows.append(
                (
                    "loading",
                    "*not extracted from CSS — agent: spinners / `aria-busy` / skeleton from HTML only*",
                    "HTML only",
                )
            )
        else:
            samples = interactions.get(state) or []
            if samples:
                inter_summary_rows.append(
                    (
                        state,
                        f"{len(samples)} rule sample(s) below — reuse, do not embellish",
                        f"top count={samples[0].get('count', '')}",
                    )
                )
            else:
                inter_summary_rows.append(
                    (
                        state,
                        f"*none extracted — do not invent a `:{state}` effect*",
                        "no matching selectors",
                    )
                )
    inter_summary_md = _plain_table(
        ["State", "Observed treatment", "Evidence"],
        inter_summary_rows,
    )

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

## Overview

Evidence-only. If a field is not on the scanned pages, write *not stated on scanned pages* — do **not** invent mission, personality, or a voice framework.

### Product summary

{product_seed}

**On-page surface**

{chr(10).join(surface_lines) if surface_lines else "- *No title/H1 extracted from scanned HTML.*"}

### Brand style

_Agent: describe the **visual** register from measured CSS/HTML only (density, contrast, geometry, chrome). Example shape: “high-contrast navy/white, sharp radii, dense sans body.” No personality fiction._

### Brand tone

_Agent: describe **observed copy register** only (headline case, CTA verbs, sentence formality) or quote on-site voice guidelines. If neither exists: *not stated on scanned pages*._

### Core visual principles

_Agent: 3–5 bullets derived from Layout, Elevation, Color, and Type. Each bullet must be supportable from measured evidence (e.g. “hairline borders over drop shadows”)._

## Logo & brand mark

Evidence-only. Document clear space, on-light / on-dark versions, and minimum size **only** if those rules or variants appear on-site. Do not invent a logo lockup.

**Detected assets**

{logo_md}

_Agent: note which file is the primary wordmark vs icon-only, background it sits on, and any observed inversion. If a usage rule is not on-site: *not stated*._

## Foundations

Layout, spacing, radius, and elevation live in their own sections below — do not duplicate those tables here.

### Color (raw, measured)

Top colors by CSS occurrence (not a brand book):

{_table([(f"raw.color.{i:02d}", c['value'], f"count={c['count']}") for i, c in enumerate(colors_raw[:16], 1)]) if colors_raw else "_No colors extracted._"}

### Typography (raw, measured)

**Families**

{_table([(f"raw.font.family.{i:02d}", f['value'], f"count={f['count']}") for i, f in enumerate(fonts[:8], 1)]) if fonts else "_No font-family rules extracted._"}

**Sizes**

{_table([(f"raw.font.size.{i:02d}", f['value'], f"count={f['count']}") for i, f in enumerate(sizes[:12], 1)]) if sizes else "_No font-size rules extracted._"}

### Motion

_Not extracted in static mode unless present as CSS transitions/animations in a future pass. Mark as missing if not listed in appendix evidence samples._

### Breakpoints

{_table([(f"raw.breakpoint.{i:02d}", b['value'], f"count={b['count']}") for i, b in enumerate(bps[:12], 1)]) if bps else "_No @media queries extracted._"}

## Layout & Spacing

Measured layout signals. Agent must describe the **system** (grid, padding scale, containers) — not dump every length.

### Grid

{_table([(f"raw.display.{i:02d}", d['value'], f"count={d['count']}") for i, d in enumerate(displays[:8], 1)]) if displays else "_No flex/grid `display` rules extracted._"}

**`grid-template-columns` samples**

{_table([(f"raw.grid.{i:02d}", g['value'][:80], f"count={g['count']}") for i, g in enumerate(grid_templates[:8], 1)]) if grid_templates else "_No grid-template-columns rules extracted._"}

**Gap**

{_table([(f"raw.gap.{i:02d}", g['value'], f"count={g['count']}") for i, g in enumerate(gaps[:12], 1)]) if gaps else "_No gap lengths extracted._"}

### Padding

{_table([(f"raw.padding.{i:02d}", p['value'], f"count={p['count']}") for i, p in enumerate(paddings[:16], 1)]) if paddings else "_No padding lengths extracted._"}

### Containers

{_table([(f"raw.max-width.{i:02d}", w['value'], f"count={w['count']}") for i, w in enumerate(max_widths[:12], 1)]) if max_widths else "_No max-width constraints extracted._"}

### Spacing scale (raw lengths)

{_table([(f"raw.space.{i:02d}", s['value'], f"count={s['count']}") for i, s in enumerate(spaces[:16], 1)]) if spaces else "_No spacing lengths extracted._"}

## Elevation & Shapes

### Surfaces

_Agent: describe layering (canvas, raised cards, sticky chrome, overlays) from background + shadow + radius + z-index. If no layering evidence: *flat / single surface — not stated otherwise*._

### Shadows

{_table([(f"raw.shadow.{i:02d}", s['value'][:80], f"count={s['count']}") for i, s in enumerate(shadows[:8], 1)]) if shadows else "_No box-shadow rules extracted._"}

### Radius

{_table([(f"raw.radius.{i:02d}", r['value'], f"count={r['count']}") for i, r in enumerate(radii[:10], 1)]) if radii else "_No border-radius rules extracted._"}

### Z-index

{_table([(f"raw.z.{i:02d}", z['value'], f"count={z['count']}") for i, z in enumerate(z_indexes[:10], 1)]) if z_indexes else "_No z-index rules extracted._"}

## Semantic tokens

Provisional semantic names mapped from **measured** CSS. Rank/order is frequency-based, **not** an official brand scale.

### Core semantic candidates

{_table(semantic[:40]) if semantic else "_No tokens emitted._"}

### Palette ranks (frequency)

{_table(palette) if palette else "_No palette ranks._"}

Machine-readable dump: `{domain}-tokens.json` and `{domain}-tokens.css`.

## Color usage rules

When to use each **semantic** color token. Palette ranks are not roles. Use-for / do-not-use rows below are **provisional from the token name** — agent must rewrite from HTML/CSS evidence and add forbidden pairs.

{color_usage_md}

### Forbidden combinations

| Pair | Why | Evidence |
|------|-----|----------|
| *(agent)* | e.g. brand fill + brand text, canvas-on-canvas, muted text on muted surface | Cite CSS/HTML or *not stated* |

_Agent: every generated UI color must map to a token in this table. Do not introduce a new hex even if it “looks close.”_

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

## Interactive states

Cross-component. The Components table may point here; **do not invent states that are empty below.** Focus ring details live in **Focus & keyboard** — do not duplicate a second ring spec.

{inter_summary_md}

### Hover

{_state_table("hover")}

### Active

{_state_table("active")}

### Disabled

{_state_table("disabled")}

### Visited

{_state_table("visited")}

_Agent: describe the shared hover/active/disabled language (opacity, underline, color shift, pointer). Loading/skeleton only if HTML evidence exists. Do not add scale, glow, or lift unless sampled above._

## Patterns / page templates

Describe only templates actually scanned (home, pricing, etc.). For each page URL, note primary layout regions observed (header, hero, main, footer).

{pattern_md}

## Iconography & media

- Report icon fonts or SVG systems only if CSS/HTML references them (e.g. Font Awesome content codes, `<svg>` usage).
- Do not invent an icon library.

## Content & copy patterns

Distinct from Overview brand tone. Record **how UI copy is written**, not a personality manifesto.

**Headings sampled**

{heading_md}

**CTA / button labels sampled**

{cta_md}

_Agent: complete heading case (sentence vs title), CTA verb style, and microcopy patterns from the samples. If a pattern is not evidenced: *not stated*._

## Focus & keyboard

Facts only — do not score accessibility here (`dd-a11y` owns audits).

**`:focus` / `:focus-visible` rule bodies**

{_table([(f"raw.focus.{i:02d}", f['value'][:80], f"count={f['count']}") for i, f in enumerate(focus_rules[:8], 1)]) if focus_rules else "_No :focus rule bodies extracted._"}

**Outline values**

{_table([(f"raw.outline.{i:02d}", o['value'], f"count={o['count']}") for i, o in enumerate(outlines[:8], 1)]) if outlines else "_No non-zero outline values extracted._"}

_Agent: describe the observed focus ring (color, width, offset, `:focus-visible` vs `:focus`). Never recommend `outline: none` without a visible replacement that is already on-site._

## Do / Don’t

Process rules (always apply):

| Do | Don’t |
|----|-------|
| Reuse measured tokens from `{domain}-tokens.css` as a starting point | Treat frequency rank as official brand hierarchy without validation |
| Cite CSS/HTML evidence when adding tokens | Invent brand mission, personality, or palette not on-site |
| Map components honestly to Framework gaps | Propose a full rebrand |
| Keep a11y/SEO work in their own skills | Score a11y or SEO inside this document |

### Generation constraints (site-specific)

Explicit enough to stop common AI UI mistakes. Provisional rows are seeded from static extraction — **agent must confirm, rewrite as hard Do/Don’t, and add any observed rules** (e.g. “always pair error text with a color indicator **and** an icon”).

{constraint_md}

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

## Agent instructions

Use this file as the **visual source of truth** when generating or editing UI for `{domain}`. Tokens, components, and Framework mapping override vague impressions from Overview.

### How to read this file

1. **Overview** sets product context and visual principles. Do not expand it into a new brand.
2. **Logo & brand mark** is the only legal mark treatment. Do not redraw, recolor, or drop a substitute logo.
3. **Tokens** are the only legal color, type, space, radius, and shadow values unless a component documents an exception.
4. **Color usage rules** say which token is for what. Do not use a token outside its Use for column.
5. **Layout & Spacing** and **Elevation & Shapes** constrain structure. Do not invent a new grid, container width, or shadow stack.
6. **Interactive states** are the only legal hover/active/disabled/loading treatments. Empty state = do not invent it.
7. **Content & copy patterns** constrain UI writing (heading case, CTA verbs). Do not invent a voice chart.
8. **Focus & keyboard** documents the observed focus treatment. Do not remove outlines or invent a glow.
9. **Do / Don’t** (including generation constraints) are hard rules. A prettier alternative that violates them is wrong.
10. **Components** and **Patterns** are the allowed building blocks. Prefer composing documented components over new ones.
11. **Framework mapping** applies when emitting ldnddev Framework HTML (`dd-*`). If the map says gap, do not force-fit.
12. **Open questions** are unknowns. Do not fill them with guesses in code.

### When writing UI

- Prefer `{domain}-tokens.css` variable names over raw hex/px.
- Apply **Color usage rules** (token role + forbidden pairs); never a close-enough hex.
- Match hover/active/disabled to **Interactive states** only — no extra scale, glow, or lift.
- Match observed density, radius, and elevation — do not “modernize” (no extra gradients, glass, or drop shadows unless documented).
- Use only documented logo assets; do not regenerate or recolor the mark.
- Match heading case and CTA verbs from **Content & copy patterns**.
- Keep the documented focus ring; never `outline: none` without the replacement already in this file.
- Pair status and error messaging with the documented indicators (color plus icon/text if that is the rule).
- If a needed token or component is missing, stop and ask, or reuse the nearest documented pattern. Never invent a palette value.
- Keep a11y/SEO scoring out of this workflow (`dd-a11y` / `dd-seo`).

### Out of scope for generated UI

- Rebrand, new visual direction, or decorative effects not evidenced above
- Unmapped third-party UI kits that conflict with these tokens

_Agent: add any site-specific interpretation notes here (e.g. “primary CTA is always the filled brand button; never outline at hero”)._

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
    web: bool = False,
    dashboard: bool = False,
    project_root: Path | None = None,
) -> dict:
    multi = len(urls) > 1
    if multi:
        plan = [normalize_url(u) for u in urls][:25]
        mode = "multi-list"
    else:
        plan = collect_urls(urls[0], None, expand_nav=True, max_extra=max_extra)
        mode = "single+nav"

    domain = domain_from_url(plan[0])
    primary = plan[0]

    if web:
        out_dir = default_web_dir(domain, project_root or Path.cwd())
        build_dash = True
    else:
        out_dir = output_dir or Path.cwd()
        build_dash = dashboard

    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / f"{domain}-design.md"
    json_path = out_dir / f"{domain}-tokens.json"
    css_path = out_dir / f"{domain}-tokens.css"
    evidence_path = out_dir / f"{domain}-designmd-evidence.json"
    index_path = out_dir / "index.html"

    if not force:
        existing = [p for p in (md_path, json_path, css_path, evidence_path) if p.exists()]
        if build_dash and index_path.exists():
            existing.append(index_path)
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

    result = {
        "domain": domain,
        "output_dir": str(out_dir.resolve()),
        "design_md": str(md_path.resolve()),
        "tokens_json": str(json_path.resolve()),
        "tokens_css": str(css_path.resolve()),
        "evidence_json": str(evidence_path.resolve()),
        "pages_scanned": len(pages),
        "mode": mode,
        "evidence_mode": evidence_mode,
        "dashboard_html": None,
    }

    if build_dash:
        dash = build_dashboard(
            out_dir,
            domain=domain,
            primary_url=primary,
            mode=mode,
            evidence_mode=evidence_mode,
            pages_scanned=len(pages),
            token_doc=token_doc,
            signals=signals,
            file_basenames={
                "design_md": md_path.name,
                "tokens_json": json_path.name,
                "tokens_css": css_path.name,
                "evidence_json": evidence_path.name,
            },
        )
        result["dashboard_html"] = str(dash.resolve())

    return result


def main():
    parser = argparse.ArgumentParser(description="Extract semantic design system from URL(s)")
    parser.add_argument("urls", nargs="*", help="URL(s)")
    parser.add_argument("--urls-file", help="File with one URL per line")
    parser.add_argument("--max-extra", type=int, default=8, help="Nav expand cap for single URL")
    parser.add_argument("--force", action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--deep", action="store_true", help="Request deep evidence mode (Playwright optional)")
    parser.add_argument("--output-dir", default=None, help="Output directory (default CWD; ignored with --web)")
    parser.add_argument(
        "--web",
        action="store_true",
        help="Write bundle to web/<domain>-designmd-YYYY-MM-DD/ with Framework dashboard",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Also write index.html dashboard into --output-dir (implied by --web)",
    )
    args = parser.parse_args()

    urls = list(args.urls or [])
    if args.urls_file:
        for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    if not urls:
        parser.error("Provide URL(s) or --urls-file")

    out = Path(args.output_dir) if args.output_dir else None
    result = run(
        urls,
        force=args.force,
        max_extra=args.max_extra,
        deep=args.deep,
        output_dir=out,
        web=args.web,
        dashboard=args.dashboard or args.web,
        project_root=Path.cwd(),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
