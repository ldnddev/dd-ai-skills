# dd-a11y — Accessibility Audit Skill

Sharable accessibility audit skill for single-page or multi-page WCAG 2.2 reviews using Playwright and `@axe-core/playwright`. Ships in two formats: a **Claude Code plugin** (preferred) and a **Codex skill** installer (`install.sh`).

## Install — Claude Code plugin (one-shot)

```bash
/plugin marketplace add <github-owner>/dd-a11y-audit
/plugin install dd-a11y@dd-a11y-marketplace
```

That's it. On the next session, the `SessionStart` bootstrap hook (`hooks/bootstrap.sh`) runs `npm ci` automatically the first time; the package.json `postinstall` script then downloads pinned Chromium. A `.dd-a11y-bootstrap.ok` sentinel file makes subsequent sessions a no-op.

To skip the Chromium download (CI / preinstalled): set `DD_A11Y_SKIP_BROWSER=1` before plugin install.

## Install — Codex skill (legacy)

```bash
bash install.sh
```

Installs to `${CODEX_HOME:-$HOME/.codex}/skills/dd-a11y/` with `SKILL.md` at install root and Codex-style `settings.json` rendered from `hooks/hooks.json`.

## What is included

- `.claude-plugin/{plugin,marketplace}.json` — Claude Code plugin manifest + marketplace
- `skills/dd-a11y/SKILL.md` — canonical skill entry
- `skills/dd-a11y/references/` — WCAG rubric + checklist
- `hooks/hooks.json` — Claude Code hook wiring (uses `${CLAUDE_PLUGIN_ROOT}`)
- `hooks/bootstrap.sh` — SessionStart one-shot dep installer
- `hooks/a11y-{team-eval,enforce-edit,mark-reviewed}.sh` — UI-edit gating
- `scripts/run_a11y_audit.py` — pipeline orchestrator (single + multi-page)
- `scripts/{axe_audit,capture_a11y_screenshots,generate_a11y_report,test_a11y_skill}.py`
- `templates/{brand.json,dashboard.html,assets/}` — report branding
- `install.sh` — Codex install path

## Requirements

- Node.js 18+
- `npm`
- `python3`
- Internet access during installation to download npm packages and the Chromium browser runtime
- A runtime environment that allows Chromium to launch

From repo root:

```bash
bash install.sh
```

The installer copies the skill to `${CODEX_HOME:-$HOME/.codex}/skills/dd-a11y`, rewrites hook paths for the local machine, installs npm dependencies, and downloads Playwright Chromium.

## Verify the install

```bash
cd ~/.codex/skills/dd-a11y
npm run verify
python3 scripts/axe_audit.py https://example.com --json
```

If Chromium launch is blocked by a sandboxed environment, `axe_audit.py` returns a structured error explaining that the browser is installed but the current runtime does not allow it to launch.

## Use the skill

Typical prompt patterns:

- `a11y audit https://example.com`
- `perform accessibility audit on https://example.com`
- `full deep a11y audit https://example.com`

Direct CLI usage:

```bash
cd ~/.codex/skills/dd-a11y
python3 scripts/axe_audit.py https://example.com --level AA --json
python3 scripts/run_a11y_audit.py https://example.com
python3 scripts/run_a11y_audit.py --urls-file ./urls.txt
python3 scripts/run_a11y_audit.py --sitemap https://example.com/sitemap.xml --max-urls 25
python3 scripts/test_a11y_skill.py https://example.com
```

## Deliverables

`python3 scripts/run_a11y_audit.py <url>` generates output in:

- `web/[DOMAIN-a11y-audit-YYYY-MM-DD]/`

For example:

```text
web/example.com-a11y-audit-2026-04-27/
```

Generated files:

- `axe-results.json`
- `WCAG-AUDIT-REPORT.md`
- `ACCESSIBILITY-ACTION-PLAN.md`
- `REMEDIATION-TASKS.csv`
- `A11Y-CLIENT-REPORT.docx`
- `index.html`

For multi-page audits, the same output folder also contains:

- `pages/<page-slug>/axe-results.json`
- `pages/<page-slug>/screenshots/full-page.png`
- `pages/<page-slug>/screenshots/A11Y-###.png`

The CSV includes page-level context and screenshot paths. The HTML dashboard links to report files and issue screenshots. The DOCX includes page-level screenshot references.

## Troubleshooting

### `Node.js` not found
Install Node.js and rerun `./install.sh`.

### `playwright` or `@axe-core/playwright` missing
From the installed skill directory:

```bash
npm ci
```

### Chromium is installed but will not launch
This usually means the current environment blocks browser subprocesses or sandbox-related system calls. Verify in a normal host shell instead of a heavily restricted sandbox.

```bash
cd ~/.codex/skills/dd-a11y
npm run verify
```

### Reinstall

```bash
bash install.sh
```
