#!/usr/bin/env python3
"""
Capture pin-map and annotated viewport screenshots for an accessibility audit page.
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


def build_capture_plan(results, cap=12, id_start=1):
    """Build full task list (stable IDs) and capped image subset.

    Task IDs are ``A11Y-{n:03d}`` with n starting at ``id_start`` so multi-page
    audits can assign globally unique IDs that match the report table.

    Returns:
      {
        "all_tasks": [{task_id, rule_id, impact, selector}, ...],
        "image_tasks": same shape, impact-sorted, selector required, max cap
      }
    """
    id_start = max(1, int(id_start))
    all_tasks = []
    for index, violation in enumerate(results.get("violations", [])):
        task_num = id_start + index
        all_tasks.append(
            {
                "task_id": f"A11Y-{task_num:03d}",
                "rule_id": violation.get("id", ""),
                "impact": (violation.get("impact") or "minor").lower(),
                "selector": _first_selector(violation),
            }
        )

    eligible = [t for t in all_tasks if t["selector"]]
    eligible.sort(
        key=lambda t: (IMPACT_ORDER.get(t["impact"], 9), t["task_id"])
    )
    # Copy so pin assignment does not mutate all_tasks entries
    image_tasks = [dict(t) for t in eligible[: max(0, int(cap))]]
    for pin, item in enumerate(image_tasks, start=1):
        item["pin"] = pin

    return {"all_tasks": all_tasks, "image_tasks": image_tasks}


def run_capture(url, results_path, output_dir, cap=12, id_start=1):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = build_capture_plan(load_results(results_path), cap=cap, id_start=id_start)
    image_tasks = plan["image_tasks"]

    script = f"""
const fs = require('fs');
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

/** Apply pin via the same locator used for count/measure. Returns true if pin DOM was added. */
async function addPin(locator, item) {{
  return locator.evaluate((el, item) => {{
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const pin = document.createElement('div');
    pin.setAttribute('data-dd-a11y-overlay', 'pin');
    pin.textContent = String(item.pin);
    pin.style.cssText = [
      'position:absolute',
      `left:${{r.left + window.scrollX + r.width / 2 - 12}}px`,
      `top:${{r.top + window.scrollY + r.height / 2 - 12}}px`,
      'width:24px',
      'height:24px',
      'border-radius:50%',
      'background:#b00020',
      'color:#fff',
      'font:bold 12px/24px sans-serif',
      'text-align:center',
      'border:2px solid #fff',
      'box-shadow:0 0 0 1px #000',
      'z-index:2147483646',
      'pointer-events:none',
    ].join(';');
    document.documentElement.appendChild(pin);
    return true;
  }}, item);
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
  const locatable = [];

  try {{
    await page.goto(url, {{ waitUntil: 'networkidle' }});

    for (const item of plan) {{
      if (!item.selector) {{
        screenshotsByTaskId.set(item.task_id, shotEntry(item, {{ status: 'missing-selector' }}));
        continue;
      }}

      try {{
        const locator = page.locator(item.selector).first();
        const count = await locator.count();
        if (!count) {{
          screenshotsByTaskId.set(item.task_id, shotEntry(item, {{ status: 'not-found' }}));
          continue;
        }}

        const metrics = await measureLocator(locator);
        if (!metrics.visible) {{
          screenshotsByTaskId.set(item.task_id, shotEntry(item, {{ status: 'not-visible' }}));
          continue;
        }}

        locatable.push(item);
      }} catch (error) {{
        screenshotsByTaskId.set(item.task_id, shotEntry(item, {{
          status: 'capture-error',
          message: error && error.message ? error.message : String(error),
        }}));
      }}
    }}

    // Pin map: only legend entries for pins that actually applied
    const pinned = [];
    if (locatable.length > 0) {{
      await clearOverlays(page);
      for (const item of locatable) {{
        try {{
          const locator = page.locator(item.selector).first();
          const count = await locator.count();
          if (!count) continue;
          const applied = await addPin(locator, item);
          if (applied) pinned.push(item);
        }} catch (e) {{
          // skip failed pin; do not claim it in pin_legend
        }}
      }}
      if (pinned.length > 0) {{
        const pinMapPath = path.join(outputDir, 'pin-map.png');
        await page.screenshot({{ path: pinMapPath, fullPage: true }});
        result.pin_map = pinMapPath;
        result.pin_legend = pinned.map((item) => ({{
          pin: item.pin,
          task_id: item.task_id,
          rule_id: item.rule_id,
          impact: item.impact,
        }}));
      }} else {{
        result.pin_map = null;
        result.pin_legend = [];
      }}
    }} else {{
      result.pin_map = null;
      result.pin_legend = [];
    }}

    for (const item of locatable) {{
      try {{
        await clearOverlays(page);
        const locator = page.locator(item.selector).first();
        const count = await locator.count();
        if (!count) {{
          screenshotsByTaskId.set(item.task_id, shotEntry(item, {{ status: 'not-found' }}));
          continue;
        }}

        await scrollToCenter(locator);
        // Prefer center scroll; also satisfy scrollIntoViewIfNeeded contract
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
        await page.screenshot({{ path: shotPath }});
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
    parser.add_argument("--cap", type=int, default=12, help="Max annotated issue screenshots (default 12)")
    parser.add_argument(
        "--id-start",
        type=int,
        default=1,
        help="First A11Y-### number for this page (use multi-page global sequencing)",
    )
    args = parser.parse_args()

    print(
        json.dumps(
            run_capture(
                args.url,
                args.input,
                args.output_dir,
                cap=args.cap,
                id_start=args.id_start,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
