# dd-vreg — Visual Regression Reporter

Captures desktop and mobile screenshots for two sites, compares matching pages, generates pixel diffs, and writes timestamped Markdown + HTML reports. Powered by Playwright + pixelmatch.

## Install — Claude Code plugin

```bash
/plugin marketplace add jlyvers/dd-ai-skills
/plugin install dd-vreg@dd-skills
```

`SessionStart` bootstrap hook runs `npm install` + `npx playwright install chromium` on first session. `.dd-vreg-bootstrap.ok` sentinel skips subsequent runs. Skip Chromium download with `DD_VREG_SKIP_BROWSER=1` (CI / pre-installed).

## Install — Codex skill

```bash
bash install.sh
```

Installs to `${CODEX_HOME:-$HOME/.codex}/skills/dd-vreg/`, runs `npm install`, fetches Chromium, renders Codex `settings.json` from `hooks/hooks.json`.

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
node "${CLAUDE_PLUGIN_ROOT}/skills/dd-vreg/scripts/run_visual_regression.js" /path/to/spec.txt
```

Codex context:

```bash
node ~/.codex/skills/dd-vreg/scripts/run_visual_regression.js /path/to/spec.txt
```

## Output (under `web/<ProjectName>-MMDDYYYY-HHMM/`)

- `report.html` — browser review
- `report.md` — text summary
- `metrics.json`
- `screenshots/`
- `diffs/`

## Viewports

- Desktop: 1440 × 1200
- Mobile: 390 × 844

Report includes top-quarter and body diff ratios to flag rotating-hero false positives.

## Layout

```
dd-vreg-audit/
├── .claude-plugin/plugin.json
├── package.json + package-lock.json
├── hooks/{hooks.json, bootstrap.sh}
├── install.sh
└── skills/dd-vreg/
    ├── SKILL.md
    ├── scripts/run_visual_regression.js
    └── assets/agency-logo.svg
```

## Requirements

- Node.js >= 18
- npm
- Runtime that allows Chromium to launch (Playwright sandbox-friendly env)

## Caveats

- Dynamic components (rotating heroes, animated banners) can produce false positives. Top-quarter vs body diff ratio helps distinguish.
- Pages with mismatched heights are padded; large height deltas may inflate diff scores.
