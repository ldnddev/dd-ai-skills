#!/usr/bin/env python3
"""
Capture a small crop for visual accessibility findings.

Full-page pin maps are not captured. Non-visual findings stay selector + HTML.
"""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
PACKAGE_JSON_PATH = SKILL_DIR / "package.json"


def load_results(path):
    return json.loads(Path(path).read_text())


IMPACT_ORDER = {
    "critical": 0,
    "serious": 1,
    "moderate": 2,
    "minor": 3,
}

# A crop is evidence only when the failure is something you have to see:
# contrast, use of color, text in an image, focus visibility / obscured focus,
# and target size. Names, alt, headings, and duplicate ids are the snippet.
VISUAL_RULE_IDS = frozenset({
    "color-contrast",
    "color-contrast-enhanced",
    "link-in-text-block",
    "target-size",
})
VISUAL_SC_TAGS = frozenset({
    "wcag141",    # 1.4.1 Use of Color
    "wcag143",    # 1.4.3 Contrast (Minimum)
    "wcag145",    # 1.4.5 Images of Text
    "wcag146",    # 1.4.6 Contrast (Enhanced)
    "wcag149",    # 1.4.9 Images of Text (No Exception)
    "wcag1411",   # 1.4.11 Non-text Contrast
    "wcag247",    # 2.4.7 Focus Visible
    "wcag2411",   # 2.4.11 Focus Not Obscured (Minimum)
    "wcag2412",   # 2.4.12 Focus Not Obscured (Enhanced)
    "wcag2413",   # 2.4.13 Focus Appearance
    "wcag255",    # 2.5.5 Target Size (Enhanced)
    "wcag258",    # 2.5.8 Target Size (Minimum)
})


def is_visual_finding(violation):
    """True when a screenshot is the evidence for this finding."""
    rule_id = violation.get("id") or violation.get("rule_id") or ""
    if rule_id in VISUAL_RULE_IDS:
        return True
    tags = violation.get("wcag_tags") or violation.get("tags") or []
    return any(tag in VISUAL_SC_TAGS for tag in tags)


def _first_selector(violation):
    previews = violation.get("nodes_preview") or []
    if not previews:
        return ""
    targets = previews[0].get("target") or []
    if not targets:
        return ""
    t = targets[0]
    if isinstance(t, list):
        return t[0] if t else ""
    return str(t) if t else ""


def _normalize_impacts(impacts):
    """Return list of impact names, or None meaning all impacts."""
    if impacts is None:
        return None
    if isinstance(impacts, str):
        impacts = [part.strip().lower() for part in impacts.split(",") if part.strip()]
    cleaned = [name for name in impacts if name in IMPACT_ORDER]
    return cleaned or None


def _sort_tasks(tasks):
    """Sitewide template shots come first so the per-page cap cannot drop them."""
    return sorted(
        tasks,
        key=lambda t: (
            0 if t.get("sitewide_representative") else 1,
            IMPACT_ORDER.get(t["impact"], 9),
            t["task_id"],
        ),
    )


def _wants_crop(task):
    if not task["selector"] or not task["visual"]:
        return False
    # False means a rolled-up duplicate. Absent means decide from the rule.
    if task.get("needs_crop") is False:
        return False
    return True


