# dd-site-speed

Page speed and Core Web Vitals audit skill — Google PageSpeed Insights (mobile + desktop), technology stack detection, stack-aware recommendations, and client deliverables matching the rest of the dd-skills suite.

Inspired by [DeployHQ PageSpeed Analyzer](https://pagespeed.deployhq.com/): measure with PSI, explain *why* it’s slow, and ship actionable fixes.

## Features

- **Mobile + desktop** PSI by default (lab Lighthouse + field CrUX when available)
- **Stack detection** (WordPress, Next.js, Shopify, CDN/host signals, …)
- **Prioritized tasks** with estimated savings, owner, effort, and how-to
- **Client bundle**: branded `index.html` dashboard, MD + dual DOCX, `tasks.csv`, `data.json`
- **Multi-page**: multiple URLs or `--urls-file`
- **Optional API key** (`--api-key` or `PAGESPEED_API_KEY`) — free tier works without one
- **Zero pip deps** (Python 3 stdlib)

## Quick start

```bash
# From this plugin directory
python3 scripts/run_speed_audit.py https://example.com

# Multi-page
python3 scripts/run_speed_audit.py https://example.com https://example.com/pricing

# URL file
python3 scripts/run_speed_audit.py --urls-file urls.txt

# Optional key
export PAGESPEED_API_KEY="your-key"
python3 scripts/run_speed_audit.py https://example.com
```

Default output:

```
web/<domain>-speed-audit-YYYY-MM-DD/
├── index.html
├── SPEED-AUDIT-REPORT.md
├── ACTION-PLAN.md
├── SPEED-CLIENT-REPORT.docx
├── ACTION-PLAN.docx
├── tasks.csv
├── data.json
└── assets/
```

## Install

### Claude Code marketplace

```bash
/plugin marketplace add ldnddev/dd-ai-skills   # once
/plugin install dd-site-speed@dd-skills
```

### Codex

```bash
bash custom/dd-site-speed-audit/install.sh
# → ~/.codex/skills/dd-site-speed/
```

## Scripts

| Script | Role |
|--------|------|
| `scripts/run_speed_audit.py` | Orchestrator — PSI + stack + full report bundle |
| `scripts/pagespeed.py` | PSI client only |
| `scripts/detect_stack.py` | Tech stack heuristics |
| `scripts/generate_report.py` | MD / DOCX / CSV / HTML from audit JSON |

## Agent skill

Canonical skill body: [`skills/dd-site-speed/SKILL.md`](skills/dd-site-speed/SKILL.md)

References:

- `skills/dd-site-speed/references/cwv-thresholds.md`
- `skills/dd-site-speed/references/optimization-playbook.md`
- `skills/dd-site-speed/references/framework-tips.md`

## License

MIT
