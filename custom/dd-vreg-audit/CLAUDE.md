# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is **not an application** — it's a packaged agentic **Skill** (`SKILL.md` is the entry manifest) loaded by Claude Code, Codex, or other agent IDEs to capture visual-regression diffs between two website environments. There is no build system, no test suite, no service to run. The "code" is two things:

1. **Markdown content** under `skills/dd-vreg/SKILL.md` and `skills/dd-vreg/references/` that the host LLM reads to plan the run.
2. **Standalone Node.js script** at `skills/dd-vreg/scripts/run_visual_regression.js` invoked by the agent. It drives Playwright (capture), pixelmatch (diff), JSZip (DOCX assembly), and emits the full client bundle.

When working in this repo, you are usually editing the skill's instructions, the report template, or the orchestrator script — not running an audit.

## Common commands

No package manager workflow beyond `npm install`. No Makefile.

```bash
# First-time install (also auto-runs via SessionStart bootstrap hook)
cd "${CLAUDE_PLUGIN_ROOT}" && npm install && npx playwright install chromium

# Run a regression audit (single command, takes a spec file path)
node "${CLAUDE_PLUGIN_ROOT}/scripts/run_visual_regression.js" /path/to/spec.txt

# Skip Chromium download (CI / pre-installed)
DD_VREG_SKIP_BROWSER=1 npm install
```

Spec file format:

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

The orchestrator writes `web/<ProjectName>-vreg-<YYYY-MM-DD>/` containing `index.html`, `DIFF-REPORT.docx`, `DIFFS.csv`, `ACTION-PLAN.md`, `report.md`, `metrics.json`, `screenshots/`, `diffs/`, `assets/`.

## Architecture

```
dd-vreg-audit/                                 ← plugin root
├── scripts/run_visual_regression.js           ← single-file Node entry point (matches dd-a11y)
│     ├─ parseSpec / sanitizeProjectName           ← spec parsing
│     ├─ capturePage (Playwright)                  ← per-page-per-viewport screenshots
│     ├─ diffImages (pixelmatch + pngjs)           ← pixel diff with top-quarter vs body split
│     ├─ classifySeverity                          ← Critical/Warning/Pass bucketing
│     ├─ render* helpers                           ← template substitution + per-section HTML
│     ├─ writeCsv / writeActionPlan / writeDocx    ← deliverable writers
│     └─ copyTemplateAssets                        ← recursive asset copy into bundle
├── templates/                                 ← shared with dd-a11y / dd-seo layout
│   ├── dashboard.html                         ← Tailwind dashboard with {{PLACEHOLDERS}}
│   ├── brand.json                             ← agency name, logo path, copy strings
│   └── assets/                                ← logo-mini.svg + favicon set
└── skills/dd-vreg/
    ├── SKILL.md                               ← top-level orchestrator manifest
    └── references/
        ├── diff-thresholds.md                 ← Critical/Warning/Pass rule definitions
        └── false-positive-patterns.md         ← Common reasons a diff fires without a bug
```

The script resolves `templates/` via `pluginRoot = path.resolve(__dirname, '..')` from `scripts/`. Don't move `templates/` or `scripts/` back inside the skill — they live at plugin root to match dd-a11y.

### Severity contract

- `Critical` (🔴): `bodyPct >= 5.0`
- `Warning` (⚠️): `bodyPct >= 1.0 AND < 5.0`, OR `topQuarterPct >= 10.0 AND bodyPct < 1.0` (with note `"Likely rotating hero — verify"`)
- `Pass` (✅): everything else

Thresholds are intentionally hardcoded — see [diff-thresholds.md](skills/dd-vreg/references/diff-thresholds.md) for rationale. Do not move them into `brand.json`.

### Output bundle contract

Every successful run writes **all** of these to `web/<Project>-vreg-<YYYY-MM-DD>/`:

| File | Purpose |
|---|---|
| `index.html` | Templated dashboard (default browser entry) |
| `DIFF-REPORT.docx` | Client-ready Word document |
| `DIFFS.csv` | One row per page × viewport for Jira/Linear/Asana import |
| `ACTION-PLAN.md` | Severity-grouped remediation list |
| `report.md` | Slim Markdown summary linking to the bundle |
| `metrics.json` | Raw metrics for programmatic consumption |
| `screenshots/` | Test + prod PNGs per page-per-viewport |
| `diffs/` | Pixelmatch overlay PNGs per page-per-viewport |
| `assets/` | Logo + favicon set (mirror of `templates/assets/`) |

Same-day re-runs **overwrite** the directory (matching dd-a11y / dd-seo behavior). If you need historical comparisons, copy the bundle elsewhere before re-running.

## Editing rules specific to this skill

These are non-obvious invariants. Violating them breaks the contract that the report HTML, CSV, and DOCX share.

1. **Severity vocabulary** — only `Critical` / `Warning` / `Pass` (with the 🔴 / ⚠️ / ✅ glyphs). New severities are silently dropped by the CSV writer and the dashboard severity table.
2. **Bundle artifact set is mandatory** — `writeDocx`, `writeCsv`, `writeActionPlan`, and the templated `index.html` must all run on every successful audit. If one fails, log it and continue; do not silently skip.
3. **`{{PLACEHOLDER}}` discipline** — every placeholder in `templates/dashboard.html` must have a matching substitution in `renderTemplate()`. Unresolved placeholders render literally and look like bugs to clients. Run `grep -oE '\{\{[A-Z_]+\}\}' web/.../index.html` after every change.
4. **`assets/` is a recursive copy** — favicons and logos live in subdirs of `templates/assets/`. The flat-copy bug from dd-seo (`os.listdir + isfile` only) must not return. Use `fs.cp(..., { recursive: true })` or equivalent.
5. **Output dir naming is `web/<Project>-vreg-<YYYY-MM-DD>/`** — no hour/minute. Matches dd-a11y/dd-seo. Tests scripted on the legacy `web/<Project>-MMDDYYYY-HHMM/` format must be updated.
6. **WCAG 2.2 AA on the dashboard** — `index.html` must pass axe-core with zero violations. The skill itself ships visual regression audits; its own deliverable being inaccessible is unacceptable. Run axe-core via playwright after template changes.
7. **`SessionStart` bootstrap idempotency** — `hooks/bootstrap.sh` writes `.dd-vreg-bootstrap.ok` sentinel and skips on subsequent sessions. `DD_VREG_SKIP_BROWSER=1` skips Chromium download. Do not remove either escape hatch.
8. **No third-party CDN dependency in the audit logic** — Playwright and pixelmatch are bundled via `npm install`. The dashboard HTML loads Tailwind + Font Awesome from CDN — that is intentional and acceptable for a client deliverable; the audit script itself does not.

## Reference material

- `skills/dd-vreg/SKILL.md` — workflow contract loaded by the host LLM.
- `skills/dd-vreg/references/diff-thresholds.md` — severity rule definitions.
- `skills/dd-vreg/references/false-positive-patterns.md` — operator guide for distinguishing real regressions from rotating heroes, A/B tests, lazy loads, etc.

## Repo layout context

This repo is `custom/dd-vreg-audit` inside the larger `dd-ai-skills` monorepo (siblings: `custom/dd-a11y-audit`, `custom/dd-seo-audit`, `contrib/`). The repo's git root is `dd-ai-skills/`, but all code in this skill lives under this subdirectory. Commits should describe changes to the skill, not the parent project.
