# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This repo is the **source bundle** for a skill named `dd-a11y` that runs WCAG 2.2 accessibility audits. It ships in two formats:

- **Claude Code plugin** (canonical): `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`. Skill body lives at `skills/dd-a11y/SKILL.md`. Hooks wired through `hooks/hooks.json` using `${CLAUDE_PLUGIN_ROOT}`. First-session bootstrap via `hooks/bootstrap.sh` (SessionStart) runs `npm ci`, which triggers the `package.json` `postinstall` to download pinned Chromium.
- **Codex skill** (legacy): `install.sh` mirrors the tree into `${CODEX_HOME:-$HOME/.codex}/skills/dd-a11y`, promotes `skills/dd-a11y/SKILL.md` to the install root, and renders `settings.json` from `hooks/hooks.json` (rewriting `${CLAUDE_PLUGIN_ROOT}` to the absolute install dir).

`SKILL_DIR` in Python scripts resolves to `Path(__file__).parent.parent` — i.e. plugin root or Codex install root. `package.json` / `node_modules` / Chromium all live there. There is one canonical `SKILL.md` (`skills/dd-a11y/SKILL.md`); install.sh copies it into the Codex install root at install time.

## Common commands

Install (from repo root):

```bash
bash install.sh                  # copy → ~/.codex/skills/dd-a11y, npm ci (postinstall pulls Chromium)
```

Run from installed skill dir (`~/.codex/skills/dd-a11y`) or plugin root:

```bash
npm run verify                                                      # smoke-test Chromium launch
python3 scripts/axe_audit.py <url> --level AA --json                # raw axe pass, prints/saves JSON
python3 scripts/run_a11y_audit.py <url>                             # full pipeline → web/<domain>-a11y-audit-<date>/
python3 scripts/run_a11y_audit.py --urls-file ./urls.txt            # multi-page from file
python3 scripts/run_a11y_audit.py --sitemap <url> --max-urls 25     # multi-page from sitemap
python3 scripts/test_a11y_skill.py <url>                            # demo/fallback when Chromium blocked
```

No test suite, linter, or formatter is configured. `npm run verify` is the only automated check.

## Architecture

Pipeline is a chain of subprocess-invoked Python scripts under `scripts/`. `run_a11y_audit.py` is the orchestrator — it does not import the others; it shells out to them. Stay consistent with that pattern when adding stages.

```
run_a11y_audit.py
  ├─ axe_audit.py            (one subprocess per URL)
  │    └─ node -e <inline JS> using playwright + @axe-core/playwright
  ├─ capture_a11y_screenshots.py   (per page, multi-mode only)
  └─ generate_a11y_report.py       (final stage, consumes combined JSON)
```

Key contracts between stages:

- **`axe-results.json` is the canonical handoff format.** `axe_audit.py` writes it; `generate_a11y_report.py` reads it. Single-page mode writes one file at the output root. Multi-page mode writes per-page files under `pages/<slug>/axe-results.json` and an aggregated file at the output root with shape `{metadata, summary, principle_counts, pages[], recommendations[]}` (see `aggregate_pages` in `run_a11y_audit.py:128`).
- **Exit codes are semantic, not just success/failure.** `axe_audit.py` exits `0` (clean), `2` (critical violations present), `3` (>5 serious violations), `1` (error). `run_a11y_audit.py:295` treats `0/2/3` as "audit ran fine, continue to report generation" — do not collapse these.
- **`SKILL_DIR` resolves relative to the script file**, so `package.json` and `templates/` are found in the installed copy, not CWD. Output (`web/<domain>-a11y-audit-<date>/`) is written under CWD.
- **Node-side execution**: `axe_audit.py` builds a JS string, writes it to a tempfile, runs `node` with `cwd=SKILL_DIR`, and uses `createRequire(<package.json>)` so the inline script resolves modules against the skill's `node_modules`. URL and level are interpolated directly into the JS string.
- **Deliverables** (`generate_a11y_report.py`): `WCAG-AUDIT-REPORT.md`, `ACCESSIBILITY-ACTION-PLAN.md`, `REMEDIATION-TASKS.csv`, `A11Y-CLIENT-REPORT.docx` (built as a ZIP), `index.html`. Branding pulled from `templates/brand.json` and `templates/assets/`.

## Hooks (Codex/Claude Code integration)

`hooks/hooks.json` is the single source of truth for hook wiring. Plugin install consumes it directly; `install.sh` renders it into Codex `settings.json` with `${CLAUDE_PLUGIN_ROOT}` replaced.

- `bootstrap.sh` — `SessionStart`: idempotent `npm ci` if `node_modules/playwright` missing; writes `.dd-a11y-bootstrap.ok` sentinel. `DD_A11Y_SKIP_BROWSER=1` skips Chromium download.
- `a11y-team-eval.sh` — `UserPromptSubmit`: detects web projects (package.json deps, framework configs, UI file extensions) or UI keywords; injects an instruction to delegate to `accessibility-agents:accessibility-lead`.
- `a11y-enforce-edit.sh` — `PreToolUse` on `Edit|Write`: emits `permissionDecision: "deny"` for UI-file edits unless `/tmp/a11y-reviewed-<session_id>` exists.
- `a11y-mark-reviewed.sh` — `PostToolUse` on `Agent`: creates that marker after an `accessibility-lead` subagent runs.

The enforce/mark-reviewed pair depends on a session-scoped marker in `/tmp`. Removing or renaming either breaks the unlock path.

## Sandbox / Chromium failure mode

`axe_audit.py:check_dependencies` distinguishes "Playwright not installed" from "Chromium installed but cannot launch in this sandbox" and returns a structured JSON error with `missing_dependencies` and `install_commands`. Preserve this — `test_a11y_skill.py` is the deliberate fallback path for the second case, and downstream code in `run_a11y_audit.py` treats a JSON-shaped error as a non-fatal page result rather than a crash.

## Reference material

`skills/dd-a11y/SKILL.md` (workflow) and `skills/dd-a11y/references/{wcag-audit-rubric,wcag-checklist}.md` (rubric/checklist) — read by the LLM at audit time, not by the scripts. Edit to change audit guidance without touching code.
