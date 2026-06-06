# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is **not an application** — it's a packaged agentic **Skill** (`skills/dd-site-compare/SKILL.md` is the entry manifest) loaded by Claude Code, Codex, or other agent IDEs to compare websites into a self-contained dashboard. There is no build system and no service to run. The "code" is two things:

1. **A standalone Python CLI** (`skills/dd-site-compare/scripts/compare_websites.py`) that fetches each homepage + linked resources and emits a 31-field JSON payload. Pure stdlib — **no external packages on the default path**.
2. **An HTML template** (`templates/dashboard.html`) the script injects the JSON into to produce a self-contained, dependency-free dashboard (sort / filter / export, dark mode).

When working in this repo, you are usually editing the skill's instructions, the CLI, the field contract, or the template — not running a comparison.

## Common commands

No package manager, no Makefile. The script is invoked directly with system Python 3.

```bash
cd skills/dd-site-compare

# Recommended — writes web/<primary-domain>-compare-audit-YYYY-MM-DD/{index.html,data.json}
python3 scripts/compare_websites.py --web https://www.example.com https://www.example.org

# Fast path (homepage only, skip subresources)
python3 scripts/compare_websites.py --web --skip-resources https://a.com https://b.com

# Explicit output paths (legacy, still supported)
python3 scripts/compare_websites.py -o reports/comparison.html --json-output reports/comparison.json https://a.com https://b.com

# All flags
python3 scripts/compare_websites.py --help

# Verification harness — run after ANY change to the script, template, or field contract
python3 scripts/verify.py
```

## Field contract

`skills/dd-site-compare/references/fields.md` is the source of truth: **every** field must be present in **every** row (failed fetches populate `error` and keep numeric defaults — never drop a row). Adding a field is a 9-step checklist documented at the bottom of `SKILL.md`; the short version: update `FIELD_ORDER` + the `SiteResult` dataclass + `analyze_site` (incl. the error early-return) + `references/fields.md` + the template display logic, then re-run `verify.py`.

## Layout notes

- `templates/dashboard.html` is resolved relative to the script via `parents[3]/templates` with fallbacks to a sibling `templates/` (so both the repo layout and a flattened Codex install work). Override with `--template`.
- `agents/openai.yaml` is interface metadata for agent registries — keep `default_prompt` in sync with the SKILL description if invocation language changes.
- `--web` placement is computed from `__file__`; when run as an installed plugin the conventional `web/` folder lands under the skill install dir, not the user's CWD. Pass explicit `-o` / `--json-output` if you need it elsewhere.
