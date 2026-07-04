# dd-seo — Google Search Console file-export ingestion

**Date:** 2026-07-04
**Skill:** `custom/dd-seo-audit` (`dd-seo`)
**Status:** Approved design — ready for implementation plan

## Summary

Let the `dd-seo` audit ingest **Google Search Console (GSC) file exports** — the `.zip`
(full Performance export) or a single `.csv` a user downloads from the GSC UI — and use
that real performance data to **enrich the existing audit deliverables**. No OAuth, no API
credentials, no new deliverable. When a GSC file is supplied, the audit gains a "Google
Search Console" section and GSC-derived items are folded into the prioritized action plan.
When no file is supplied, audit output is unchanged.

This is distinct from the existing `gsc_checker.py`, which pulls the **GSC API** (service
account / OAuth). The new path is file-based and zero-auth, but converges on the same
normalized row schema so the report layer is source-agnostic.

## Goals

- Accept `--gsc <path>` where `<path>` is a GSC `.zip` or `.csv` export.
- Parse it with **zero new dependencies** (Python standard library only).
- Derive four insight families and surface them in the report + action plan:
  1. Striking-distance queries
  2. Low-CTR outliers
  3. Top performers + branded/non-branded split
  4. Trends (comparison exports) + query cannibalization
- Re-prioritize fixes using real demand data (impressions/clicks), not just on-page heuristics.
- Keep all query data local — never transmit it.

## Non-goals (deferred)

- Bing Webmaster Tools ingest, GA4, Ahrefs/Semrush/Moz, a real PSI/CrUX key path — all
  noted as future add-ons following this same file-ingest pattern. Not in this spec.
- A standalone `seo gsc <file>` sub-skill / separate deliverable. Enrichment only.
- Any change to the API-based `gsc_checker.py`.

## Approach

**Chosen: a new pure-stdlib `gsc_import.py` that emits the same normalized JSON schema as
`gsc_checker.py`, plus an `insights` block.** `generate_report.py` gains a `--gsc` argument
that, when set, adds `gsc_import.py` to its analyses list.

Rejected alternatives:
- Extend `gsc_checker.py` with a `--from-export` mode — mixes the `google-*` API deps into a
  zero-dep path; import friction.
- Parse inline in `generate_report.py` — already ~69 KB; would bloat a large file.

## Architecture / data flow

```
--gsc <path.zip|.csv>
        │
        ▼
gsc_import.py  ──►  JSON { source:"file", meta{}, rows[], insights{} }
        │              (rows[] identical shape to gsc_checker.py output)
        ▼
generate_report.py
  • adds one analysis entry when --gsc is set (mirrors the existing
    (name, script, args) analyses list invoked with --json)
        │
        ├─►  "Google Search Console" section in index.html + FULL-AUDIT-REPORT.md
        ├─►  prioritized findings in ACTION-PLAN.md
        └─►  rows in tasks.csv
```

When `--gsc` is absent, none of the above runs; output is byte-for-byte unchanged.

## Components

### 1. `skills/dd-seo/scripts/gsc_import.py` (new)

Pure stdlib: `csv`, `zipfile`, `io`, `argparse`, `json`, `sys`, `re`.

**Inputs**
- Positional or flag path to a `.zip` or `.csv`.
- `--json` (emit machine JSON — matches the convention every analysis script uses).
- `--brand "t1,t2"` optional brand tokens (override/augment auto-derivation).
- `--min-impressions N` threshold for striking-distance and low-CTR (default `50`).
- `--url <audited-url>` (passed through by `generate_report.py`) — used to derive the brand
  token from the registrable domain and to focus page-level insights on the audited site.

**Parsing**
- `.zip`: read member CSVs by name — `Queries.csv`, `Pages.csv`, `Countries.csv`,
  `Devices.csv`, `Dates.csv`, `Search appearance.csv`. Use whatever members exist.
- `.csv`: identify the report from its header row (e.g. `Top queries`, `Top pages`, `Date`).
- Normalize each row to `{query?, page?, clicks, impressions, ctr, position}`:
  - `clicks`, `impressions` → int.
  - `ctr` → float percent (`"3.4%"` → `3.4`).
  - `position` → float, 1 decimal.
  - Malformed numeric cell → skip the row, increment a `skipped` counter reported in `meta`.
- **Comparison export detection**: if columns look like `Clicks Last 3 months` /
  `Clicks Previous 3 months` (GSC "Compare" mode), retain both periods per row for trends.
- Localization tolerance: match report/columns case-insensitively and by known aliases; if a
  loose CSV cannot be identified, return a structured error (see Error handling).

**Output JSON**
```json
{
  "source": "file",
  "meta": {
    "input": "<path>",
    "kind": "zip|csv",
    "reports": ["queries","pages","dates"],
    "rows_parsed": 1234,
    "skipped": 3,
    "brand_tokens": ["ldnddev"],
    "comparison": true,
    "min_impressions": 50
  },
  "rows": [
    {"query": "...", "page": "...", "clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}
  ],
  "insights": { "...": "see below" }
}
```

