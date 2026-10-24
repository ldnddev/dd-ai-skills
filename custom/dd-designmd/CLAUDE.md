# CLAUDE.md — dd-designmd

## Purpose

Reverse-engineer a **semantic design system** from live URLs into `{domain}-design.md` + token files.

## Layout

```
dd-designmd/
├── skills/dd-designmd/SKILL.md
├── skills/dd-designmd/references/
├── scripts/run_designmd.py      # orchestrator
├── scripts/generate_dashboard.py
└── templates/                   # dashboard.html + brand.json
```

`--web` writes `web/<domain>-designmd-YYYY-MM-DD/index.html` + deliverables. Dashboard CSS/JS/logos come from webroot `/assets/`.

## Invariants

- Domain naming: lowercase, strip `www.`
- Refuse overwrite without `--force`
- Tokens must carry evidence strings
- Always include Framework mapping and Agent instructions sections
- Never invent brand or rebrand advice

## Test fixture

`https://www.ldnddev.com` → `ldnddev.com-design.md`