def build_capture_plan(
    results,
    cap=12,
    id_start=1,
    impacts=None,
    pin_impacts=None,
    pin_cap=None,
):
    """Build task ids and the visual crops to take.

    Task IDs are ``A11Y-{n:03d}`` starting at ``id_start``, unless the violation
    already has ``task_id`` (multi-page rollup assigns those).

    ``image_tasks`` are visual findings with a selector. The cap applies to
    page-only crops. Sitewide representatives are kept so the shared template
    is shot once. ``pin_tasks`` stays empty: full-page pin maps are not captured.
    ``pin_impacts`` and ``pin_cap`` are accepted and ignored.
    """
    del pin_impacts, pin_cap
    id_start = max(1, int(id_start))
    impact_filter = _normalize_impacts(impacts)

    all_tasks = []
    for index, violation in enumerate(results.get("violations", [])):
        task_num = id_start + index
        needs = violation.get("needs_crop", None) if "needs_crop" in violation else None
        all_tasks.append(
            {
                "task_id": violation.get("task_id") or f"A11Y-{task_num:03d}",
                "rule_id": violation.get("id", ""),
                "impact": (violation.get("impact") or "minor").lower(),
                "selector": _first_selector(violation),
                "visual": is_visual_finding(violation),
                "needs_crop": needs,
                "sitewide_representative": bool(violation.get("sitewide_representative")),
            }
        )

    pool = [t for t in all_tasks if _wants_crop(t)]
    if impact_filter is not None:
        allowed = set(impact_filter)
        pool = [t for t in pool if t["impact"] in allowed]
    pool = _sort_tasks(pool)
    representatives = [dict(t) for t in pool if t.get("sitewide_representative")]
    page_only = [dict(t) for t in pool if not t.get("sitewide_representative")]
    image_tasks = representatives + page_only[: max(0, int(cap))]

    return {
        "all_tasks": all_tasks,
        "image_tasks": image_tasks,
        "pin_tasks": [],
    }


