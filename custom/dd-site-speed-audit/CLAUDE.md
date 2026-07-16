# CLAUDE.md — dd-site-speed

## Purpose

Client-ready **page speed / Core Web Vitals** audits. Google PageSpeed Insights (mobile + desktop), stack detection, prioritized recommendations, branded dashboard + downloadable task list.

## Layout

```
dd-site-speed-audit/
├── .claude-plugin/plugin.json
├── skills/dd-site-speed/SKILL.md
├── skills/dd-site-speed/references/
├── scripts/
│   ├── run_speed_audit.py      # main entry
│   ├── pagespeed.py
│   ├── detect_stack.py
│   └── generate_report.py
├── templates/
│   ├── dashboard.html
│   ├── brand.json
│   └── assets/
├── install.sh
└── README.md
```

## Orchestrator contract

```bash
python3 scripts/run_speed_audit.py <url> [urls...] [--urls-file f] [--api-key K]
```

Writes `web/<domain>-speed-audit-YYYY-MM-DD/` containing:

| Artifact | Required |
|----------|----------|
| `index.html` | yes |
| `SPEED-AUDIT-REPORT.md` | yes |
| `ACTION-PLAN.md` | yes |
| `SPEED-CLIENT-REPORT.docx` | yes |
| `ACTION-PLAN.docx` | yes |
| `tasks.csv` | yes |
| `data.json` | yes |
| `assets/` | yes |

## Rules

1. Always run the orchestrator for audit requests — do not invent PSI scores.
2. Default strategies: **mobile + desktop**.
3. API key optional (`PAGESPEED_API_KEY` / `PSI_API_KEY` / `--api-key`).
4. INP only — never FID.
5. On partial failures, still emit deliverables and list Environment Limitations.
6. Pure stdlib Python — no required pip packages.

## Boundaries

- **dd-site-speed** — deep performance + CWV + speed dashboard
- **dd-seo** — full SEO (may include a light CWV check)
- **dd-site-compare** — multi-site homepage metrics, not Lighthouse scoring
