# Dashboard Template Notes

Client-facing HTML dashboard for the dd-a11y audit. Wired into
`scripts/generate_a11y_report.py::build_dashboard` — editing these files changes
every audit dashboard the script emits.

## Styling: ldnddev Framework (not bespoke CSS)

The dashboard is built from **ldnddev Framework** components, not a self-contained
theme. The head links the compiled framework build:

```html
<link rel="stylesheet" href="assets/css/style.min.css">
<script src="assets/js/main.min.js" defer></script>
```

`build_dashboard` copies `templates/assets/{css,js,favicon,imgs}` into the output
bundle so those links resolve. Column sort, `aria-sort`, and scroll-region
keyboard access on the task table come from the framework's `dd_data_table` JS —
the template's own `<script>` only adds the filter, CSV export, a polite live
region, and in-page focus handling.

**Dark mode** is driven by the framework via `prefers-color-scheme` only — there
is no manual light/dark toggle. Brand color/font tokens are **not** used
(the framework's compiled tokens own the look); `brand.json` now only supplies
the agency lockup and report copy.

## Components used

| Region | Component |
|---|---|
| Masthead | `dd-header` (banner, outside `<main>`) |
| Summary readout | `app-summary` `<dl>` (shell CSS — no framework component) |
| Severity breakdown | `dd-bar-chart` (server-rendered rows) |
| Page previews | `dd-card` grid |
| Task table | `dd-data-table` + `dd-badge` severity cells |
| Downloads | `<a class="dd-button -secondary" download>` |
| Footer | `dd-footer` (contentinfo, sibling after `</main>`) |

## Placeholders in `dashboard.html`

Brand / chrome (from `brand.json`):

- `{{REPORT_TITLE}}`, `{{REPORT_SUBTITLE}}`
- `{{AGENCY_NAME}}`, `{{AGENCY_KICKER}}`, `{{AGENCY_LOGO}}`
- `{{TASKS_NOTE}}`, `{{DOWNLOADS_NOTE}}`, `{{FOOTER_TEXT}}`

Audit data (from the axe results):

- `{{AUDIT_URL}}`, `{{AUDIT_DATE}}`, `{{WCAG_TARGET}}`
- `{{SCORE_VALUE}}`, `{{SCORE_RATING}}`, `{{TOTAL_ISSUES}}`, `{{TASK_COUNT}}`
- `{{CRITICAL_COUNT}}`, `{{SERIOUS_COUNT}}`, `{{MODERATE_COUNT}}`, `{{MINOR_COUNT}}`

Server-rendered component fragments:

- `{{SEVERITY_BARS}}` — `dd-bar-chart` rows (`_render_severity_bars`)
- `{{PAGE_CARDS}}` — `dd-card` items (`_render_page_cards`)
- `{{TASK_ROWS}}` — `dd-data-table` rows with `dd-badge` (`_render_task_rows`)
- `{{DOWNLOAD_LINKS}}` — `dd-button` download links (`_render_download_links`)

## Accessibility contract

Baked into the builders (`accessibility-lead` reviewed): badge label text carries
the axe severity word (never color alone, 1.4.1); screenshot links have unique,
context-bearing names (2.4.4/2.5.3); card screenshots are decorative `alt=""` with
a self-describing "View screenshot of {url}" link; download labels state the real
format (Markdown/CSV/DOCX/JSON, 2.5.3); a `role="status"` live region announces
filter results; `prefers-reduced-motion` is honored.

Validate any rendered output with:

```bash
python3 ../../dd-framework/skills/dd-framework/scripts/dd_framework_helper.py validate index.html --human
```