def run_capture(
    url,
    results_path,
    output_dir,
    cap=12,
    id_start=1,
    impacts=None,
    pin_impacts=None,
    pin_cap=None,
    annotate=True,
    pin_format="jpeg",
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = build_capture_plan(
        load_results(results_path),
        cap=cap,
        id_start=id_start,
        impacts=impacts,
        pin_impacts=pin_impacts,
        pin_cap=pin_cap,
    )
    image_tasks = plan["image_tasks"] if annotate else []
    # pin_format is unused. Crops are PNG. The argument remains so older
    # command lines that passed --pin-format still run.

    script = f"""
const path = require('path');
const {{ createRequire }} = require('module');
const requireFromSkill = createRequire({json.dumps(str(PACKAGE_JSON_PATH))});
const {{ chromium }} = requireFromSkill('playwright');

const url = {json.dumps(url)};
const outputDir = {json.dumps(str(output_dir))};
const plan = {json.dumps(image_tasks)};

async function clearOverlays(page) {{
  await page.evaluate(() => {{
    document.querySelectorAll('[data-dd-a11y-overlay]').forEach((n) => n.remove());
    document.querySelectorAll('[data-dd-a11y-overlay-target]').forEach((el) => {{
      el.style.outline = '';
      el.style.outlineOffset = '';
      el.removeAttribute('data-dd-a11y-overlay-target');
    }});
  }});
}}

async function measureLocator(locator) {{
  return locator.evaluate((el) => {{
    const r = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    const visible =
      style.visibility !== 'hidden' &&
      style.display !== 'none' &&
      r.width > 0 &&
      r.height > 0;
    return {{
      width: r.width,
      height: r.height,
      visible,
    }};
  }});
}}

/**
 * Highlight + badge via the same locator. Returns true if overlay applied.
 * Places badge below the box when the element is near the top of the viewport
 * (getBoundingClientRect().top < 36) so the badge is not clipped.
 */
async function highlightIssue(locator, item) {{
  return locator.evaluate((el, item) => {{
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    el.setAttribute('data-dd-a11y-overlay-target', '1');
    el.style.outline = '3px solid #b00020';
    el.style.outlineOffset = '2px';
    const badge = document.createElement('div');
    badge.setAttribute('data-dd-a11y-overlay', 'badge');
    badge.textContent = `${{item.task_id}} · ${{item.rule_id}} · ${{item.impact}}`;
    const placeBelow = r.top < 36;
    const top = placeBelow
      ? r.bottom + window.scrollY + 4
      : Math.max(0, r.top + window.scrollY - 32);
    const left = Math.max(0, r.left + window.scrollX);
    badge.style.cssText = [
      'position:absolute',
      `left:${{left}}px`,
      `top:${{top}}px`,
      'background:#1a1a1a',
      'color:#fff',
      'font:12px/1.3 sans-serif',
      'padding:4px 8px',
      'border-radius:4px',
      'max-width:360px',
      'z-index:2147483647',
      'pointer-events:none',
      'box-shadow:0 1px 4px rgba(0,0,0,0.4)',
      'white-space:nowrap',
      'overflow:hidden',
      'text-overflow:ellipsis',
    ].join(';');
    document.documentElement.appendChild(badge);
    return true;
  }}, item);
}}

async function scrollToCenter(locator) {{
  await locator.evaluate((el) => {{
    el.scrollIntoView({{ block: 'center', inline: 'nearest' }});
  }});
}}

/** Viewport clip around the element. Padding keeps the badge and nearby background. */
function cropBox(box, viewport) {{
  const pad = 64;
  const minW = 320;
  const minH = 180;
  let width = Math.max(box.width + pad * 2, minW);
  let height = Math.max(box.height + pad * 2, minH);
  let x = box.x + box.width / 2 - width / 2;
  let y = box.y + box.height / 2 - height / 2;
  x = Math.max(0, x);
  y = Math.max(0, y);
  if (x + width > viewport.width) width = viewport.width - x;
  if (y + height > viewport.height) height = viewport.height - y;
  return {{
    x,
    y,
    width: Math.max(1, width),
    height: Math.max(1, height),
  }};
}}

function shotEntry(item, overrides) {{
  return Object.assign({{
    task_id: item.task_id,
    rule_id: item.rule_id,
    selector: item.selector || '',
    pin: item.pin,
    path: null,
  }}, overrides);
}}

(async () => {{
  const browser = await chromium.launch({{ headless: true, channel: 'chromium' }});
  const context = await browser.newContext({{ viewport: {{ width: 1440, height: 2200 }} }});
  const page = await context.newPage();
  const result = {{
    pin_map: null,
    pin_legend: [],
    issue_screenshots: [],
  }};
  // Preserve image_tasks order in issue_screenshots
  const screenshotsByTaskId = new Map();

  async function resolveLocatable(items, recordFailures) {{
    const found = [];
    for (const item of items) {{
      if (!item.selector) {{
        if (recordFailures) {{
          screenshotsByTaskId.set(item.task_id, shotEntry(item, {{ status: 'missing-selector' }}));
        }}
        continue;
      }}
      try {{
        const locator = page.locator(item.selector).first();
        const count = await locator.count();
        if (!count) {{
          if (recordFailures) {{
            screenshotsByTaskId.set(item.task_id, shotEntry(item, {{ status: 'not-found' }}));
          }}
          continue;
        }}
        const metrics = await measureLocator(locator);
        if (!metrics.visible) {{
          if (recordFailures) {{
            screenshotsByTaskId.set(item.task_id, shotEntry(item, {{ status: 'not-visible' }}));
          }}
          continue;
        }}
        found.push(item);
      }} catch (error) {{
        if (recordFailures) {{
          screenshotsByTaskId.set(item.task_id, shotEntry(item, {{
            status: 'capture-error',
            message: error && error.message ? error.message : String(error),
          }}));
        }}
      }}
    }}
    return found;
  }}

  try {{
    await page.goto(url, {{ waitUntil: 'networkidle' }});

    // Visual crops only. No full-page pin map.
    const annotateLocatable = await resolveLocatable(plan, true);
    for (const item of annotateLocatable) {{
      try {{
        await clearOverlays(page);
        const locator = page.locator(item.selector).first();
        const count = await locator.count();
        if (!count) {{
          screenshotsByTaskId.set(item.task_id, shotEntry(item, {{ status: 'not-found' }}));
          continue;
        }}

        await scrollToCenter(locator);
        await locator.scrollIntoViewIfNeeded();

        let applied = false;
        try {{
          applied = await highlightIssue(locator, item);
        }} catch (overlayErr) {{
          screenshotsByTaskId.set(item.task_id, shotEntry(item, {{
            status: 'capture-error',
            message: overlayErr && overlayErr.message ? overlayErr.message : String(overlayErr),
          }}));
          continue;
        }}

        if (!applied) {{
          screenshotsByTaskId.set(item.task_id, shotEntry(item, {{ status: 'not-found' }}));
          continue;
        }}

        const shotPath = path.join(outputDir, `${{item.task_id}}.png`);
        const box = await locator.boundingBox();
        const viewport = page.viewportSize();
        const shotOpts = {{ path: shotPath }};
        if (box && viewport) {{
          shotOpts.clip = cropBox(box, viewport);
        }}
        await page.screenshot(shotOpts);
        screenshotsByTaskId.set(item.task_id, shotEntry(item, {{
          path: shotPath,
          status: 'captured',
        }}));
      }} catch (error) {{
        screenshotsByTaskId.set(item.task_id, shotEntry(item, {{
          status: 'capture-error',
          message: error && error.message ? error.message : String(error),
        }}));
      }}
    }}

    result.issue_screenshots = plan
      .map((item) => screenshotsByTaskId.get(item.task_id))
      .filter(Boolean);
  }} finally {{
    await browser.close();
  }}
  console.log(JSON.stringify(result, null, 2));
}})().catch(error => {{
  console.error(JSON.stringify({{ error: true, message: error.message }}));
  process.exit(1);
}});
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as handle:
        handle.write(script)
        js_file = handle.name

    try:
        result = subprocess.run(
            ["node", js_file],
            capture_output=True,
            text=True,
            cwd=SKILL_DIR,
            check=False,
        )
        if result.returncode != 0:
            return {
                "error": True,
                "message": result.stderr.strip() or result.stdout.strip(),
            }
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return {
                "error": True,
                "message": f"Invalid capture JSON: {exc}",
                "stdout": (result.stdout or "")[:2000],
                "stderr": (result.stderr or "").strip(),
            }
    finally:
        if os.path.exists(js_file):
            os.unlink(js_file)


def main():
    parser = argparse.ArgumentParser(description="Capture accessibility screenshots for a page audit")
    parser.add_argument("url")
    parser.add_argument("--input", required=True, help="Path to axe-results.json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--cap",
        type=int,
        default=3,
        help="Max page-only visual crops (default 3). Sitewide representatives are not capped.",
    )
    parser.add_argument(
        "--id-start",
        type=int,
        default=1,
        help="First A11Y-### number for this page (use multi-page global sequencing)",
    )
    parser.add_argument(
        "--impacts",
        default="critical,serious",
        help="Comma-separated impacts for visual crops (default: critical,serious). Use 'all' for every impact.",
    )
    parser.add_argument(
        "--pin-impacts",
        default="critical,serious",
        help="Ignored. Full-page pin maps are not captured.",
    )
    parser.add_argument("--pin-cap", type=int, default=8, help="Ignored. Full-page pin maps are not captured.")
    parser.add_argument(
        "--no-annotate",
        action="store_true",
        help="Skip visual crops",
    )
    parser.add_argument(
        "--pin-format",
        choices=["jpeg", "png"],
        default="jpeg",
        help="Ignored. Crops are PNG.",
    )
    args = parser.parse_args()

    impacts = None if args.impacts.strip().lower() == "all" else args.impacts
    pin_impacts = None if args.pin_impacts.strip().lower() == "all" else args.pin_impacts

    print(
        json.dumps(
            run_capture(
                args.url,
                args.input,
                args.output_dir,
                cap=args.cap,
                id_start=args.id_start,
                impacts=impacts,
                pin_impacts=pin_impacts,
                pin_cap=args.pin_cap,
                annotate=not args.no_annotate,
                pin_format=args.pin_format,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
