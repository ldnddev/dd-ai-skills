---
name: dd-a11y
description: >
  WCAG 2.2 accessibility audit for single-page or multi-page web reviews using
  Playwright and @axe-core/playwright. Generates client deliverables
  (Markdown report, action plan, CSV, DOCX, HTML dashboard). Falls back to a
  structured error when Chromium cannot launch.
---

# dd-a11y — WCAG Accessibility Audit Skill

Run automated WCAG 2.2 accessibility audits and produce a client-ready report set. Backed by Playwright + `@axe-core/playwright` for evidence collection and an LLM analysis pass for prioritization and remediation guidance.

## Trigger phrases

- `a11y audit <url>`
- `dd-a11y audit <url>`
- `perform accessibility audit on <url>`
- `full deep a11y audit <url>`
- `multi-page a11y audit <url-list-or-sitemap>`

## Workflow

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/dd-a11y/references/wcag-audit-rubric.md` and `wcag-checklist.md`.
2. Run the pipeline:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_a11y_audit.py <url> --level AA
```

Multi-page:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_a11y_audit.py --urls-file ./urls.txt
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_a11y_audit.py --sitemap https://example.com/sitemap.xml --max-urls 25
```

3. Chromium-blocked fallback (sandboxed runtimes):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/test_a11y_skill.py <url>
```

4. For each finding, document: evidence, WCAG reference, severity, impact, fix.

## Deliverables (saved under `web/<domain>-a11y-audit-<date>/`)

- `WCAG-AUDIT-REPORT.md`
- `ACCESSIBILITY-ACTION-PLAN.md`
- `REMEDIATION-TASKS.csv`
- `A11Y-CLIENT-REPORT.docx`
- `index.html`
- `pages/<slug>/axe-results.json`
- `pages/<slug>/screenshots/full-page.png`
- `pages/<slug>/screenshots/A11Y-###.png`

## Notes

- Default WCAG level is AA. Pass `--level A` or `--level AAA` to override.
- Node deps (`playwright`, `@axe-core/playwright`) and Chromium are installed by the plugin postinstall step.
- If Chromium fails to launch, the runner emits a structured JSON error with `missing_dependencies` and `install_commands`. Document blocked checks as environment limitations.
- Per-issue screenshots are best-effort. Page-level full-page screenshot is the floor.
