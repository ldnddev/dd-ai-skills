---
name: seo-audit
description: >
  Full website SEO audit with parallel subagent delegation. Page-level scripts
  plus specialists, health score. Use when user says "seo audit", "full SEO
  check", or "analyze my site's SEO". Whole-site URL/404 maps are dd-crawl;
  speed/CWV audits are dd-site-speed.
---

# Full Website SEO Audit

Apply `resources/references/llm-audit-rubric.md` for evidence standards, confidence labels, severity mapping, and report structure.

## Process

1. **Read page with LLM** — use `read_url_content` to read the page and begin analysis using SEO best practices.
2. **Detect business type** — analyze homepage signals per seo orchestrator
3. **Run scripts for evidence** — Always attempt to run relevant scripts for structured data collection. Scripts provide precise, machine-readable evidence that strengthens the analysis:
   - `seo-technical` — robots.txt, sitemaps, canonicals, security headers
   - `seo-content` — E-E-A-T, readability, thin content, AI citation readiness
   - `seo-schema` — detection, validation, generation recommendations
   - `seo-sitemap` — structure analysis, quality gates, missing pages
   - `seo-visual` — screenshots, mobile testing, above-fold analysis
   - If the user supplies a Google Search Console export (`.zip`/`.csv`), pass it via
     `generate_report.py --gsc <path>` to enrich findings with real query/click data.
4. **LLM analysis** — Apply `llm-audit-rubric.md`, score each category using chain-of-thought. Combine LLM reasoning with script evidence. If a script failed, the LLM still covers that area using its own analysis (confidence: `Likely` instead of `Confirmed`).
5. **Score** — aggregate into SEO Health Score (0-100)
6. **Report** — generate prioritized action plan
7. **Generate client bundle (mandatory)** — run `python3 <SKILL_DIR>/scripts/generate_report.py <url>`. Produces `web/<domain>-seo-audit-<YYYY-MM-DD>/` containing `index.html`, `FULL-AUDIT-REPORT.docx`, `ACTION-PLAN.docx`, `tasks.csv`. Required default for every audit — only skip on environment failure (note as `Environment Limitation`).

## Page sample (not a site crawl)

This audit is the requested URL plus page-level scripts:

- `broken_links.py` — links on this page
- `internal_links.py` — default `--depth 1 --max-pages 20` (anchor text / shallow orphans)

For a whole-site URL inventory, 404s, and redirects, run **dd-crawl**.

## Output Files

All outputs below are **required by default** — `generate_report.py` is mandatory, not optional.

- `FULL-AUDIT-REPORT.md` — Comprehensive findings
- `ACTION-PLAN.md` — Prioritized recommendations (Critical → High → Medium → Low)
- `web/<domain>-seo-audit-<YYYY-MM-DD>/` — Client bundle (always produced via `generate_report.py`). Contents:
  - `index.html` — Branded interactive dashboard (rendered from `templates/dashboard.html` + `templates/brand.json`); links webroot `/assets/`
  - `FULL-AUDIT-REPORT.docx` — Findings + scoring narrative
  - `ACTION-PLAN.docx` — Prioritized remediation tasks (P0/P1/P2 grouping)
  - `tasks.csv` — Same tasks in CSV form (project-tracker-ready)
- `screenshots/` — Desktop + mobile captures (if Playwright available)

## Scoring Weights

> **Source of truth**: `SKILL.md` Step 7. Update weights there first, then mirror here.

| Category | Weight |
|----------|--------|
| Technical SEO | 30% |
| Content Quality | 20% |
| On-Page SEO | 15% |
| Schema / Structured Data | 15% |
| Images | 15% |
| AI Search Readiness | 5% |

## Report Structure

### Executive Summary
- Overall SEO Health Score (0-100)
- Business type detected
- Top 5 critical issues
- Top 5 quick wins

### Technical SEO
- Crawlability issues
- Indexability problems
- Security concerns

### Content Quality
- E-E-A-T assessment
- Thin content pages
- Duplicate content issues
- Readability scores

### On-Page SEO
- Title tag issues
- Meta description problems
- Heading structure
- Internal linking gaps

### Schema & Structured Data
- Current implementation
- Validation errors
- Missing opportunities

### Images
- Missing alt text
- Oversized images
- Format recommendations

### AI Search Readiness
- Citability score
- Structural improvements
- Authority signals

## Priority Definitions

- **Critical**: Blocks indexing or causes penalties (fix immediately)
- **High**: Significantly impacts rankings (fix within 1 week)
- **Medium**: Optimization opportunity (fix within 1 month)
- **Low**: Nice to have (backlog)
