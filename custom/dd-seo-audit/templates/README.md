# Dashboard Template

Client-facing HTML dashboard, brand tokens, and shared assets for the dd-seo audit. Wired into `scripts/generate_report.py` — editing these files changes every audit dashboard the script emits.

## Files

```
templates/
├── dashboard.html   # Outer chrome of the report (HTML + CSS, no JS)
├── brand.json       # Brand colors, fonts, agency lockup, copy
└── assets/
    └── agency-logo.svg
```

## Output bundle

When the user runs `generate_report.py <url>`, the script writes:

```
web/<domain>-seo-audit-<YYYY-MM-DD>/
├── index.html               # populated dashboard.html
├── FULL-AUDIT-REPORT.docx   # findings + scoring narrative
├── ACTION-PLAN.docx         # prioritized remediation tasks
├── tasks.csv                # the same tasks in CSV form
└── assets/
    └── agency-logo.svg      # copied from templates/assets/
```

The `web/<domain>-seo-audit-<date>/` folder name is the public contract — sub-skill files and README references rely on it.

## Placeholders in dashboard.html

### Brand and chrome

| Placeholder | Source | Notes |
|---|---|---|
| `{{AGENCY_NAME}}` | `brand.json:agency_name` | alt text + plain text |
| `{{AGENCY_KICKER}}` | `brand.json:agency_kicker` | small caps line above the title |
| `{{AGENCY_LOGO}}` | `brand.json:agency_logo` | path is relative to `index.html` (script copies the file into `assets/`) |
| `{{REPORT_TITLE}}` | `brand.json:report_title` | `<h1>` |
| `{{REPORT_SUBTITLE}}` | `brand.json:report_subtitle` | hero paragraph + `<meta name="description">` |
| `{{DOWNLOADS_NOTE}}` | `brand.json:downloads_note` | copy above the download grid |
| `{{TASKS_NOTE}}` | `brand.json:tasks_note` | copy above the task table |
| `{{FOOTER_TEXT}}` | `brand.json:footer_text` | bottom paragraph |

### Audit data

| Placeholder | Source | Notes |
|---|---|---|
| `{{AUDIT_URL}}` | `data["url"]` | rendered as link |
| `{{AUDIT_DOMAIN}}` | `data["domain"]` | hostname only |
| `{{AUDIT_DATE}}` | local date (`YYYY-MM-DD`) | also drives the output folder name |
| `{{ENV_PLATFORM}}` | `data["environment"]["primary"]` | detected CMS / framework |
| `{{SCORE_VALUE}}` | `scores["overall"]` | 0–100 integer |
| `{{SCORE_RATING}}` | derived from `{{SCORE_VALUE}}` | "Excellent / Good / Needs Improvement / Poor / Critical" |

### Severity counts

| Placeholder | Source |
|---|---|
| `{{CRITICAL_COUNT}}` | tasks where priority == "Critical" |
| `{{WARNING_COUNT}}` | tasks where priority == "Warning" |
| `{{INFO_COUNT}}` | tasks where priority == "Info" |
| `{{PASS_COUNT}}` | finding rows where severity == "Pass" |

Severity vocabulary is locked to **Critical / Warning / Pass / Info** (matches `resources/references/llm-audit-rubric.md` and `scripts/finding_verifier.py`). The dashboard renders the severity word as the **`dd-badge` label text** (e.g. `-critical` → "Critical"), so meaning is carried by text, not color alone (WCAG 1.4.1).

### Repeating slots (HTML strings injected by the script)

The dashboard is built from **ldnddev Framework components** (see `custom/dd-framework`). Each producer emits framework markup:

| Placeholder | Producer (`generate_report.py`) |
|---|---|
| `{{CATEGORY_CARDS}}` | one `dd-score-ring -link` card per category (grid item), arc tone by score |
| `{{BAR_CHART_ROWS}}` | one `dd-bar-chart__row` per category (label + value text + decorative bar) |
| `{{DOWNLOAD_LINKS}}` | one `<a class="dd-button -secondary" download>` per output artifact (DOCX / CSV / MD) |
| `{{TASK_ROWS}}` | one `dd-data-table__row` per task; severity cell embeds a `dd-badge` |
| `{{DETAILED_SECTIONS}}` | one `dd-accordion__item` (`<details>`) per analyzer, each body using `dd-finding` lists and plain status tables |

### Styling — framework-driven

The template links the framework build and lets it theme everything:

```
<link rel="stylesheet" href="assets/css/style.min.css">
<script src="assets/js/main.min.js" defer></script>
```

Drop `style.min.css` + `main.min.js` (from `framework.ldnddev.com`) into the report bundle's `assets/`. The framework provides all component styling, the 24-col `dd-g` grid, dark mode (via `prefers-color-scheme`), and `dd-data-table` sort + scroll-region accessibility. **There is no manual theme toggle** — the framework themes by system preference only.

Severity colors, focus rings, and control-border contrast (WCAG 1.4.11 / 2.4.13) all live in the framework stylesheet — verify AA there, not here. The template keeps only a small inline `<style>` for the few shell bits the framework has no component for (skip link, summary `<dl>`, sticky rail, status tables inside accordions). The old `brand.json` color/font tokens (`BRAND_BG`, `DISPLAY_FONT`, `PRIORITY_BG`, …) are **no longer consumed** by the template; theming is the framework's job.

## Editing workflow

1. Adjust `dashboard.html` for layout / structure / WCAG compliance.
2. Adjust `brand.json` for per-agency copy and color tokens.
3. Drop the agency mark into `templates/assets/agency-logo.svg` (or update `brand.json:agency_logo` to a new filename — anything in `templates/assets/` is copied into the audit bundle).
4. Smoke-test:
   ```bash
   python3 ../skills/dd-seo/scripts/generate_report.py https://example.com
   open "web/example.com-seo-audit-$(date +%F)/index.html"
   ```

## Accessibility commitments

- One `<main>` landmark + skip link to it.
- Single `<h1>` (`{{REPORT_TITLE}}`); each `<section class="panel">` is `aria-labelledby` its own `<h2>`.
- All interactive controls (`<a>`, `<summary>`) are keyboard-reachable and show a visible `:focus-visible` outline.
- Severity is conveyed through both color and text content — color is never the sole signal.
- `prefers-reduced-motion` disables the hover translate on download cards.
- Print stylesheet expands all `<details>` so the printed PDF has every finding visible.
- Target contrast: AA (4.5:1 text, 3:1 UI). When forking `brand.json` for a new client, re-verify the severity pills against the new background and the body copy against `--bg`.
