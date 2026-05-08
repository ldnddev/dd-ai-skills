# SEO Action Plan — ldnddev.com

**Source audit:** `FULL-AUDIT-REPORT.md` (2026-05-06)
**Scoring basis:** Impact × Effort. Do P0s this week, P1s this month, P2s this quarter.

---

## P0 — Critical, fix this week

### 1. Stop client-rendering the homepage main content
**Problem:** `<main hx-trigger="load" hx-get="/home.html">` and `<header hx-get="/includes/header.html">` defer the actual content to a second HTTP round-trip on every page. Non-JS crawlers (GPTBot, ClaudeBot, PerplexityBot, plain text fetchers) see an empty shell.
**Fix:** Server-side include the homepage hero/sections and the header/footer before sending HTML. Keep HTMX for in-page interactions (forms, filtering), not for the initial frame. If a static site generator is in play, render the layout into every page at build time.
**Verify:** `curl -A "Mozilla/5.0" https://www.ldnddev.com/ | grep -c "<h1>"` should return `1` (or more), not `0`.

### 2. Add JSON-LD structured data
**Problem:** Zero schema across audited pages.
**Fix:** Add three schema blocks to the appropriate templates (use JSON-LD only — no Microdata/RDFa):

- **Site-wide (in `<head>` of every page):** `Organization` + `WebSite` (with `SearchAction`).
- **Blog index:** `Blog` + `BreadcrumbList`.
- **Blog post template:** `BlogPosting` (with `author` → `Person`, `datePublished`, `dateModified`, `image`, `mainEntityOfPage`) + `BreadcrumbList`. Reference an `@id`'d `Person` for Jared Lyvers with `sameAs` linking to LinkedIn/GitHub.

Templates exist at `<dd-seo skill>/resources/schema/templates.json`. **Do not** use `FAQPage` (commercial-restricted) or `HowTo` (deprecated). Validate with `python3 <dd-seo>/scripts/validate_schema.py <file>` before deploy.

### 3. Add Open Graph + Twitter Card tags
**Problem:** 0/7 OG, 0/6 Twitter on both audited URLs.
**Fix:** Add to the base `<head>` template:

```html
<meta property="og:type" content="website">
<meta property="og:title" content="{{ page_title }}">
<meta property="og:description" content="{{ meta_description }}">
<meta property="og:url" content="{{ canonical_url }}">
<meta property="og:image" content="{{ social_image_1200x630 }}">
<meta property="og:site_name" content="ldnddev">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ page_title }}">
<meta name="twitter:description" content="{{ meta_description }}">
<meta name="twitter:image" content="{{ social_image_1200x630 }}">
```

For blog posts use `og:type="article"` plus `article:published_time`, `article:author`, `article:tag`. Generate 1200×630 social images per post (the existing `hero-lg.webp` is close — just confirm crop ratio).

### 4. Fix the blog index meta description
**Problem:** `<meta name="description" content="ldndddev insights." />` — typo (`ldndddev` has three `d`s) and only 18 chars.
**Fix:** Replace with 140–160 chars of real copy, e.g.:

> Insights on Drupal, WordPress, AI-driven development, accessibility, and modern web tooling — written by the ldnddev team for builders and decision-makers.

### 5. Add the missing security headers
**Problem:** `security_headers.py` scored 25/100. Missing HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
**Fix:** Set these via Cloudflare → Rules → Transform Rules → Modify Response Headers (no origin change needed):

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'self'
```

Tighten the CSP after a one-week report-only trial (`Content-Security-Policy-Report-Only:` first). Drop `'unsafe-inline'` once inline scripts/styles are removed or hashed.

---

## P1 — Important, fix this month

### 6. Populate `llms.txt`
**Problem:** Score 5/100 — empty file. AI search engines treat this as a low-quality signal.
**Fix:** Replace with a populated file matching the [llmstxt.org](https://llmstxt.org) spec:

```markdown
# ldnddev

> ldnddev is a B2B web development studio specializing in Drupal and WordPress for healthcare, outreach, and service-industry brands. SOC2 / HIPAA-aware delivery.

