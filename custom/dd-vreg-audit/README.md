# dd-vreg — Visual Regression Reporter

Captures desktop and mobile screenshots for two sites, compares matching pages with pixelmatch, buckets findings by severity, and writes a client-ready bundle: templated dashboard, Word document, CSV, action plan, Markdown summary, and raw metrics. Powered by Playwright + pixelmatch + JSZip.

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-vreg@dd-skills
```

`SessionStart` bootstrap hook runs `npm install` + `npx playwright install chromium` on first session. `.dd-vreg-bootstrap.ok` sentinel skips subsequent runs. Skip Chromium download with `DD_VREG_SKIP_BROWSER=1` (CI / pre-installed).

## Install — Codex skill

`bash install.sh` from this directory — runs `npm install`, fetches Chromium, renders Codex `settings.json` from `hooks/hooks.json`.

## Input format

Paste a spec block:

```text
#ProjectName
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

## Run

Plugin context:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/run_visual_regression.js" /path/to/spec.txt
```

Codex context:

```bash
node ~/.codex/skills/dd-vreg/scripts/run_visual_regression.js /path/to/spec.txt
```

## Output bundle — `web/<Project>-vreg-<YYYY-MM-DD>/`

Every successful run writes the full set:

| File | Purpose |
|---|---|
| `index.html` | Templated dashboard, axe-core 0 violations. Sidebar nav, KPI cards, severity table, per-page test/prod/diff grid, download buttons. |
| `DIFF-REPORT.docx` | Client-ready Word doc with severity summary + findings table. |
| `DIFFS.csv` | One row per page × viewport, severity-sorted. Project tracker import. |
| `ACTION-PLAN.md` | Severity-grouped remediation list with false-positive-pattern citations. |
| `report.md` | Slim Markdown summary. |
| `metrics.json` | Raw per-result objects. |
| `screenshots/` | Test + prod PNGs per page-per-viewport. |
| `diffs/` | Pixelmatch overlay PNGs. |
| `assets/` | Logo + favicon set. |

Same-day re-runs overwrite the directory.

## Severity

Each page-viewport pair is classified by body % and top-quarter % from the pixelmatch diff:

- 🔴 **Critical** — body diff ≥ 5%
- ⚠️ **Warning** — body diff 1–5%, OR top-quarter ≥ 10% with body < 1% (flagged as likely rotating hero)
- ✅ **Pass** — body diff < 1% AND top-quarter < 10%

Thresholds are intentionally hardcoded — see [`skills/dd-vreg/references/diff-thresholds.md`](skills/dd-vreg/references/diff-thresholds.md).

## Viewports

- Desktop: 1440 × 1200
- Mobile: 390 × 844 (deviceScaleFactor 2, isMobile, hasTouch)

## Layout

```
dd-vreg-audit/
├── CLAUDE.md                              ← skill-dev guide
├── .claude-plugin/plugin.json
├── package.json + package-lock.json       (jszip + pixelmatch + playwright + pngjs)
├── hooks/{hooks.json, bootstrap.sh}
├── install.sh
├── scripts/run_visual_regression.js       ← single-file orchestrator (root-level, matches dd-a11y)
├── templates/                             ← shared layout with dd-a11y / dd-seo
│   ├── dashboard.html
│   ├── brand.json
│   └── assets/{imgs/logo-mini.svg, favicon/*}
└── skills/dd-vreg/
    ├── SKILL.md
    └── references/
        ├── diff-thresholds.md
        └── false-positive-patterns.md
```

## Caveats

- Rotating heroes, A/B-test cookies, dynamic dates, lazy-loaded images, font swap, animated elements, geolocation gating, and consent banners can produce diffs without a real regression. See [`skills/dd-vreg/references/false-positive-patterns.md`](skills/dd-vreg/references/false-positive-patterns.md) for the operator playbook.
- Pages with mismatched heights are padded; large height deltas may inflate scores.
- The top-quarter vs body split keeps hero noise from masking real body regressions.
