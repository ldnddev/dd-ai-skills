# dd-seo — SEO Audit Skill

Deterministic, LLM-first SEO audits for websites, blog posts, and GitHub repositories. Bundles 30+ Python scripts for evidence collection (PageSpeed, robots, llms.txt, security headers, broken links, schema, redirects, social meta, internal links, GitHub repo audits, etc.) and a rubric-driven analysis pass for prioritized fixes.

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-seo@dd-skills
```

Python deps (`requests`, `beautifulsoup4`) are not auto-installed. Run once:

```bash
pip3 install --user requests beautifulsoup4
```

Optional (visual scripts):

```bash
pip3 install --user playwright && python3 -m playwright install chromium
```

## Install — Codex skill

`bash install.sh` from this directory — attempts `pip3 install --user requests beautifulsoup4`. See [root README](../../README.md#codex-install-legacy) for context.

## Trigger phrases

| Command | Sub-skill |
|---|---|
| `seo audit <url>` | full website audit + scoring |
| `seo page <url>` | single-page deep dive |
| `seo technical <url>` | crawl/index/security/CWV/JS rendering |
| `seo content <url>` | content quality + E-E-A-T |
| `seo schema <url>` | JSON-LD detect/validate/generate |
| `seo sitemap <url>` | sitemap analysis + generation |
| `seo images <url>` | image optimization audit |
| `seo geo <url>` | AI search optimization (GEO) |
| `seo aeo <url>` | answer engine optimization |
| `seo programmatic <url>` | programmatic SEO safeguards |
| `seo competitors <url>` | comparison/alternatives pages |
| `seo hreflang <url>` | international SEO |
| `seo plan <url>` | strategic SEO plan |
| `seo github <repo>` | GitHub repo discoverability |
| `seo article <url>` | article extraction + LLM optimization |
| `seo links <url>` | backlink/link health |
| `perform seo analysis on <url>` | generic → single-page full audit |

## Deliverables (full/page audits)

- `FULL-AUDIT-REPORT.md`
- `ACTION-PLAN.md`
- Optional client bundle via `generate_report.py` — written into `web/<domain>-seo-audit-<YYYY-MM-DD>/`:
  - `index.html` — branded interactive dashboard (driven by `templates/dashboard.html` + `templates/brand.json`)
  - `FULL-AUDIT-REPORT.docx` — findings + scoring narrative
  - `ACTION-PLAN.docx` — prioritized remediation tasks (P0/P1/P2 grouping)
  - `tasks.csv` — same tasks in CSV form (project-tracker-ready)
  - `assets/` — agency logo and other branded assets copied from `templates/assets/`
- GitHub repo audits via `github_seo_report.py` always emit four files:
  - `GITHUB-SEO-REPORT.md`
  - `GITHUB-ACTION-PLAN.md`
  - `GITHUB-REMEDIATION-TASKS.csv`
  - `GITHUB-CLIENT-REPORT.docx`

## Layout

```
dd-seo-audit/
├── .claude-plugin/plugin.json
├── install.sh
├── CLAUDE.md
└── skills/dd-seo/
    ├── SKILL.md
    ├── scripts/        (30+ Python audit scripts)
    └── resources/
        ├── skills/     (16 sub-skill workflow files)
        ├── agents/     (10 specialist agent definitions)
        ├── references/ (rubric, quality gates, schema types, CWV thresholds, E-E-A-T)
        ├── templates/  (industry templates: saas, local, ecommerce, publisher, agency, generic)
        └── schema/     (JSON-LD templates)
```

## Critical rules

- **INP not FID** (FID removed 2024-09-09)
- **JSON-LD only** for structured data
- **FAQPage schema restricted** (gov/healthcare only since 2023-08)
- **HowTo schema deprecated** (rich results removed 2023-09)
- **Mobile-first complete** (since 2024-07-05)
- **E-E-A-T applies to all competitive queries** (since 2025-12)
- AI crawler audit: GPTBot, ClaudeBot, PerplexityBot, Applebot-Extended, Google-Extended, Bytespider, CCBot

## Scoring weights (full audit)

| Category | Weight |
|---|---|
| Technical SEO | 25% |
| Content Quality | 20% |
| On-Page SEO | 15% |
| Schema | 15% |
| Performance (CWV) | 10% |
| Image Optimization | 10% |
| AI Search Readiness (GEO) | 5% |