## Core pages
- [Services](https://www.ldnddev.com/services/): Drupal & WordPress engagement models
- [Experience](https://www.ldnddev.com/experience/): Sectors and case-study highlights
- [Results](https://www.ldnddev.com/results/): Client outcomes
- [Brands](https://www.ldnddev.com/brands/): Brands we partner with
- [Contact](https://www.ldnddev.com/contact-us/): Get in touch

## Blog
- [Blog index](https://www.ldnddev.com/blog/): Insights from the ldnddev team

## Optional
- [Sitemap](https://www.ldnddev.com/sitemap.xml)
```

### 7. Tighten anchor text on the blog index
**Problem:** Card anchors are flavor text ("GIT Workflows.", "Diff Away.", "Arch BTW."). Search engines and screen readers can't tell what each link leads to.
**Fix:** Use the post title as anchor text (or a descriptive variant). Keep the flavor line as visible card copy if you like the voice — just wrap the title in the `<a>` instead.

### 8. De-duplicate blog thumbnail alt text
**Problem:** Four cards reuse the alt `"What Developers Need to Know"`.
**Fix:** Make each alt describe its specific post (e.g. "Headless vs traditional CMS comparison illustration", "AI-game-changer SEO email-marketing chart"). No two thumbnails on the same page should share alt text.

### 9. Fix heading hierarchy on the blog index
**Problem:** Page goes H1 → 23 × H3 with no H2.
**Fix:** Either (a) wrap card sections in an H2 like "Latest insights" / "Featured" / "All posts", or (b) promote each card title to H2 if there is no group hierarchy. Pick one — don't mix.

### 10. Get Core Web Vitals data
**Problem:** PSI was rate-limited; no confirmed LCP/INP/CLS numbers.
**Fix:** Run the page through PSI manually (`https://pagespeed.web.dev/?url=https%3A%2F%2Fwww.ldnddev.com%2F`) and check Search Console → Core Web Vitals (real-user CrUX data, more authoritative). Once homepage main content is no longer HTMX-deferred (P0 #1), LCP should drop materially. Expected wins: ≥30% LCP improvement on mobile.

### 11. Add `Person` schema for the author
**Problem:** No author entity exists for E-E-A-T attribution.
**Fix:** Create `/about-jared/` (or `/team/jared-lyvers/`) with `Person` JSON-LD, `sameAs` to LinkedIn/GitHub, role at ldnddev, areas of expertise. Reference its `@id` from every `BlogPosting.author`.

---

## P2 — Optimize, fix this quarter

### 12. Expand homepage word count to ≥800
**Problem:** Rendered homepage is ~460 words.
**Fix:** Add a services overview block with three to five service cards (Drupal builds, WordPress builds, accessibility, performance, ongoing care), a proof block (logos / metrics / testimonials), and a brief FAQ section (without `FAQPage` schema — that type is restricted to gov/healthcare authorities).

### 13. Add `BreadcrumbList` schema globally
**Problem:** No breadcrumbs appear in document HTML or JSON-LD.
**Fix:** Render a visible breadcrumb on interior pages (`Home > Blog > Post Title`) and emit matching `BreadcrumbList` JSON-LD. This drives the breadcrumb path display in Google SERPs.

### 14. Add a populated FAQ section to `/services/`
Without `FAQPage` schema, you still get user-answer benefits and AI-overview attribution. Aim for 5–8 questions that match real client objections (cost ranges, timelines, accessibility/HIPAA scope, headless vs traditional, ongoing-care models).

### 15. Build out a topic cluster around "Drupal accessibility" and "WordPress for healthcare"
You already have `dd_wcag` content — turn it into a cluster page (`/services/accessibility/`) that links out to all the WCAG/APCA posts. Same for HIPAA / healthcare CMS. This concentrates topical authority on commercial-intent landing pages.

### 16. Set up GSC + Bing Webmaster + IndexNow
- Submit `sitemap.xml` to Google Search Console and Bing Webmaster Tools.
- Wire up IndexNow (`<dd-seo>/scripts/indexnow_checker.py`) — publish, ping, and Bing/Yandex crawl within minutes.

### 17. Plan a competitive entity sweep
Run `<dd-seo>/scripts/competitor_gap.py` and `entity_checker.py` against two or three peer studios (e.g. Lullabot, Mediacurrent, 10up) to find topical gaps and entity coverage holes for the cluster pages above.

---

## Acceptance Tests (run after each P0/P1 batch lands)

```bash
SKILL=/home/jlyvers/.claude/plugins/cache/dd-skills/dd-seo/1.0.0/skills/dd-seo
python3 $SKILL/scripts/social_meta.py https://www.ldnddev.com           # expect 7/7 OG
python3 $SKILL/scripts/social_meta.py https://www.ldnddev.com/blog/     # expect 7/7 OG
python3 $SKILL/scripts/security_headers.py https://www.ldnddev.com      # expect ≥85/100
python3 $SKILL/scripts/llms_txt_checker.py https://www.ldnddev.com      # expect ≥70/100
curl -sA "Mozilla/5.0" https://www.ldnddev.com/ | grep -c "application/ld+json"  # expect ≥1
curl -sA "Mozilla/5.0" https://www.ldnddev.com/ | grep -c "<h1"                  # expect ≥1 (no JS render)
python3 $SKILL/scripts/pagespeed.py https://www.ldnddev.com --strategy mobile    # rerun w/ API key
```

---

## Quick Reference — Severity Budget

| Severity | Count | Examples |
|---|---|---|
| 🔴 Critical | 8 | HTMX-deferred main, missing schema, missing OG, security headers, blog meta typo |
| ⚠️ Warning | 7 | Heading hierarchy, anchor text, duplicate alt, llms.txt empty, thin homepage |
| ✅ Pass | 9 | HTTPS clean, sitemap valid, alt coverage, WebP, canonical, robots, etc. |
| ℹ️ Info / Hypothesis | 2 | CWV (rate-limited), readability paragraph heuristic |

Generated artifacts: `FULL-AUDIT-REPORT.md`, `ACTION-PLAN.md`.
