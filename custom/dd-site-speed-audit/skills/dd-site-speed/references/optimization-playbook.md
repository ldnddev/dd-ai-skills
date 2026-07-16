# Optimization playbook

<!-- Updated: 2026-07-15 -->

Map common Lighthouse opportunity IDs to concrete fixes. Pair with `framework-tips.md` for stack-specific steps.

## LCP-focused

| Opportunity ID | Fix summary |
|----------------|-------------|
| `render-blocking-resources` | Defer non-critical CSS/JS; inline critical CSS; async/defer scripts. |
| `server-response-time` | Cache HTML, optimize origin TTFB, reduce redirects. |
| `uses-responsive-images` | Correct `srcset`/`sizes`; stop shipping desktop images to mobile. |
| `modern-image-formats` / `uses-webp-images` | AVIF/WebP with fallbacks; CDN transforms. |
| `offscreen-images` | Lazy-load below fold; **never** lazy-load LCP/hero. |
| `priority-hints` | `fetchpriority="high"` + optional preload for LCP image. |
| `font-display` | `font-display: swap`; subset fonts; preload primary face. |
| `uses-text-compression` | Brotli/gzip for text assets. |
| `uses-rel-preconnect` | Preconnect critical third-party origins. |
| `redirects` | Collapse multi-hop redirects. |

### LCP subparts (when diagnosing)

1. **TTFB** — server/CDN/cache  
2. **Resource load delay** — LCP not discoverable early (lazy, JS-injected)  
3. **Resource load duration** — file too large / slow CDN  
4. **Element render delay** — CSS/JS blocking paint  

## INP-focused

| Opportunity ID | Fix summary |
|----------------|-------------|
| `bootup-time` | Smaller JS, less polyfill, defer non-critical scripts. |
| `mainthread-work-breakdown` | Break long tasks; reduce style thrash. |
| `unused-javascript` | Code-split; remove dead libraries; delay third parties. |
| `third-party-summary` | Audit tags; load after consent/idle. |
| `dom-size` | Fewer nodes; virtualize long lists. |

## CLS-focused

| Opportunity ID | Fix summary |
|----------------|-------------|
| `unsized-images` | Explicit width/height or `aspect-ratio`. |
| `layout-shift-elements` | Reserve space for ads/embeds/fonts; avoid injecting above content. |

## Priority heuristic

1. Opportunities with **≥ 1s** estimated savings → P0/Critical  
2. Poor CWV ratings without matching opportunity → still create a metric task  
3. Prefer shared fixes that help every page in a multi-page audit  

## What not to do

- Do not invent savings milliseconds.
- Do not recommend FID optimizations.
- Do not claim “SEO ranking will improve by X positions.”
