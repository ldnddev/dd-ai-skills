---
name: dd-vreg
description: Capture desktop and mobile screenshots for two websites, compare matching pages, generate pixel diffs, and write timestamped Markdown and HTML reports. Use when the user pastes a spec with a #Project_Name line, two URLs, and one or more page paths for reusable visual regression testing.
---

# Visual Regression Reporter

Use this skill when the user wants a repeatable visual regression run between two sites.

## Input format

Expect pasted text that includes:
- A line starting with `#` for the project name
- Two site URLs
- One or more page paths beginning with `/`

Example:

```text
#AtlanticTech
- URL's
  - https://test.example.com
  - https://www.example.com
- Pages
  - /
  - /about/
```

## Workflow

1. Save the pasted spec to a temporary text file in the current workspace.
2. Ensure the skill dependencies are installed by running `npm install` inside this skill folder if `node_modules` is missing.
3. Run `scripts/run_visual_regression.js` with the spec file path.
4. The script creates an output folder inside `web/` in the current working directory, named `web/Project_Name-MMDDYYYY-HHMM`.
5. Review the generated `report.md` and `report.html`, then summarize the main regressions for the user.

## Commands

Dependencies install automatically on first session via the plugin's SessionStart hook. To re-run manually:

```bash
cd "${CLAUDE_PLUGIN_ROOT}" && npm install && npx playwright install chromium
```

Run the report:

```bash
node "${CLAUDE_PLUGIN_ROOT}/skills/dd-vreg/scripts/run_visual_regression.js" /path/to/spec.txt
```

## Outputs

The generated folder contains:
- `agency-logo.svg`
- `report.html` for browser review
- `report.md` for text summary
- `metrics.json`
- `screenshots/`
- `diffs/`

## Notes

- Desktop viewport is `1440x1200`.
- Mobile viewport is `390x844`.
- The script highlights pixel differences and pads shorter images when page heights differ.
- The report includes top-quarter and body diff ratios to help identify likely hero-only false positives.
- Dynamic components such as rotating heroes can still produce false positives; call that out when the top-quarter diff is high but the body diff stays low.
