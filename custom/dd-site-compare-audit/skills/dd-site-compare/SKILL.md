---
name: dd-site-compare
description: >
  Generate HTML dashboards that compare multiple websites by URL, HTTP status,
  response time, page size, total load size, resource counts, largest item, trackers, title,
  meta description, heading/image/link counts, detected technologies, dependency-free keyword
  phrases, mobile viewport support, server headers, homepage positioning (headline, subhead,
  nav, CTAs), conversion signals (forms, offer type, pricing visibility, trust), nav page-type
  presence, and errors. Supports parallelism and 42 quantitative + qualitative signals.
  When --web is used, automatically writes the HTML (as index.html) + JSON into
  web/<primary-domain>-compare-audit-YYYY-MM-DD/ at the project root.
  Use when the user pastes 1+ URLs (or a file), asks to "compare websites", "competitive analysis",
  "compare this to competitors", "homepage comparison report", or invokes
  /dd-site-compare or $dd-site-compare. One URL triggers peer discovery before the dashboard.
version: 1.4.2
when-to-use: "Use for website comparisons, competitive audits, multi-site homepage metric dashboards. Trigger phrases: compare sites, site comparison, competitive analysis, compare this to competitors, homepage comparison report, dashboard for these URLs."
argument-hint: "[urls...] [--web] [--urls-file file.txt] [--skip-resources] [--max-resources N] [--workers 4] [--json-output out.json] [-o out.html]"
---

# DD Site Compare

**v1.1 adds 12 new strictly-required fields** (final_url, redirected, word_count, h2/h3 counts, images_missing_alt, external_link_count, has_favicon, has_canonical, json_ld_count, server, powered_by), parallel fetching (default 4 workers), client-side sort/filter/export in the dashboard, richer field docs, dark mode, a `scripts/verify.py` harness, and the `--web` flag for automatic `web/<domain>-compare-audit-YYYY-MM-DD/` placement. All prior CLI flags and output shape remain compatible; new fields are always present.

**v1.3 adds 11 homepage competitive signals** (positioning, conversion, nav page-types) from the same parse — no extra network. Names, types, and computation: `references/fields.md`.

**v1.4** marks the first CLI URL as the **primary** site (`primary_url` on the dashboard payload) and adds discovery intake when the user gives one site or unnamed competitors.

**v1.4.1** documents skill ownership (Related) and drops generic “website audit” triggers.

## Workflow

1. Collect URLs from the prompt, a pasted list, or a text file. **The first URL is the primary site** (your client / the site under review). Remaining URLs are peers.
2. If there is only one URL, or the user asked to compare against competitors without naming them, run **Discovery intake** below and **wait** for confirmation (or an explicit skip) before step 3.
3. Run `scripts/compare_websites.py` with the **primary URL first**, then confirmed peers, preferably with `--web`:
   `web/<first-domain>-compare-audit-YYYY-MM-DD/`
   (e.g. `web/example.com-compare-audit-2025-06-02/index.html`).
4. Confirm `data.json` includes `primary_url` (matching the first URL) and **every field** in `references/fields.md` for every row.
5. Report the generated HTML (and JSON) path(s). Note failed or redirected URLs. The dashboard links webroot `/assets/` for framework CSS/JS.
6. Read `data.json` and add a short **gap note** framed as **primary vs peers** (a few bullets, not a narrative report): sharpest/most specific promise (`h1_text` + `hero_subhead`); offer friction (`offer_type`, `form_field_count`, `pricing_visible`); missing `page_types` vs the set; stronger `trust_signals`. Tone and “lead-with” (features vs outcomes vs price vs brand) are judgment over those extracted strings — do not invent metrics the script did not emit.

## Discovery intake

Use this when the compare set is incomplete. **Do not** pick peers inside the Python CLI, call paid traffic/SEO APIs, or run the dashboard until the set is confirmed.

1. Keep the given URL as primary (it stays first on the CLI).
2. Propose **4–8** candidates as a table: URL · Kind · Why (one line) · Source.
   - **Direct** — same offer and buyer
   - **Adjacent** — same category, different wedge
   - **SERP/content** — competes for keywords; may not sell the same thing
3. Sources, in order: primary homepage (`/alternatives`, `/compare`, vs pages, “unlike …”, peer logos, G2/Capterra category); web search (`[category] alternatives`, `best [category]`, `[name] vs`); model knowledge only as a hypothesis, labeled that way.
4. Recommend **primary + 2–4 Direct** (then Adjacent). List the rest as optional, not in this run. If Direct and SERP/content are both included, keep Kind in the gap note.
5. If the user skips discovery or says “just this URL”, run primary-only.

## Quick Start

**Recommended for this project** (places output in the conventional web folder):

