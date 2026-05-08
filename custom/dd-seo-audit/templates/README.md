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

Severity vocabulary is locked to **Critical / Warning / Pass / Info** (matches `resources/references/llm-audit-rubric.md` and `scripts/finding_verifier.py`). The dashboard renders the severity word in the cell text **and** as a `data-severity` attribute, so colorblind users get a textual cue.

### Repeating slots (HTML strings injected by the script)

| Placeholder | Producer |
|---|---|
| `{{CATEGORY_CARDS}}` | one `<div class="category-card">` per category, each with a ring + numeric score |
| `{{DOWNLOAD_LINKS}}` | one `<a class="download-link">` per output artifact (DOCX / CSV / MD) |
| `{{TASK_ROWS}}` | one `<tr>` per task; severity cell uses `<span class="priority-pill" data-severity="...">` |
| `{{DETAILED_SECTIONS}}` | one `<details class="section-detail">` per analyzer (security, social, robots, broken_links, …) |

### Brand color and font tokens (from `brand.json`)

These are dropped directly into CSS custom properties. **Keep contrast ≥ 4.5:1 for text and ≥ 3:1 for non-text UI** — the dashboard relies on `brand.json` defaults to meet WCAG 2.2 AA. If you override colors per client, re-check the four severity pills and the title/body copy against the new background.

```
DISPLAY_FONT       BODY_FONT          UI_FONT
BRAND_BG           BRAND_BG_TOP       BRAND_SURFACE
BRAND_TEXT         BRAND_MUTED        BRAND_ACCENT       BRAND_ACCENT_2
BRAND_LINE         BRAND_SHADOW
BRAND_GLOW_1       BRAND_GLOW_2
HERO_BG_1          HERO_BG_2
TABLE_HEAD_BG
PRIORITY_BG        PRIORITY_TEXT      ← used for the chip on download cards
```

The four severity colors (`critical`, `warning`, `pass`, `info`) are **fixed in the CSS** of `dashboard.html`. They don't come from `brand.json` because their meaning must stay stable across client palettes and the WCAG-AA contrast values were tuned to that palette.

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
