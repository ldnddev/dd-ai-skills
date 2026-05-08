# SEO Full Audit — ldnddev.com

**URLs audited:** `https://www.ldnddev.com/` · `https://www.ldnddev.com/blog/`
**Date:** 2026-05-06
**Method:** LLM-first analysis with deterministic script verification (`dd-seo` skill v1.0.0)
**Overall score:** **57/100** — Needs Improvement

---

## Executive Summary

ldnddev.com has clean URL structure, working sitemap, valid canonicals, populated alt text, and modern image formats (WebP). The biggest drags on score are:

1. **Critical:** the homepage main content is loaded via HTMX after page load (`<main hx-trigger="load" hx-get="/home.html">`), so crawlers that don't fully render JS see a near-empty document.
2. **Critical:** zero JSON-LD structured data anywhere on the audited URLs (no Organization, WebSite, BlogPosting, BreadcrumbList).
3. **Critical:** zero Open Graph / Twitter Card tags on either URL — social/LinkedIn shares get no rich preview.
4. **Critical:** missing security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy). Site scored 25/100 on the security-headers check.
5. **Warning:** blog index meta description is `"ldndddev insights."` — typo (`ldndddev` has three `d`s) and 18 chars, which Google will rewrite.

The blog index itself is in much better shape than the homepage — it has an H1, structured H3 list, lazy-loaded WebP thumbnails with descriptive alt text, and crawlable internal links. All 22 internal links checked from the blog index returned HTTP 200.

---

## Category Scores

| Category | Weight | Score | Notes |
|---|---|---|---|
| Technical SEO | 25% | 60/100 | HTMX-rendered home; security headers missing |
| Content Quality | 20% | 70/100 | H1s present, decent E-E-A-T signals on posts |
| On-Page SEO | 15% | 60/100 | Blog meta description typo + too short |
| Schema / Structured Data | 15% | 10/100 | None detected |
| Performance (CWV) | 10% | 60/100 | Hypothesis — PageSpeed API rate-limited |
| Image Optimization | 10% | 80/100 | WebP, alt text, srcset on hero |
| AI Search Readiness (GEO) | 5% | 30/100 | llms.txt empty; no schema |
| **Weighted total** | 100% | **57/100** | Needs Improvement |

---

## Findings — Homepage (`/`)

| # | Finding | Evidence | Impact | Severity | Confidence |
|---|---|---|---|---|---|
| H1 | Main content not in initial HTML | `home.html:35` → `<main id="main-content" hx-trigger="load" hx-get="/home.html">`. The shipped HTML body has no H1, no copy, no nav links — only a skeleton. The actual content lives at `/home/` and is injected after page load by HTMX. | Crawlers that don't run JS see a blank page. Even Googlebot (which renders JS) treats client-rendered content as second-tier and may delay indexing. AI crawlers (GPTBot, PerplexityBot, ClaudeBot) generally do **not** execute JavaScript. | 🔴 Critical | Confirmed |
| H2 | Header & footer also lazy-loaded | `home.html:33,37` use the same HTMX pattern: `hx-trigger="load" hx-get="/includes/header.html"`. Initial HTML contains no `<nav>`, no internal links. | Internal-link graph is invisible to non-rendering crawlers; PageRank flow from homepage is broken for AI/text-only bots. | 🔴 Critical | Confirmed |
| H3 | Zero structured data | `grep -c "application/ld+json" home.html` → 0. No Organization, WebSite (with `SearchAction`), or BreadcrumbList. | Loses rich-result eligibility, knowledge-panel signals, and AI-overview attribution opportunities. | 🔴 Critical | Confirmed |
| H4 | No Open Graph or Twitter Card tags | `social_meta.py` reported 0/7 OG, 0/6 Twitter. | Shares on LinkedIn/X/Facebook/Slack render as bare URL with no image or description. | 🔴 Critical | Confirmed |
| H5 | Title tag fine | `<title>Custom Drupal & WordPress Development | ldnddev</title>` — 49 chars. | Pass. | ✅ Pass | Confirmed |
| H6 | Meta description fine | 161 chars, includes target terms (Drupal, WordPress, healthcare, B2B, SOC2/HIPAA). | Pass. | ✅ Pass | Confirmed |
| H7 | Canonical correct | `<link rel="canonical" href="https://www.ldnddev.com/" />` | Pass. | ✅ Pass | Confirmed |
| H8 | `lang="en"` set | `<html lang="en">` | Pass — but no `hreflang` (only an issue if you add other locales). | ✅ Pass | Confirmed |
| H9 | Hero copy is one short H2 + one paragraph after HTMX render | `/home.html` fragment: 460 words total across the page. | Thin for a B2B services homepage. Add a services overview block, proof points (logos, metrics), and an FAQ section to reach 800+ words and increase topical coverage. | ⚠️ Warning | Confirmed |
| H10 | All hero images have alt text + srcset | `home.html` (fragment): 7 images, 0 missing alt. WebP with `sizes`/`srcset`. | Pass. | ✅ Pass | Confirmed |
| H11 | Heading hierarchy after render | H1 "Driven to Achieve business goals." + 5 H2s. No H3s. | Acceptable. Consider adding H3s under each section for scannability and AI extraction. | ⚠️ Warning | Confirmed |

