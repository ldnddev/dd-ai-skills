# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is **not an application** — it's a packaged agentic **Skill** (`SKILL.md` is the entry manifest) loaded by Claude Code, Codex, or other agent IDEs to perform deterministic SEO audits. There is no build system, no test suite, no service to run. The "code" is two things:

1. **Markdown content** under `resources/` that the host LLM reads on demand to adopt sub-skill / agent personas.
2. **Standalone Python scripts** under `scripts/` invoked by the agent for evidence collection (HTML parse, PageSpeed, robots.txt, schema validation, GitHub API, etc.).

When working in this repo, you are usually editing the skill's instructions or the supporting scripts — not running an audit.

## Common commands

No package manager, no Makefile. Scripts are invoked directly.

```bash
# Install runtime deps for scripts
pip install requests beautifulsoup4
# Visual scripts (capture_screenshot.py, analyze_visual.py) additionally need:
pip install playwright && playwright install chromium

# Run any script standalone (all take --help)
python3 scripts/<name>.py --help

# Validate JSON-LD in a single HTML file
python3 scripts/validate_schema.py path/to/file.html

# Pre-commit lint (staged HTML files: schema placeholders, title length, alt text, deprecated FID/HowTo/FAQ)
bash scripts/pre_commit_seo_check.sh

# End-to-end audit dashboard (drives many other scripts internally)
python3 scripts/generate_report.py <url> --output SEO-REPORT.html
```

GitHub-repo scripts (`github_*.py`) require `GITHUB_TOKEN`/`GH_TOKEN` env var **or** an authenticated `gh` CLI; they accept `--provider auto|api|gh`.

## Architecture

The skill is a layered orchestration over Python scripts. Editing one layer in isolation often breaks the contract another layer depends on — read across before changing.

```
SKILL.md                       ← top-level orchestrator, routing table, critical rules
  ├── resources/skills/*.md    ← 16 sub-skills (one per `seo <verb>` command); each
  │                              describes its own evidence/script pipeline + outputs
  ├── resources/agents/*.md    ← 10 specialist personas the orchestrator delegates to
  │                              (technical, content, performance, schema, sitemap,
  │                              visual, verifier, github-*)
  ├── resources/references/*.md← rubrics & thresholds the LLM applies during analysis
  │                              (llm-audit-rubric, eeat-framework, cwv-thresholds,
  │                              quality-gates, schema-types, github-ranking-factors)
  ├── resources/templates/*.md ← per-industry strategic plan templates + report shells
  └── resources/schema/templates.json ← prebuilt JSON-LD blocks
scripts/*.py                   ← deterministic evidence collectors invoked by sub-skills
```

### Audit flow (what the orchestrator actually does)

`SKILL.md` § "Orchestration Logic" defines the canonical 8-step flow: identify task → collect evidence (`read_url_content` first, then scripts) → LLM analysis with `llm-audit-rubric.md` → run baseline verification scripts → delegate to specialist agent files → apply quality gates from `resources/references/` → run `scripts/finding_verifier.py` → score and write deliverables.

Mandatory artifacts for any full / page / generic audit are **`FULL-AUDIT-REPORT.md`** and **`ACTION-PLAN.md`** in CWD, created at audit start and updated as evidence arrives. Don't move these names — they are referenced from multiple sub-skill files and are the public contract.

### Script conventions

All scripts:
- Use Python 3.8+, single-file, no shared utility module **except** `scripts/github_api.py` (imported by every `github_*.py`).
- Accept `--json` for machine output (consumed by `generate_report.py` and `finding_verifier.py`).
- Fail open: network/DNS/rate-limit errors must be reported as environment limits, not site issues. The agent must keep going at confidence `Likely` instead of `Confirmed` (see SKILL.md Critical Rule #9).
- `fetch_page.py` enforces SSRF protection (rejects private/loopback IPs) — preserve this when editing.

### Score weights — single source of truth

Default audit category weights live in **two** places that must be kept in sync:
- `SKILL.md` § "Default Scoring Weights (Full Audit)"
- `resources/skills/seo-audit.md` § "Scoring Weights"

`scripts/generate_report.py` has its own internal weights for the HTML dashboard — these are intentionally separate (script-level, not narrative-level). Don't try to unify them.

## Editing rules specific to this skill

These are non-obvious invariants enforced across the content. Violating them produces wrong audits.

1. **Freshness comments** — every file in `resources/references/` carries `<!-- Updated: YYYY-MM-DD -->`. When editing a reference, bump the date. Anything older than 90 days is considered stale by the orchestrator.
2. **Critical Rules in SKILL.md are load-bearing** — the numbered list under "Critical Rules" (INP not FID, FAQ schema restricted to gov/health, HowTo deprecated, JSON-LD only, mobile-first complete, 30/50 location-page limits, AI crawler list, file-artifact requirement, bounded retries) is referenced by sub-skills and verified by `pre_commit_seo_check.sh`. Changing one means updating the lint script too.
3. **`<SKILL_DIR>` placeholder** — sub-skill docs reference scripts as `python3 <SKILL_DIR>/scripts/x.py`. Keep this convention so the skill works when installed at any path.
4. **Severity vocabulary** — only `Critical` / `Warning` / `Pass` / `Info` (with the 🔴 / ⚠️ / ✅ / ℹ️ glyphs). `finding_verifier.py` ranks on these exact strings; new severities will be silently dropped.
5. **Confidence labels** — `Confirmed` / `Likely` / `Hypothesis` are the only valid values per `llm-audit-rubric.md`. Used by both LLM output and `finding_verifier.py`.
6. **No third-party content mirrors** — never recommend `r.jina.ai` or similar as primary evidence (SKILL.md § Step 2). Direct fetch + bundled scripts only.

## Repo layout context

This repo is `custom/dd-seo-audit` inside the larger `dd-ai-skills` monorepo (sibling: `contrib/`). The repo's git root is `dd-ai-skills/`, but all code in this skill lives under this subdirectory. Commits should describe changes to the skill, not the parent project.
