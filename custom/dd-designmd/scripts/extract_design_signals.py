#!/usr/bin/env python3
"""Extract raw design signals (colors, type, layout, elevation, breakpoints) from CSS."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from typing import Iterable

HEX = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
RGB = re.compile(r"rgba?\(\s*[^)]+\)", re.I)
HSL = re.compile(r"hsla?\(\s*[^)]+\)", re.I)
FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;}{]+)", re.I)
FONT_SIZE = re.compile(r"font-size\s*:\s*([^;}{]+)", re.I)
FONT_WEIGHT = re.compile(r"font-weight\s*:\s*([^;}{]+)", re.I)
LINE_HEIGHT = re.compile(r"line-height\s*:\s*([^;}{]+)", re.I)
LETTER_SPACING = re.compile(r"letter-spacing\s*:\s*([^;}{]+)", re.I)
BORDER_RADIUS = re.compile(r"border-radius\s*:\s*([^;}{]+)", re.I)
BOX_SHADOW = re.compile(r"box-shadow\s*:\s*([^;}{]+)", re.I)
MEDIA = re.compile(r"@media[^{]+\{?", re.I)
MAX_WIDTH = re.compile(r"max-width\s*:\s*([^;}{]+)", re.I)
DISPLAY = re.compile(r"display\s*:\s*([^;}{]+)", re.I)
GRID_TEMPLATE = re.compile(r"grid-template-columns\s*:\s*([^;}{]+)", re.I)
Z_INDEX = re.compile(r"z-index\s*:\s*([^;}{]+)", re.I)
GRADIENT = re.compile(r"(?:repeating-)?(?:linear|radial|conic)-gradient\(", re.I)
PADDING_PROP = re.compile(
    r"padding(?:-(?:top|right|bottom|left))?\s*:\s*([^;}{]+)", re.I
)
GAP_PROP = re.compile(r"(?:row-|column-)?gap\s*:\s*([^;}{]+)", re.I)
FOCUS_BLOCK = re.compile(
    r"[^{}]*:focus(?:-visible|-within)?[^{]*\{([^}]*)\}",
    re.I,
)
OUTLINE_PROP = re.compile(
    r"outline(?:-color|-width|-offset|-style)?\s*:\s*([^;}{]+)",
    re.I,
)
INTERACTION_BLOCK = re.compile(
    r"([^{};\n]{0,120}:(?:hover|active|disabled|visited))\s*\{([^}]*)\}",
    re.I,
)
DISABLED_ATTR = re.compile(
    r"([^{};\n]{0,120}\[(?:aria-)?disabled[^\]]*\])\s*\{([^}]*)\}",
    re.I,
)
INTERACTION_STATES = ("hover", "active", "disabled", "visited")
# spacing-ish declarations
SPACE_PROPS = re.compile(
    r"(?:margin|padding|gap|row-gap|column-gap|top|right|bottom|left|"
    r"width|height|min-width|max-width|min-height|max-height)\s*:\s*([^;}{]+)",
    re.I,
)
LAYOUT_DISPLAYS = frozenset({"flex", "inline-flex", "grid", "inline-grid"})
LENGTH = re.compile(
    r"(-?\d+\.?\d*)(px|rem|em|%|vh|vw|ch)",
    re.I,
)
CSS_VAR = re.compile(r"--([a-zA-Z0-9_-]+)\s*:\s*([^;}{]+)")


def _iter_css_blobs(css_payload: dict) -> Iterable[tuple[str, str]]:
    for block in css_payload.get("css") or []:
        page = block.get("url") or ""
        for inline in block.get("inline") or []:
            yield page, inline
        for sheet in block.get("sheets") or []:
            src = sheet.get("href") or page
            if sheet.get("css"):
                yield src, sheet["css"]


def _norm_color(c: str) -> str:
    c = c.strip().lower()
    if c.startswith("#") and len(c) == 4:
        # #rgb -> #rrggbb
        c = "#" + "".join(ch * 2 for ch in c[1:])
    return c


def extract_signals(css_payload: dict, max_each: int = 40) -> dict:
    colors: Counter[str] = Counter()
    fonts: Counter[str] = Counter()
    font_sizes: Counter[str] = Counter()
    font_weights: Counter[str] = Counter()
    line_heights: Counter[str] = Counter()
    radii: Counter[str] = Counter()
    shadows: Counter[str] = Counter()
    spaces: Counter[str] = Counter()
    breakpoints: Counter[str] = Counter()
    max_widths: Counter[str] = Counter()
    displays: Counter[str] = Counter()
    grid_templates: Counter[str] = Counter()
    z_indexes: Counter[str] = Counter()
    gradients: Counter[str] = Counter()
    paddings: Counter[str] = Counter()
    gaps: Counter[str] = Counter()
    focus_rules: Counter[str] = Counter()
    outlines: Counter[str] = Counter()
    interactions: dict[str, Counter[str]] = {
        name: Counter() for name in INTERACTION_STATES
    }
    css_vars: dict[str, str] = {}
    evidence_samples: dict[str, list[str]] = {
        "color": [],
        "font": [],
        "space": [],
        "radius": [],
        "shadow": [],
        "breakpoint": [],
        "css_var": [],
        "layout": [],
        "elevation": [],
        "focus": [],
        "interaction": [],
    }

    def note(kind: str, sample: str, limit: int = 8):
        bucket = evidence_samples[kind]
        if len(bucket) < limit and sample not in bucket:
            bucket.append(sample[:200])

    for src, css in _iter_css_blobs(css_payload):
        for m in HEX.finditer(css):
            val = _norm_color(m.group(0))
            colors[val] += 1
            note("color", f"{val} @ {src}")
        for m in RGB.finditer(css):
            val = re.sub(r"\s+", "", m.group(0).lower())
            colors[val] += 1
            note("color", f"{val} @ {src}")
        for m in HSL.finditer(css):
            val = re.sub(r"\s+", " ", m.group(0).lower()).strip()
            colors[val] += 1
            note("color", f"{val} @ {src}")

        for m in FONT_FAMILY.finditer(css):
            fam = re.sub(r"\s+", " ", m.group(1)).strip().strip("\"'")
            fonts[fam] += 1
            note("font", f"font-family: {fam} @ {src}")
        for m in FONT_SIZE.finditer(css):
            val = m.group(1).strip()
            font_sizes[val] += 1
        for m in FONT_WEIGHT.finditer(css):
            font_weights[m.group(1).strip()] += 1
        for m in LINE_HEIGHT.finditer(css):
            line_heights[m.group(1).strip()] += 1

        for m in BORDER_RADIUS.finditer(css):
            val = m.group(1).strip()
            radii[val] += 1
            note("radius", f"border-radius: {val} @ {src}")
        for m in BOX_SHADOW.finditer(css):
            val = re.sub(r"\s+", " ", m.group(1)).strip()
            if val and val != "none":
                shadows[val] += 1
                note("shadow", f"box-shadow: {val[:80]} @ {src}")
                note("elevation", f"box-shadow: {val[:80]} @ {src}")

        for m in MAX_WIDTH.finditer(css):
            val = re.sub(r"\s+", " ", m.group(1)).strip()
            if val and val.lower() not in {"none", "auto", "100%", "0", "0px"}:
                max_widths[val] += 1
                note("layout", f"max-width: {val} @ {src}")

        for m in DISPLAY.finditer(css):
            val = m.group(1).strip().split()[0].lower() if m.group(1).strip() else ""
            if val in LAYOUT_DISPLAYS:
                displays[val] += 1
                note("layout", f"display: {val} @ {src}")

        for m in GRID_TEMPLATE.finditer(css):
            val = re.sub(r"\s+", " ", m.group(1)).strip()
            if val and val.lower() not in {"none", "auto"}:
                grid_templates[val] += 1
                note("layout", f"grid-template-columns: {val[:80]} @ {src}")

        for m in Z_INDEX.finditer(css):
            val = m.group(1).strip()
            if val and val.lower() not in {"auto"}:
                z_indexes[val] += 1
                note("elevation", f"z-index: {val} @ {src}")

        for m in GRADIENT.finditer(css):
            snippet = re.sub(r"\s+", " ", css[m.start() : m.start() + 96]).strip()
            gradients[snippet] += 1
            note("color", f"{snippet} @ {src}")

        for m in PADDING_PROP.finditer(css):
            for lm in LENGTH.finditer(m.group(1)):
                token = f"{lm.group(1)}{lm.group(2).lower()}"
                paddings[token] += 1

        for m in GAP_PROP.finditer(css):
            for lm in LENGTH.finditer(m.group(1)):
                token = f"{lm.group(1)}{lm.group(2).lower()}"
                gaps[token] += 1
                note("layout", f"gap: {token} @ {src}")

        for m in FOCUS_BLOCK.finditer(css):
            body = re.sub(r"\s+", " ", m.group(1)).strip()
            if body:
                focus_rules[body[:120]] += 1
                note("focus", f":focus {{ {body[:80]} }} @ {src}")

        for m in OUTLINE_PROP.finditer(css):
            val = re.sub(r"\s+", " ", m.group(1)).strip()
            if val and val.lower() not in {"none", "0", "0px"}:
                outlines[val] += 1
                note("focus", f"outline: {val} @ {src}")

        for m in INTERACTION_BLOCK.finditer(css):
            selector = re.sub(r"\s+", " ", m.group(1)).strip()
            body = re.sub(r"\s+", " ", m.group(2)).strip()
            state = ""
            low = selector.lower()
            for name in INTERACTION_STATES:
                if f":{name}" in low:
                    state = name
                    break
            if state and body:
                sample = f"{selector[:60]} {{ {body[:80]} }}"
                interactions[state][sample] += 1
                note("interaction", f"{sample} @ {src}")

        for m in DISABLED_ATTR.finditer(css):
            selector = re.sub(r"\s+", " ", m.group(1)).strip()
            body = re.sub(r"\s+", " ", m.group(2)).strip()
            if body:
                sample = f"{selector[:60]} {{ {body[:80]} }}"
                interactions["disabled"][sample] += 1
                note("interaction", f"{sample} @ {src}")

        for m in SPACE_PROPS.finditer(css):
            for lm in LENGTH.finditer(m.group(1)):
                token = f"{lm.group(1)}{lm.group(2).lower()}"
                spaces[token] += 1
                note("space", f"{token} @ {src}")

        for m in MEDIA.finditer(css):
            query = re.sub(r"\s+", " ", m.group(0)).strip().rstrip("{").strip()
            breakpoints[query] += 1
            note("breakpoint", f"{query} @ {src}")

        for m in CSS_VAR.finditer(css):
            name, val = m.group(1), m.group(2).strip()
            if name not in css_vars:
                css_vars[name] = val
                note("css_var", f"--{name}: {val} @ {src}")

    def top(counter: Counter, n: int = max_each):
        return [{"value": k, "count": v} for k, v in counter.most_common(n)]

    return {
        "domain": css_payload.get("domain"),
        "colors": top(colors),
        "font_families": top(fonts, 15),
        "font_sizes": top(font_sizes, 25),
        "font_weights": top(font_weights, 12),
        "line_heights": top(line_heights, 12),
        "radii": top(radii, 15),
        "shadows": top(shadows, 12),
        "spacing_values": top(spaces, 30),
        "max_widths": top(max_widths, 12),
        "displays": top(displays, 8),
        "grid_templates": top(grid_templates, 10),
        "z_indexes": top(z_indexes, 10),
        "gradients": top(gradients, 8),
        "paddings": top(paddings, 16),
        "gaps": top(gaps, 12),
        "focus_rules": top(focus_rules, 10),
        "outlines": top(outlines, 8),
        "interactions": {
            name: top(interactions[name], 8) for name in INTERACTION_STATES
        },
        "breakpoints": top(breakpoints, 20),
        "css_variables": [
            {"name": f"--{k}", "value": v} for k, v in list(css_vars.items())[:80]
        ],
        "evidence_samples": evidence_samples,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON from extract_css path or combined")
    args = parser.parse_args()
    payload = json.loads(open(args.input, encoding="utf-8").read())
    # Accept either {css: [...]} or full extract_css output
    if "css" not in payload and "pages" in payload:
        raise SystemExit("Pass CSS collection JSON (run extract_css first)")
    print(json.dumps(extract_signals(payload), indent=2))


if __name__ == "__main__":
    main()