---

## Findings — Blog Index (`/blog/`)

| # | Finding | Evidence | Impact | Severity | Confidence |
|---|---|---|---|---|---|
| B1 | Meta description typo + too short | `<meta name="description" content="ldndddev insights." />` — note `ldndddev` with three `d`s; only 18 chars. | Google will replace with auto-generated text; reflects poorly on brand attention to detail. | 🔴 Critical | Confirmed |
| B2 | No JSON-LD on blog index | Same `grep` returned 0 occurrences. | A blog index is a strong candidate for `Blog` + `BreadcrumbList` schema and per-item `BlogPosting` references. | 🔴 Critical | Confirmed |
| B3 | No Open Graph / Twitter Card | `social_meta.py` 0/7 OG, 0/6 Twitter. | Same as homepage — shares look broken. | 🔴 Critical | Confirmed |
| B4 | Title tag fine | `<title>ldnddev, LLC. | From the ldnddev Blog</title>` — 41 chars. | Pass — but consider adding a primary keyword (e.g. "Drupal & WordPress Development Insights"). | ⚠️ Warning | Confirmed |
| B5 | H1 present and unique | `<h1>Insights From the ldnddev Blog</h1>` | Pass. | ✅ Pass | Confirmed |
| B6 | 23 H3 cards for posts, no H2s | `parse_html.py` returned 0 H2 and 23 H3. | Heading hierarchy skips a level. Convert section headings (e.g. one H2 "Latest posts") and keep individual cards as H3, OR convert cards to H2 if they're top-level navigational items. | ⚠️ Warning | Confirmed |
| B7 | All thumbnails have alt + width/height + lazy | 22 thumbnails: every one has `alt`, `width="768"`, `height="287"`, `loading="lazy"`. | Pass — strong CLS protection. | ✅ Pass | Confirmed |
| B8 | Some alt text duplicated | Four post cards share alt text "What Developers Need to Know" (CMS, Leveraging-AI, AI-game-changer, AI-powered-web-dev). | Duplicate alt across distinct posts dilutes accessibility and image-search signal. Each thumbnail should describe its specific post. | ⚠️ Warning | Confirmed |
| B9 | Internal-link text is generic / non-keyword | Anchor text on cards: "Better Together.", "Change the approach.", "Arch BTW.", "Diff Away.", "GIT Workflows.", etc. | Non-descriptive anchor text loses SEO value and accessibility. Use the post title or a keyword-rich phrase. | ⚠️ Warning | Confirmed |
| B10 | All 22 internal links return 200 | `broken_links.py` — 22 healthy, 0 broken, 0 redirected. | Pass. | ✅ Pass | Confirmed |
| B11 | Single-paragraph layout flagged | `readability.py` — paragraph_count 1, sentence_count 34. | Indicates the script's heuristic — actual rendered HTML has many `<h3>` cards, so this is likely a false positive from the card structure. Re-verify when adding article-level summaries below each card. | ℹ️ Info | Hypothesis |
| B12 | No author/Person schema | No JSON-LD anywhere; no `rel="author"`. | E-E-A-T attribution depends on author signals. Add `Person` schema (with `sameAs` pointing to LinkedIn/GitHub) referenced by each `BlogPosting`. | ⚠️ Warning | Confirmed |