```bash
python3 scripts/compare_websites.py \
  --web \
  https://www.example.com https://www.example.org
```

This creates (for example):

```
web/example.com-compare-audit-2025-06-02/
├── index.html   # the dashboard (ldnddev Framework; links webroot /assets/)
└── data.json    # raw results
```

With file + control:

```bash
python3 scripts/compare_websites.py \
  --web \
  --urls-file urls.txt \
  --workers 4 \
  --max-resources 100
```

Legacy / explicit path (still supported):

```bash
python3 scripts/compare_websites.py \
  --output reports/comparison.html \
  --json-output reports/comparison.json \
  https://www.example.com https://www.example.org
```

Faster homepage-only:

```bash
python3 scripts/compare_websites.py --web --skip-resources https://a.com https://b.com
```

Run the verification harness (recommended after changes or before delivering an audit):

```bash
python3 scripts/verify.py
```

## Script Behavior

- Pure Python stdlib only (`urllib`, `html.parser`, `concurrent.futures`, `dataclasses`, etc.). Never pull in external packages for the default path.
- **Parallel by default**: analyzes up to `--workers 4` sites concurrently. Use `--workers 1` to force the old serial behavior.
- Homepage + direct linked resources (img, css, script, source) up to `--max-resources`. `total_page_load_size` and `largest_item` aggregate across them.
- Keyword extraction (15 phrases) is deterministic, dependency-free, and scores title (high), meta description, headings, and paragraph text from the *same* fetched pages used for all other metrics.
- Redirects are followed for fetching but the user-supplied URL is always kept as the "URL" column. `final_url` and `redirected` now expose the difference.
- Failed fetches still produce a full row (with `error` populated and numeric fields defaulted safely). Never drop rows.
- The HTML dashboard lives in the sibling `../../templates/dashboard.html`. Edit the template for visual/layout changes; the Python only supplies the JSON payload.
- `--skip-resources` is the fast path for many URLs or when subresource fetching is blocked/slow.
- `--web` (recommended): automatically computes `<primary-domain>-compare-audit-YYYY-MM-DD` from the first URL + today's date (UTC) and writes `index.html` + `data.json` into `web/<folder>/` relative to the project root. The parent `web/` directory is created if needed. Explicit `--output` or `--json-output` basenames are respected inside that folder.
- **Primary site:** the first input URL. The JSON payload includes `primary_url` (same value). The dashboard labels that column/row “Primary”.

## Required Fields (Contract)

**Load `references/fields.md` before emitting or auditing output.** The script and dashboard **must** include every field for every row. The contract is additive and strictly enforced.

See the expanded reference for types, computation notes, and "lower/higher is better" guidance.

Legacy note: older notebook `script.py` / `keywords.py` were the source of the original implementation. Always use the CLI in `scripts/compare_websites.py`.

## Notes For Agents

- Keep user-provided URLs in the report (even on redirect). Populate `final_url` + `redirected`.
- Always emit a row for every input URL; use the `error` field instead of omitting.
- When the user says "like the old demo" or "Markdown table", still produce (and point to) the **HTML dashboard** + optional JSON. Never hand-craft a static MD transcript.
- After edits to the script or template, run `python3 scripts/verify.py` and paste a summary of its output.
- The `agents/openai.yaml` provides the interface metadata for agent registries; keep `default_prompt` in sync with the description above if you change invocation language.

## Extending the Dashboard (for future changes)

1. Add the new field name to `FIELD_ORDER` (scripts/compare_websites.py) in a logical position.
2. Add the attribute + default to the `SiteResult` dataclass.
3. Populate it in `analyze_site` (and the error early-return path).
4. (If parser-driven) extend `ParsedHTML` or the post-parse logic.
5. Update `to_output_row()` if the shape differs (e.g. object vs primitive).
6. Update `references/fields.md` (both the bullet list and the detailed table).
7. Add tasteful display logic in dashboard.html (formatDisplayValue, appendDisplayCell, pills, best-value highlighting, chartDefinitions if numeric + useful).
8. Re-run `python3 scripts/verify.py` and a manual 3-URL test; confirm both tables, sort, filter, and exports work.
9. Update this SKILL.md "Required Fields" list + the v1.x note if the contract grew.

This discipline keeps the field contract and the zero-dep contract intact.

## Related

This skill owns **multi-site homepage competitive comparison** (positioning, conversion, cheap tech/size columns). Title/canonical/alts here are comparison columns, not an SEO audit.

- **dd-seo** — SEO audit; `seo competitors` *writes* vs/alternatives pages
- **dd-site-speed** — PageSpeed / CWV depth (not these size/TTFB columns)
- **dd-crawl** — whole-site URL/404 map
- Combined crawl+SEO+speed package → **dd-audit**
