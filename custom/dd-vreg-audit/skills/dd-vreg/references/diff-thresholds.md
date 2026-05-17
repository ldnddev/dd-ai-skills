<!-- Updated: 2026-05-16 -->
# Diff thresholds

The `classifySeverity(bodyPct, topQuarterPct)` function in `scripts/run_visual_regression.js` buckets each page-viewport pair into one of three severity levels using two pixel-diff metrics:

- **bodyPct** — percent of pixels that changed across the *full page body*, excluding the top quarter.
- **topQuarterPct** — percent of pixels that changed in the *top quarter* of the page only.

Both metrics are computed from the side-by-side pixelmatch run in `diffImages()`.

## Buckets

| Severity | Glyph | Rule | Meaning |
|---|---|---|---|
| Critical | 🔴 | `bodyPct >= 5.0` | Substantial body-content regression. Almost always real. Investigate immediately. |
| Warning  | ⚠️ | `bodyPct >= 1.0 AND < 5.0` | Moderate body-content drift. Often real, but verify before opening a bug. |
| Warning  | ⚠️ | `topQuarterPct >= 10.0 AND bodyPct < 1.0` | Hero-region only changed. Likely a [rotating hero](false-positive-patterns.md), date string, or A/B test. Flag with note `"Likely rotating hero — verify"`. |
| Pass     | ✅ | `bodyPct < 1.0 AND topQuarterPct < 10.0` | No meaningful visual regression. |

## Why split body and top-quarter

Hero banners, featured product rotators, and date strings live in the top quarter of most pages. A naive full-page diff treats every cycle of those components as a regression. By separating the two metrics:

- A real layout shift below the fold surfaces as Critical/Warning on `bodyPct` regardless of hero noise.
- A hero-only cycle surfaces as Warning *with a note* on `topQuarterPct`, instead of being silently swallowed (Pass) or escalated (Critical).

Both viewports (desktop 1440×1200 and mobile 390×844) compute the same metrics independently.

## Tuning

Thresholds are intentionally **not configurable in brand.json**. They are part of the audit contract — clients comparing two reports rely on the same buckets meaning the same thing. If a project genuinely needs different thresholds, fork the script.

## See also

- [false-positive-patterns.md](false-positive-patterns.md) — common reasons a diff fires without a real regression.