### 2. Insights engine (pure functions inside `gsc_import.py`)

- **striking_distance** — rows with `10 <= position <= 20 AND impressions >= min_impressions`,
  sorted by impressions desc. Each item: query, page (if present), impressions, position, ctr.
- **low_ctr** — rows with `position <= 20 AND impressions >= min_impressions AND ctr` materially
  below the expected-CTR-for-position value from a bundled static benchmark table
  (constant in-module; no network). Each item: query/page, actual vs expected CTR, position, impressions.
- **top_performers** — top-N pages and top-N queries by clicks (default N=10), plus a
  `branded` object: `{branded_clicks, nonbranded_clicks, branded_share_pct}` computed by
  matching `brand_tokens` (auto from domain, override via `--brand`). If no brand token can be
  derived and none supplied, omit the split and note it in `meta`.
- **trends** — only when `meta.comparison` is true: per-query/per-page click and position
  deltas (current − previous), top movers up and down. When absent, key is omitted and a
  `trends_skipped_reason` note is added to `meta`.
- **cannibalization** — queries mapped to ≥2 distinct pages (requires both query and page
  dimensions, i.e. the full ZIP). Each item: query, competing pages with clicks/position.

### 3. `generate_report.py` (modified)

- Add `--gsc <path>` (and pass-through `--brand`, `--min-impressions`) to argparse.
- When `--gsc` is set, append `("gsc", "gsc_import.py", [gsc_path, "--url", url, ...])` to the
  analyses list so it runs through the existing `--json` collection path.
- New render function for the "Google Search Console" section: summary tiles
  (total clicks, impressions, avg CTR, avg position) then one table per non-empty insight.
- Feed **striking_distance** and **low_ctr** items into the ACTION-PLAN findings list and
  `tasks.csv`, phrased as concrete fixes, e.g.
  *"Rewrite title + meta for `/pricing` — position 12, 4,200 impressions, 0.8% CTR (expected ~3%)."*
- Section is omitted entirely if the GSC analysis returned an error or empty insights.

### 4. Accessibility (report HTML)

The new dashboard section renders into `index.html`, which is user-facing. It must match the
existing dashboard's accessible table patterns and meet **WCAG 2.2 AA**: real `<table>` with
`<caption>`, `<th scope="col">` headers, no color-only meaning (pair any color with text/icon),
and section headings that continue the existing heading hierarchy. Reuse the current
dashboard's table/tile components rather than introducing new markup. An accessibility review
of the rendered section is required before the feature is considered complete.

## Error handling / edge cases

- **Not a GSC file** (unrecognizable CSV / ZIP without expected members) → `gsc_import.py`
  returns `{"error": "...", "source": "file"}`; `generate_report.py` logs a warning, omits the
  GSC section, and completes the rest of the audit normally.
- **Partial ZIP** (only some CSVs) → use what exists; insights needing missing dimensions are
  skipped with a reason.
- **Empty file / zero rows** → GSC section omitted; `meta.rows_parsed = 0` recorded.
- **Large exports** → stream rows; cap each rendered table (default 100 rows) and log the cap
  so truncation is never silent.
- **Malformed cells** → skip row, count in `meta.skipped`.
- **Missing brand token** → branded split omitted, noted in `meta`.

## Dependencies & privacy

- **Zero new dependencies.** `csv` + `zipfile` are standard library.
- GSC exports contain real user search queries. All parsing is local; query text appears only
  in the locally-written deliverables and is never sent to any external service.

## Testing

- Unit: parser fixtures for (a) full Performance ZIP, (b) loose `Queries.csv`, (c) loose
  `Pages.csv`, (d) comparison export, (e) malformed rows, (f) non-GSC CSV → error.
- Unit: each insight function against a small crafted row set with known expected output
  (striking-distance boundary at position 10/20, low-CTR vs benchmark, branded matching,
  cannibalization with 2+ pages, trends deltas).
- Integration: `generate_report.py <url> --gsc <fixture.zip>` produces a report containing the
  GSC section and at least one GSC-derived ACTION-PLAN row; the same command without `--gsc`
  produces byte-identical output to today (regression guard).
- Accessibility: rendered GSC section passes the dd-a11y checks (table semantics, headings).

## Documentation

- `SKILL.md`: document `--gsc` on the full/page audit path and the "provide your GSC export"
  trigger wording.
- `resources/skills/seo-audit.md` and `seo-page.md`: note GSC enrichment when a file is passed.
- `README.md`: one line under the SEO features list.

## Rollout

- Bundle version bump for `dd-seo` plugin (`plugin.json`) on release.
- Backward compatible: no behavior change unless `--gsc` is passed.