---

## Findings — Site-Wide (apply to both URLs and beyond)

| # | Finding | Evidence | Impact | Severity | Confidence |
|---|---|---|---|---|---|
| S1 | Six security headers missing | `security_headers.py` 25/100. Missing: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy. | Direct ranking impact is small, but Google flags HTTPS without HSTS as weaker; some PageSpeed best-practice audits dock points; clickjacking/XSS/MIME-sniffing exposure is real. | 🔴 Critical | Confirmed |
| S2 | `llms.txt` exists but empty | `llms_txt_checker.py` — 5/100, no title, no description, no sections, no links. `llms-full.txt` also exists. | AI search engines (Perplexity, ChatGPT, Claude.ai citations) prefer a populated llms.txt to understand site structure. Empty file is worse than absent for first impressions. | ⚠️ Warning | Confirmed |
| S3 | `robots.txt` is well-formed | Allows all UAs, disallows `/assets/`, `/dist/`, `/node_modules/`, query-string variants. AI crawlers commented out (deliberate "allow" stance). Sitemap declared. | Pass. The skill's robot-checker flagged "AI crawlers not managed" but you've explicitly chosen to let them through — that is a valid choice for a B2B site that wants AI-search visibility. | ✅ Pass | Confirmed |
| S4 | Sitemap is valid | `/sitemap.xml` returns valid XML with priorities, changefreqs, lastmods. Core pages 1.00/0.90, blog posts 0.80. | Pass. Consider splitting into a sitemap index once you exceed ~50K URLs (not close yet). | ✅ Pass | Confirmed |
| S5 | Cloudflare CDN active | `server: cloudflare`, `cf-cache-status: HIT`, HTTP/2, h3 advertised via `alt-svc`. | Pass — global delivery and edge caching are working. | ✅ Pass | Confirmed |
| S6 | HTTP/HTTPS canonical clean | `redirect_checker.py` — `https://www.ldnddev.com` returns 200 in one hop; no chain. | Pass. | ✅ Pass | Confirmed |
| S7 | PageSpeed not measured (env limit) | Google PageSpeed Insights API rate-limited the unauthenticated request. | Cannot confirm LCP/INP/CLS values today. **Likely concern:** the HTMX-fetch pattern adds an extra round-trip before LCP element paints, which typically pushes mobile LCP past 2.5s. | ⚠️ Warning | Hypothesis |
| S8 | Header/footer in client-fetched fragments | `<header hx-trigger="load" hx-get="/includes/header.html">` on every page sampled. | Same crawlability concern as homepage main content for non-JS bots. Either inline the nav or server-side-include it before delivery. | 🔴 Critical | Confirmed |

---

## Environment Limitations

- **Google PageSpeed Insights API** rate-limited for both URLs without an API key. CWV scores are rated `Hypothesis` accordingly. To get definitive numbers: run with a free PSI API key, or check Search Console → Core Web Vitals report against real-user data.
- **Header fragment** (`/includes/header.html`) blocked by Cloudflare for plain `curl` user-agents during this audit. The page-fetch script (which sets a browser UA) succeeded for all primary URLs.
- Visual / Playwright screenshots not run this session.

---

## What's Already Good

- Cloudflare CDN with HTTP/2 + HTTP/3 advertised.
- WebP images with responsive `srcset` on hero blocks.
- Alt text populated on 100% of sampled images.
- `width`/`height`/`loading="lazy"` on blog thumbnails (CLS-safe).
- Clean canonical tags, `lang="en"`, single-hop HTTPS.
- Valid robots.txt with explicit asset blocks and sitemap declaration.
- Sitemap with sensible priorities and recent `lastmod` dates.
- All 22 internal links from the blog index resolved 200.
- Blog post template surfaces author + date inline (`*By Jared Lyvers, ldnddev — March 23, 2026*`) — strong E-E-A-T base; just needs schema to match.
