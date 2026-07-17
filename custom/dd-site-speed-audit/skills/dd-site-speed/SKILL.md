---
name: dd-site-speed
description: >
  Page speed and Core Web Vitals audits powered by Google PageSpeed Insights
  (mobile + desktop lab and field data), stack-aware optimization
  recommendations, and client deliverables (branded HTML dashboard, Markdown
  report, action plan, dual DOCX, downloadable tasks.csv). Use when the user
  asks to run a page speed test, PageSpeed/Lighthouse audit, Core Web Vitals
  report, performance audit, "make the site faster", speed recommendations, or
  invokes /dd-site-speed. Supports single URL, multiple URLs, and --urls-file.
---

# dd-site-speed — Page Speed & Core Web Vitals Audit

Run performance audits like DeployHQ PageSpeed: measure with Google PSI, explain
results, and produce stack-aware recommendations plus a client report bundle.

## Trigger phrases

- `page speed audit <url>`
- `pagespeed <url>` / `lighthouse audit <url>`
- `core web vitals report <url>`
- `make this site faster`
- `speed recommendations for <url>`
- `/dd-site-speed`
- multi-page: paste several URLs or provide a URL list file

## Workflow

1. Read references:
   - `${CLAUDE_PLUGIN_ROOT}/skills/dd-site-speed/references/cwv-thresholds.md`
   - `${CLAUDE_PLUGIN_ROOT}/skills/dd-site-speed/references/optimization-playbook.md`
   - `${CLAUDE_PLUGIN_ROOT}/skills/dd-site-speed/references/framework-tips.md`
2. Collect target URL(s) from the user (or a file). Normalize missing schemes to `https://`.
3. Run the pipeline (default: **mobile + desktop**):

```bash
# Single URL → web/<domain>-speed-audit-YYYY-MM-DD/
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_speed_audit.py https://example.com

# Multiple URLs
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_speed_audit.py \
  https://example.com https://example.com/pricing

# URL list file
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_speed_audit.py --urls-file ./urls.txt

# Optional API key (also PAGESPEED_API_KEY / PSI_API_KEY env)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_speed_audit.py https://example.com \
  --api-key "$PAGESPEED_API_KEY"

# Custom output directory
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_speed_audit.py https://example.com \
  --output-dir reports/acme-speed/
```

Standalone helpers (evidence / debugging):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/pagespeed.py https://example.com --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/detect_stack.py https://example.com --json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate_report.py --input data.json --output-dir ./out
```

4. After scripts finish, **enrich recommendations with LLM analysis**:
   - Map top opportunities to the detected stack (WordPress, Next.js, Shopify, etc.).
   - Prefer highest estimated savings and P0/P1 tasks.
   - Keep INP (never FID). Cite metric values and PSI opportunity titles as evidence.
   - If the site is CMS/framework-specific, add concrete implementation steps from `framework-tips.md`.

5. Report every artifact path to the user and summarize the top 3–5 wins.

## Deliverables (`web/<domain>-speed-audit-YYYY-MM-DD/`)

| File | Purpose |
|------|---------|
| `index.html` | Branded dashboard (scores, CWV, tasks with expandable What/Why/How insights, CSV download button) |
| `SPEED-AUDIT-REPORT.md` | Full findings narrative |
| `ACTION-PLAN.md` | Prioritized remediation plan (What / Why / How per task) |
| `SPEED-CLIENT-REPORT.docx` | Client-facing report |
| `ACTION-PLAN.docx` | Client-facing action plan |
| `tasks.csv` | Tracker-ready task list with what, why, how columns (downloadable) |
| `data.json` | Raw audit JSON (PSI + stack) |
| `assets/` | Framework CSS/JS + branding |

## Defaults & options

| Option | Default | Notes |
|--------|---------|-------|
| Strategies | mobile + desktop | `--strategy mobile` or `desktop` to narrow |
| API key | optional | Free tier works without key; rate-limited |
| Max URLs | 25 | `--max-urls N` |
| Output | `web/<domain>-speed-audit-<date>/` | Override with `--output-dir` |
| Stack detect | on | `--skip-stack` to disable |

## Rules for agents

1. **Always run `run_speed_audit.py`** for audit requests — do not hand-wave scores without PSI data.
2. **Always produce the full client bundle** (dashboard + both MD + both DOCX + CSV + data.json).
3. On PSI rate limits or network failures: retry once if the script already did not; document **Environment Limitations**; still emit partial deliverables when any page succeeded.
4. Never claim field CrUX data when `field_data_available` is false.
5. Never recommend FID; interactivity metric is **INP** only.
6. Do not invent savings numbers — use PSI `savings_ms` / metric values from JSON.
7. For multi-page audits, call out the worst-scoring page and shared systemic issues (e.g. render-blocking sitewide).

## Notes

- Pure Python 3 stdlib (urllib) — no `pip install` required for the default path.
- Optional env: `PAGESPEED_API_KEY` or `PSI_API_KEY` for higher Google API quotas.
- This skill owns **performance depth**. Full SEO remains `dd-seo`; multi-site homepage compare remains `dd-site-compare`.
