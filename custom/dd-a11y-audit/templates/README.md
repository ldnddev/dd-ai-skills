# Dashboard Template Notes

These files are not wired into the report generator yet. They are the staging area for your branded HTML dashboard.

Files:

- `dashboard.html`
- `brand.json`

Recommended workflow:

1. Edit `dashboard.html` until the structure and CSS match your agency style.
2. Edit `brand.json` for logo path, agency name, footer copy, fonts, and color values.
3. When the design is final, wire these placeholders into `scripts/generate_a11y_report.py`.

Primary placeholders in `dashboard.html`:

- `{{AGENCY_NAME}}`
- `{{AGENCY_LOGO}}`
- `{{REPORT_TITLE}}`
- `{{REPORT_SUBTITLE}}`
- `{{AUDIT_URL}}`
- `{{AUDIT_DATE}}`
- `{{SCORE_VALUE}}`
- `{{SCORE_RATING}}`
- `{{CRITICAL_COUNT}}`
- `{{SERIOUS_COUNT}}`
- `{{MODERATE_COUNT}}`
- `{{MINOR_COUNT}}`
- `{{DOWNLOAD_LINKS}}`
- `{{TASK_ROWS}}`

Brand/style placeholders:

- `{{DISPLAY_FONT}}`
- `{{BODY_FONT}}`
- `{{UI_FONT}}`
- `{{BRAND_BG}}`
- `{{BRAND_BG_TOP}}`
- `{{BRAND_SURFACE}}`
- `{{BRAND_TEXT}}`
- `{{BRAND_MUTED}}`
- `{{BRAND_ACCENT}}`
- `{{BRAND_ACCENT_2}}`
- `{{BRAND_LINE}}`
- `{{BRAND_SHADOW}}`
- `{{BRAND_GLOW_1}}`
- `{{BRAND_GLOW_2}}`
- `{{HERO_BG_1}}`
- `{{HERO_BG_2}}`
- `{{TABLE_HEAD_BG}}`
- `{{PRIORITY_BG}}`
- `{{PRIORITY_TEXT}}`

Keep assets relative to the generated audit folder or define a copy step when you are ready to integrate the template into the skill.
