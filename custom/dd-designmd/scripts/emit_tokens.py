#!/usr/bin/env python3
"""Promote raw signals to a provisional semantic token map (evidence-bound)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone


def _pick_colors(colors: list[dict]) -> dict:
    """Heuristic semantic assignment from frequency — values still measured."""
    # Prefer hex; skip pure black/white early for "brand" slots if others exist
    hexes = [c for c in colors if str(c["value"]).startswith("#")]
    if not hexes:
        hexes = colors[:12]

    def is_near_white(h: str) -> bool:
        if not h.startswith("#") or len(h) < 7:
            return False
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        return (r + g + b) / 3 > 245

    def is_near_black(h: str) -> bool:
        if not h.startswith("#") or len(h) < 7:
            return False
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        return (r + g + b) / 3 < 25

    ordered = [c["value"] for c in hexes]
    whites = [c for c in ordered if is_near_white(c)]
    blacks = [c for c in ordered if is_near_black(c)]
    chromatics = [c for c in ordered if c not in whites and c not in blacks]

    tokens = {}
    if whites:
        tokens["color.bg.canvas"] = {
            "value": whites[0],
            "evidence": "frequent light color in CSS",
        }
    if blacks:
        tokens["color.text.primary"] = {
            "value": blacks[0],
            "evidence": "frequent dark color in CSS",
        }
    if chromatics:
        tokens["color.brand.primary"] = {
            "value": chromatics[0],
            "evidence": "most frequent non-neutral color in CSS",
        }
    if len(chromatics) > 1:
        tokens["color.brand.secondary"] = {
            "value": chromatics[1],
            "evidence": "second non-neutral color by frequency",
        }
    # Keep raw top-N as palette.* without over-claiming semantics
    for i, c in enumerate(ordered[:12], start=1):
        tokens[f"color.palette.{i:02d}"] = {
            "value": c,
            "evidence": "top color by CSS occurrence",
        }
    return tokens


def _pick_fonts(families: list[dict], sizes: list[dict], weights: list[dict]) -> dict:
    tokens = {}
    if families:
        tokens["font.family.base"] = {
            "value": families[0]["value"],
            "evidence": "most common font-family declaration",
        }
    if len(families) > 1:
        tokens["font.family.secondary"] = {
            "value": families[1]["value"],
            "evidence": "second font-family by frequency",
        }
    for i, s in enumerate(sizes[:8], start=1):
        tokens[f"font.size.{i:02d}"] = {
            "value": s["value"],
            "evidence": "font-size declaration frequency",
        }
    for i, w in enumerate(weights[:6], start=1):
        tokens[f"font.weight.{i:02d}"] = {
            "value": w["value"],
            "evidence": "font-weight declaration frequency",
        }
    return tokens


def _pick_space(spaces: list[dict]) -> dict:
    tokens = {}
    # Prefer rem/px scales
    ranked = sorted(
        spaces,
        key=lambda x: (-x["count"], x["value"]),
    )
    for i, s in enumerate(ranked[:16], start=1):
        tokens[f"space.{i:02d}"] = {
            "value": s["value"],
            "evidence": "length used in margin/padding/gap/size props",
        }
    return tokens


def _pick_radii(radii: list[dict]) -> dict:
    tokens = {}
    for i, r in enumerate(radii[:8], start=1):
        tokens[f"radius.{i:02d}"] = {
            "value": r["value"],
            "evidence": "border-radius declaration frequency",
        }
    return tokens


def _pick_shadows(shadows: list[dict]) -> dict:
    tokens = {}
    for i, s in enumerate(shadows[:6], start=1):
        tokens[f"shadow.{i:02d}"] = {
            "value": s["value"],
            "evidence": "box-shadow declaration frequency",
        }
    return tokens


def _pick_breakpoints(bps: list[dict]) -> dict:
    tokens = {}
    for i, b in enumerate(bps[:10], start=1):
        tokens[f"breakpoint.{i:02d}"] = {
            "value": b["value"],
            "evidence": "@media query occurrence",
        }
    return tokens


def _pick_containers(max_widths: list[dict]) -> dict:
    tokens = {}
    for i, item in enumerate(max_widths[:6], start=1):
        key = "space.container" if i == 1 else f"space.container.{i:02d}"
        tokens[key] = {
            "value": item["value"],
            "evidence": "max-width declaration frequency",
        }
    return tokens


def build_token_doc(signals: dict, source_url: str, domain: str) -> dict:
    tokens: dict = {}
    tokens.update(_pick_colors(signals.get("colors") or []))
    tokens.update(_pick_fonts(
        signals.get("font_families") or [],
        signals.get("font_sizes") or [],
        signals.get("font_weights") or [],
    ))
    tokens.update(_pick_space(signals.get("spacing_values") or []))
    tokens.update(_pick_radii(signals.get("radii") or []))
    tokens.update(_pick_shadows(signals.get("shadows") or []))
    tokens.update(_pick_breakpoints(signals.get("breakpoints") or []))
    tokens.update(_pick_containers(signals.get("max_widths") or []))

    # Surface existing CSS variables as-is (strong evidence)
    for var in signals.get("css_variables") or []:
        name = var["name"].lstrip("-")
        key = f"cssvar.{name}"
        tokens[key] = {
            "value": var["value"],
            "evidence": f"declared CSS custom property {var['name']}",
        }

    return {
        "meta": {
            "domain": domain,
            "source_url": source_url,
            "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "note": (
                "Semantic names are provisional promotions of measured CSS values. "
                "Do not treat palette ranks as official brand guidelines."
            ),
        },
        "tokens": tokens,
    }


def tokens_to_css(token_doc: dict) -> str:
    lines = [":root {"]
    for key, body in (token_doc.get("tokens") or {}).items():
        css_name = "--" + key.replace(".", "-")
        val = body.get("value", "")
        # skip multi-line / very long shadows in CSS file for readability? keep them
        if "\n" in str(val):
            continue
        lines.append(f"  {css_name}: {val};")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="signals JSON")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--css-out", help="optional path to write CSS variables")
    args = parser.parse_args()
    signals = json.loads(open(args.input, encoding="utf-8").read())
    doc = build_token_doc(signals, args.source_url, args.domain)
    print(json.dumps(doc, indent=2))
    if args.css_out:
        open(args.css_out, "w", encoding="utf-8").write(tokens_to_css(doc))


if __name__ == "__main__":
    main()
