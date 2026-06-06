---
name: dd-site-compare
description: >
  Generate self-contained HTML dashboards that compare multiple websites by URL, HTTP status,
  response time, page size, total load size, resource counts, largest item, trackers, title,
  meta description, heading/image/link counts, detected technologies, dependency-free keyword
  phrases, mobile viewport support, server headers, and errors. Supports parallelism and ~31
  quantitative + qualitative signals.
  When --web is used, automatically writes the HTML (as index.html) + JSON into
  web/<primary-domain>-compare-audit-YYYY-MM-DD/ at the project root.
  Use when the user pastes 2+ URLs (or a file), asks to "compare websites", "competitive analysis",
  "site audit dashboard", "homepage comparison report", or invokes /dd-site-compare or $dd-site-compare.
version: 1.1.1
when-to-use: "Use for website comparisons, competitive audits, multi-site technical reports, or when a self-contained HTML + JSON dashboard of homepage metrics is needed. Trigger phrases: compare sites, site comparison, website audit, competitive analysis, dashboard for these URLs."
argument-hint: "[urls...] [--web] [--urls-file file.txt] [--skip-resources] [--max-resources N] [--workers 4] [--json-output out.json] [-o out.html]"
---

# DD Site Compare

**v1.1 adds 12 new strictly-required fields** (final_url, redirected, word_count, h2/h3 counts, images_missing_alt, external_link_count, has_favicon, has_canonical, json_ld_count, server, powered_by), parallel fetching (default 4 workers), client-side sort/filter/export in the dashboard, richer field docs, dark mode, a `scripts/verify.py` harness, and the `--web` flag for automatic `web/<domain>-compare-audit-YYYY-MM-DD/` placement. All prior CLI flags and output shape remain compatible; new fields are always present.

## Workflow

1. Collect the target website URLs from the user prompt, a pasted list, or a text file.
2. Normalize missing schemes by adding `https://` (the script does this).
3. Run `scripts/compare_websites.py` (from the skill dir or with absolute path), preferably with `--web` so the output HTML (index.html) and data.json are placed in the conventional project-level location:
   `web/<first-domain>-compare-audit-YYYY-MM-DD/`
   (e.g. `web/example.com-compare-audit-2025-06-02/index.html`).
   This follows the required naming convention for web-served audits.
4. **Run `python3 scripts/verify.py`** (or the manual equivalent in the Verification section) and confirm the output includes **every field** listed in the current `references/fields.md` (the contract is now 31 fields).
5. Report the generated HTML (and JSON) path(s). Explicitly note any URLs that failed or redirected. Mention that the dashboard is fully self-contained (open it in any browser, no server).

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
├── index.html   # the self-contained dashboard
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

## Required Fields (Contract)

**Load `references/fields.md` before emitting or auditing output.** The script and dashboard **must** include every field for every row. The contract is additive and now strictly enforced (v1.1).

See the expanded reference for types, computation notes, and "lower/higher is better" guidance.

Legacy note: older notebook `script.py` / `keywords.py` were the source of the original implementation. Always use the CLI in `scripts/compare_websites.py`.

## Notes For Agents

- Keep user-provided URLs in the report (even on redirect). Populate `final_url` + `redirected`.
- Always emit a row for every input URL; use the `error` field instead of omitting.
- When the user says "like the old demo" or "Markdown table", still produce (and point to) the **self-contained HTML dashboard** + optional JSON. Never hand-craft a static MD transcript.
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

This discipline keeps the 31+ field contract and the zero-dep contract intact.
