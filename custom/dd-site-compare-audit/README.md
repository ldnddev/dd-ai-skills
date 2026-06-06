# dd-site-compare — Website Comparison Dashboard Skill

Compare 2+ websites into a **self-contained HTML + JSON dashboard**. One pure-stdlib Python CLI fetches each homepage (plus linked resources), extracts **31 quantitative + qualitative signals**, and injects them into a dependency-free dashboard with client-side sort, filter, export, and dark mode. Parallel by default (4 workers). No runtime dependencies — just system Python 3.

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-site-compare@dd-skills
```

No Python deps to install — the skill uses the standard library only.

## Install — Codex skill

`bash install.sh` from this directory — mirrors `skills/dd-site-compare/` into `${CODEX_HOME:-~/.codex}/skills/dd-site-compare`. See [root README](../../README.md) for context.

## Trigger phrases

| Say | Result |
|---|---|
| `compare websites <url> <url>` | full comparison dashboard |
| `competitive analysis` | multi-site dashboard |
| `site audit dashboard` | homepage metrics dashboard |
| `homepage comparison report` | dashboard + JSON |
| `/dd-site-compare` or `$dd-site-compare` | explicit invocation |

## Output

With `--web` (recommended), writes the conventional bundle:

```
web/<primary-domain>-compare-audit-YYYY-MM-DD/
├── index.html   # self-contained dashboard — open in any browser, no server
└── data.json    # raw 31-field results
```

## What it measures

URL / final URL / redirected, HTTP status, response time, page size, total load size, resource counts, largest item, trackers, title, meta description, heading (h1/h2/h3) counts, word count, image counts + images missing alt, internal/external link counts, detected technologies, dependency-free keyword phrases, favicon, canonical, JSON-LD count, mobile viewport, server / powered-by headers, and errors. Full contract: [`skills/dd-site-compare/references/fields.md`](skills/dd-site-compare/references/fields.md).

## Quick start (standalone)

```bash
cd skills/dd-site-compare
python3 scripts/compare_websites.py --web https://www.example.com https://www.example.org
python3 scripts/verify.py   # run after any change
```

All flags: `python3 scripts/compare_websites.py --help`.
