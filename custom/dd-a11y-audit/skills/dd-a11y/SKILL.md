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

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/dd-a11y/references/wcag-audit-rubric.md`, `${CLAUDE_PLUGIN_ROOT}/scripts/wcag_criteria.py` (the WCAG 2.2 criterion list), and `wcag-checklist.md`.
2. Run the pipeline:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_a11y_audit.py <url>
# same scan, explicit: WCAG 2.2 Level AA
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_a11y_audit.py <url> --level AA
```

Multi-page (default **light** screenshots — visual crops only):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_a11y_audit.py --urls-file ./urls.txt
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_a11y_audit.py --sitemap https://example.com/sitemap.xml --max-urls 25

# All impacts, higher page-only crop cap
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_a11y_audit.py --urls-file ./urls.txt --screenshot-mode full

# No images
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_a11y_audit.py --urls-file ./urls.txt --screenshot-mode off
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
- `pages/<slug>/screenshots/A11Y-###.png` — crop of a visual finding, when one was captured

### Screenshot modes (`--screenshot-mode`)

| Mode | Behavior |
|------|----------|
| **`light` (default)** | Crop only visual findings (`is_visual_finding` in `scripts/capture_a11y_screenshots.py`): contrast, target size, focus, text in images. Critical and serious. Cap **3** page-only crops per page, on every page. |
| **`full`** | Same crops for every impact. Cap **12** page-only crops per page. |
| **`off`** | No screenshots (`--no-screenshots` is an alias). |

Repeated chrome (header, footer, nav, cookie or consent banner) and any other finding with the same rule and selector on more than one URL are one sitewide finding and one crop, on the first page where it appears. Page-only visual findings keep their own crop. Names, alt text, headings, and duplicate ids stay selector + HTML, with no image.

Optional: `--screenshot-cap N`, `--annotated-pages N` (only the N worst pages; default is every page), `--embed-screenshots` (inline images in DOCX/MD). Selector + HTML snippet remain the source of truth.

## Notes

- Default scan is **WCAG 2.2 Level AA**. Pass `--level A` or `--level AAA` to override. The axe tag set for each level lives in `scripts/axe_audit.py` (`wcag_tags`). Do not pass a different tag list.
- Before every audit, `axe_audit.py --prepare-axe` installs the npm `latest` dist-tags of `axe-core` and `@axe-core/playwright` into `.axe-runtime/` and the scan loads that copy. Do not pin an older axe-core or skip prepare.
- The HTML dashboard does not animate. Do not add `data-sal`, `data-sal-delay`, `data-sal-duration`, or `data-sal-easing` to it.
- Node deps (`playwright`, `@axe-core/playwright`) and Chromium are installed by the plugin postinstall step. The scan still refreshes axe-core at run time.
- If Chromium fails to launch, the runner emits a structured JSON error with `missing_dependencies` and `install_commands`. Document blocked checks as environment limitations.
- Screenshot capture runs after axe via `capture_a11y_screenshots.py` (best-effort; failures do not block the report).
- The numeric score is the share of axe rules that passed. It is not a WCAG conformance claim. Do not describe a score as "AA compliant".
- The report lists success criteria at the scanned level that had no axe rule execute. The level follows `--level` (default AA). The catalog is `scripts/wcag_criteria.py`.
