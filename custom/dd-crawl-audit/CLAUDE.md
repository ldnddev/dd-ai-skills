# CLAUDE.md — dd-crawl

## Purpose

Full-site crawl: map URLs, check HTTP status, highlight broken + redirects + chrome-once links.

## Layout

```
dd-crawl-audit/
├── skills/dd-crawl/SKILL.md
├── scripts/run_crawl.py
├── scripts/crawl_core.py
├── scripts/generate_dashboard.py
└── templates/  # dashboard.html + brand.json
```

## Invariants

- Stdlib only
- Default delay 1.0s, max-pages 500
- robots.txt on unless `--robots-override`
- Exact host (+www) only
- Default output: `web/<domain>-crawl-YYYY-MM-DD/`
