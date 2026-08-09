---
name: dd-crawl
description: >
  Use when the user wants to crawl or map a website, inventory all URLs, find
  broken links / 404s, check redirects, scan header/footer/nav once, or produce
  a site link report. Triggers: crawl site, link check, find 404s, site map URLs,
  broken links full site, /dd-crawl.
---

# dd-crawl — Whole-site URL scanner + link checker

Crawls internal pages from a start URL, records HTTP status for every discovered
URL (pages, assets, external, mailto/tel), and writes a **Framework dashboard**
bundle under `web/<domain>-crawl-YYYY-MM-DD/` by default.

## Behavior contract

1. **Excluded** (`--exclude-tag` / `--exclude-id`): removed before link extraction — not scanned, not crawled through.
2. **Chrome** (default `header`, `footer`, `nav`): links collected **once** into a chrome table; still followed if internal pages; stripped from per-page noise.
3. **External**: listed + status-checked by default; never crawled.
4. **Host**: exact host (+ `www.` equivalence only).
5. **Query strings**: distinct URLs; fragments ignored.
6. **robots.txt**: respected by default; `--robots-override` to ignore Disallow.
7. **No JS execution** — SPA-only routes may be missing.

## Workflow

### 1. Confirm inputs

- Start URL (scheme optional; `https://` added if missing)
- Excludes vs chrome (default chrome once; exclude = skip entirely)
- Large sites: mention defaults `--max-pages 500`, `--delay 1.0`, optional `--depth`

### 2. Run (default web bundle)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_crawl.py https://example.com

# Polite large crawl
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_crawl.py https://example.com \
  --delay 1.5 --max-pages 500 --depth 5

# Exclude footer; custom chrome
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_crawl.py https://example.com \
  --exclude-tag footer --chrome-tag header --chrome-tag nav

# Staging with basic auth + ignore robots
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_crawl.py https://staging.example.com \
  --auth 'user:pass' --robots-override

# Write to a folder without web/ naming
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_crawl.py https://example.com --no-web --output-dir ./out
```

### 3. Deliverables (`web/<domain>-crawl-YYYY-MM-DD/`)

| File | Purpose |
|------|---------|
| `index.html` | Framework dashboard: stats, broken, redirects, all URLs, chrome, downloads |
| `data.json` | Full machine-readable result |
| `all-urls.csv` | Every URL (page + chrome) |
| `broken.csv` | Broken only |
| `assets/` | Framework CSS/JS |

### 4. Report to user

- Path to **dashboard**
- Headline: pages crawled, total URLs, **broken**, redirects
- Call out 404s / ERROR worth fixing
- Note SPA limitation if the site is JS-heavy
- Note if max-pages or robots blocked URLs

## Options

| Flag | Default | Purpose |
|------|---------|---------|
| `--max-pages` | 500 | Cap on pages fetched as HTML |
| `--depth` | unlimited | Max BFS depth from start (0 = start only) |
| `--delay` | **1.0** s | Pause between page fetches |
| `--timeout` | 15 | Per-request timeout |
| `--exclude-tag` / `--exclude-id` | — | Remove before scan |
| `--chrome-tag` | header, footer, nav | Once-scanned chrome |
| `--no-check-external` | off | List externals without HEAD/GET |
| `--robots-override` | off | Ignore robots.txt |
| `--user` / `--password` / `--auth` | — | HTTP basic auth |
| `--web` | **on** | `web/<domain>-crawl-<date>/` |
| `--no-web` | — | Use `--output-dir` instead |
| `--output-dir` | `.` with `--no-web` | Output directory |

## Related

- Single-page broken links in **dd-seo** remain separate; use this skill for **full-site** inventory + status.

## Notes

- Pure **Python 3 stdlib** (urllib + html.parser) — no pip install.
- Only crawl sites the user owns or has permission to scan.
