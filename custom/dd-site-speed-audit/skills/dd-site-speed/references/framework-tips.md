# Framework-specific speed tips

<!-- Updated: 2026-07-15 -->

Use when `detect_stack.py` reports these labels. Combine with generic playbook items.

## WordPress

- **Images:** ShortPixel, Imagify, or host CDN image transforms; regenerate thumbnails after theme changes.
- **Cache:** Full-page cache (host, WP Rocket, LiteSpeed, Cloudflare APO); object cache (Redis) on dynamic sites.
- **Assets:** Dequeue plugin CSS/JS on templates that do not need them; avoid loading page-builder assets sitewide if unused.
- **LCP:** Ensure hero is a real `<img>` (or background with preload), not lazy-loaded; set dimensions.
- **DB:** Autoload options bloat and heavy queries hurt TTFB — profile with Query Monitor when TTFB is poor.

## Next.js

- Use `next/image` with correct `sizes`; avoid `unoptimized` for LCP.
- `dynamic(() => import())` heavy client components; analyze with `@next/bundle-analyzer`.
- Prefer Server Components for static content; keep client JS minimal for INP.
- Fonts via `next/font` (self-hosted, automatic subsetting).

## React (CSR SPA)

- Code-split routes; consider SSR/SSG or islands if LCP is poor.
- Hydrate only interactive regions; avoid shipping the entire design system to first paint.
- Prefetch critical data carefully — waterfalls hurt TTFB/LCP.

## Shopify

- Remove unused app embeds; each app can add third-party JS.
- Optimize theme Liquid image tags (`image_url` filters, width params).
- Defer non-critical apps until after interaction or consent.

## Drupal

- Aggregated/minified CSS-JS; BigPipe / Dynamic Page Cache where appropriate.
- Image styles for responsive derivatives; CDN for public files.
- Avoid render-cache bypasses on anonymous traffic.

## Vue / Nuxt / Angular / Svelte

- Route-level code splitting; SSR/SSG modes when LCP matters for marketing pages.
- Tree-shake UI libraries; avoid full icon packs.

## Webflow / Wix / Squarespace

- Compress uploaded media before upload; limit custom embed scripts.
- Minimize multi-hop redirects and heavy third-party widgets in the hero.

## Cloudflare / Fastly / other CDN

- Cache HTML for anonymous pages when safe; Polish/Mirage or equivalent for images.
- Early Hints / preconnect for critical origins.
- Review cache status headers when TTFB is high from origin.

## Hosting notes (Pantheon, WP Engine, Vercel, Netlify)

- Confirm page cache HIT rates on production URLs.
- Edge config (ISR, stale-while-revalidate) for framework hosts.
- Avoid audit runs against uncached cold multidev/staging as the only sample when reporting “production” performance.
