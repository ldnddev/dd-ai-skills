#!/usr/bin/env python3
"""
Capture full-page and issue-level screenshots for an accessibility audit page.
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


def build_capture_plan(results):
    plan = []
    for index, violation in enumerate(results.get("violations", []), start=1):
        selector = ""
        previews = violation.get("nodes_preview") or []
        if previews:
            targets = previews[0].get("target") or []
            if targets:
                selector = targets[0]
        plan.append(
            {
                "task_id": f"A11Y-{index:03d}",
                "rule_id": violation.get("id", ""),
                "selector": selector,
            }
        )
    return plan


def run_capture(url, results_path, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = build_capture_plan(load_results(results_path))

    script = f"""
const fs = require('fs');
const path = require('path');
const {{ createRequire }} = require('module');
const requireFromSkill = createRequire({json.dumps(str(PACKAGE_JSON_PATH))});
const {{ chromium }} = requireFromSkill('playwright');

const url = {json.dumps(url)};
const outputDir = {json.dumps(str(output_dir))};
const plan = {json.dumps(plan)};

(async () => {{
  const browser = await chromium.launch({{ headless: true, channel: 'chromium' }});
  const context = await browser.newContext({{ viewport: {{ width: 1440, height: 2200 }} }});
  const page = await context.newPage();
  const result = {{
    full_page: null,
    issue_screenshots: []
  }};

  try {{
    await page.goto(url, {{ waitUntil: 'networkidle' }});
    const fullPagePath = path.join(outputDir, 'full-page.png');
    await page.screenshot({{ path: fullPagePath, fullPage: true }});
    result.full_page = fullPagePath;

    for (const item of plan) {{
      if (!item.selector) {{
        result.issue_screenshots.push({{ ...item, path: null, status: 'missing-selector' }});
        continue;
      }}

      try {{
        const locator = page.locator(item.selector).first();
        const count = await locator.count();
        if (!count) {{
          result.issue_screenshots.push({{ ...item, path: null, status: 'not-found' }});
          continue;
        }}

        await locator.scrollIntoViewIfNeeded();
        const shotPath = path.join(outputDir, `${{item.task_id}}.png`);
        await locator.screenshot({{ path: shotPath }});
        result.issue_screenshots.push({{ ...item, path: shotPath, status: 'captured' }});
      }} catch (error) {{
        result.issue_screenshots.push({{
          ...item,
          path: null,
          status: 'capture-error',
          message: error && error.message ? error.message : String(error),
        }});
      }}
    }}
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
        return json.loads(result.stdout)
    finally:
        if os.path.exists(js_file):
            os.unlink(js_file)


def main():
    parser = argparse.ArgumentParser(description="Capture accessibility screenshots for a page audit")
    parser.add_argument("url")
    parser.add_argument("--input", required=True, help="Path to axe-results.json")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    print(json.dumps(run_capture(args.url, args.input, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
