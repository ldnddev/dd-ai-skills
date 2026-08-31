# CLAUDE.md — dd-audit

## Purpose

Orchestrate a primary-URL site audit by **invoking** dd-crawl, dd-seo, and dd-site-speed into nested folders, then write a cover dashboard. Requires dd-site-compare installed too (not run in v1).

## Layout

```
dd-audit/
├── skills/dd-audit/SKILL.md
├── scripts/run_audit.py      # preflight / init / assemble
├── scripts/discover.py
├── scripts/assemble.py
└── templates/                # cover dashboard only
```

## Invariants

- Do not inline child skills
- Do not rewrite child HTML
- Preflight all four plugins or stop
- v1 run: crawl + seo + speed; continue on child error
- Default output: `web/<domain>-site-audit-YYYY-MM-DD/`
