# dd-a11y — Accessibility Audit Skill

WCAG 2.2 accessibility audit for single-page or multi-page web reviews. Playwright + `@axe-core/playwright` for evidence; LLM analysis for prioritization. Generates `WCAG-AUDIT-REPORT.md`, `ACCESSIBILITY-ACTION-PLAN.md`, `REMEDIATION-TASKS.csv`, `A11Y-CLIENT-REPORT.docx`, and an HTML dashboard.

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-a11y@dd-skills
```

`SessionStart` bootstrap hook runs `npm ci` + downloads pinned Chromium on first session. Skip browser download with `DD_A11Y_SKIP_BROWSER=1`.

## Install — Codex skill

```bash
bash install.sh
```

See [root README](../../README.md#codex-install-legacy) for layout details.

## Trigger phrases

- `a11y audit <url>`
- `perform accessibility audit on <url>`
- `full deep a11y audit <url>`
- `multi-page a11y audit <url-list-or-sitemap>`

## CLI usage

```bash
python3 scripts/axe_audit.py <url> --level AA --json
python3 scripts/run_a11y_audit.py <url>
python3 scripts/run_a11y_audit.py --urls-file ./urls.txt
python3 scripts/run_a11y_audit.py --sitemap https://example.com/sitemap.xml --max-urls 25
python3 scripts/test_a11y_skill.py <url>          # demo / Chromium-blocked fallback
```

Verify install:

```bash
npm run verify   # smoke-tests Chromium launch
```

## Deliverables (under `web/<domain>-a11y-audit-<date>/`)

- `axe-results.json`
- `WCAG-AUDIT-REPORT.md`
- `ACCESSIBILITY-ACTION-PLAN.md`
- `REMEDIATION-TASKS.csv`
- `A11Y-CLIENT-REPORT.docx`
- `index.html`

Multi-page adds:

- `pages/<page-slug>/axe-results.json`
- `pages/<page-slug>/screenshots/full-page.png`
- `pages/<page-slug>/screenshots/A11Y-###.png`

CSV includes page-level context + screenshot paths. HTML dashboard links to report files and issue screenshots. DOCX embeds page-level screenshots.

## UI-edit hook gating

`hooks/a11y-enforce-edit.sh` blocks `Edit`/`Write` on UI files (`.jsx`, `.tsx`, `.vue`, `.svelte`, `.html`, `.css`, etc.) until `accessibility-agents:accessibility-lead` subagent runs in the same session. `hooks/a11y-mark-reviewed.sh` clears the block via a `/tmp` session marker.

## Caveats

- If Chromium fails to launch (sandboxed runtime), `axe_audit.py` returns a structured JSON error with `missing_dependencies` + `install_commands`. Use `test_a11y_skill.py` as a fallback report path.
- `hooks/a11y-team-eval.sh` injects a mandatory delegation instruction on web projects. Disable by removing it from `hooks/hooks.json` if not needed.
