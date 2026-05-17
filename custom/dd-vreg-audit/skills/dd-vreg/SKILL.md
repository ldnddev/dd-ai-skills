---
name: dd-vreg
description: Capture desktop and mobile screenshots for two websites, compare matching pages with pixelmatch, bucket findings by severity (Critical / Warning / Pass), and write a client bundle (templated dashboard, DOCX, CSV, Action Plan, Markdown summary, metrics JSON). Use when the user pastes a spec with a #Project_Name line, two URLs, and one or more page paths.
---

# Visual Regression Reporter

Use this skill when the user wants a repeatable visual regression run between two sites.

## Input format

Expect pasted text that includes:

- A line starting with `#` for the project name
- Two site URLs (test environment first, production second)
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
  - /pricing/
```

## Trigger phrases

- "run visual regression on these sites"
- "diff <url1> against <url2> for / and /about"
- "compare staging vs production for these pages"

## Workflow

1. Save the pasted spec to a temporary text file in the current workspace.
2. Ensure dependencies are installed by running `npm install` inside this skill folder if `node_modules` is missing. (Auto-handled on first session via the plugin's `SessionStart` hook.)
3. Run `../../scripts/run_visual_regression.js` with the spec file path.
4. The script writes a client bundle to `web/<Project>-vreg-<YYYY-MM-DD>/` in the current working directory. Same-day re-runs **overwrite** the directory.
5. Review the generated `index.html` (templated dashboard) and `ACTION-PLAN.md`, then summarize the main regressions for the user.

## Commands

First-time install (Claude Code plugin auto-runs this via `SessionStart`):

```bash
cd "${CLAUDE_PLUGIN_ROOT}" && npm install && npx playwright install chromium
```

Run the report:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/run_visual_regression.js" /path/to/spec.txt
```

Skip Chromium download (CI / pre-installed):

```bash
DD_VREG_SKIP_BROWSER=1 npm install
```

## Mandatory bundle artifacts

Every successful run writes **all** of these to `web/<Project>-vreg-<YYYY-MM-DD>/`:

| File | Purpose |
|---|---|
| `index.html` | Templated dashboard (default browser entry). Sidebar nav (Overview / Diffs / Per-Page Previews / Downloads), 4 KPI cards, severity table, per-page preview grid (test \| prod \| diff per viewport), download buttons. WCAG 2.2 AA compliant. |
| `DIFF-REPORT.docx` | Client-ready Word document — project metadata, severity summary, full findings table. |
| `DIFFS.csv` | One row per page × viewport for Jira / Linear / Asana import. Columns: project, page, viewport, severity, body_pct, top_quarter_pct, changed_ratio_pct, note, test_screenshot, prod_screenshot, diff_image. Severity-sorted (Critical → Warning → Pass). |
| `ACTION-PLAN.md` | Severity-grouped remediation list. Rotating-hero warnings cite `references/false-positive-patterns.md`. |
| `report.md` | Slim Markdown summary linking to the bundle. |
| `metrics.json` | Raw per-result objects (severity, dimensions, pixel counts, region metrics, screenshot paths). |
| `screenshots/<viewport>/<test\|prod>/<slug>.png` | Captured screenshots per page-per-viewport-per-environment. |
| `diffs/<viewport>/<slug>.png` | Pixelmatch overlay PNGs (red = changed pixels). |
| `assets/` | Logo (`imgs/logo-mini.svg`) + favicon set copied from `templates/assets/`. |

## Severity vocabulary

The orchestrator classifies each page-viewport pair using two metrics from the pixelmatch diff:

- `bodyPct` — percent of pixels changed below the top quarter
- `topQuarterPct` — percent of pixels changed in the top quarter

| Severity | Glyph | Rule |
|---|---|---|
| Critical | 🔴 | `bodyPct >= 5.0` |
| Warning | ⚠️ | `bodyPct >= 1.0 AND < 5.0` |
| Warning | ⚠️ | `topQuarterPct >= 10.0 AND bodyPct < 1.0` — note `"Likely rotating hero — verify"` |
| Pass | ✅ | `bodyPct < 1.0 AND topQuarterPct < 10.0` |

Only these four exact labels are emitted. New severities are silently dropped by the CSV / dashboard / action plan writers.

See `references/diff-thresholds.md` for rationale, `references/false-positive-patterns.md` for operator guidance on distinguishing real regressions from rotating heroes, A/B tests, lazy loads, etc.

## Viewports

- Desktop: 1440 × 1200
- Mobile: 390 × 844 (deviceScaleFactor 2, isMobile true, hasTouch true)

## Capture hardening

`capturePage()` disables animations, hides chat widgets / reCAPTCHA badges, sets `reduced-motion: reduce`, waits 4s after `domcontentloaded`, scrolls to top, awaits `document.fonts.ready`, then screenshots fullPage. These mitigate most timing-related false positives but do not eliminate rotating heroes, A/B-test cookies, or geolocation-gated content — see `references/false-positive-patterns.md`.

## After the run

Summarize for the user:

1. Total diffs (Critical + Warning) vs total comparisons (`spec.pages.length × 2 viewports`).
2. Per-severity counts.
3. The top 3 Critical findings (page + viewport + body %).
4. Any Warning-with-rotating-hero notes that need manual verification.
5. Point them at `index.html` for the interactive dashboard and `DIFF-REPORT.docx` for client delivery.
