# SEO Full Audit — threeriversinspection.com

- **Audit date**: 2026-05-07
- **Auditor**: dd-seo (LLM-first + script-backed)
- **Pages audited**: 5 supplied URLs + sitewide signals (robots.txt, sitemap, headers)
- **Bundle**: `web/threeriversinspection.com-seo-audit-2026-05-07/`
- **Overall score (script-derived)**: **65 / 100 — Needs Improvement**

## Pages In Scope

| # | URL | Title chars | H1 | Meta Desc | Words |
|---|-----|------------:|----|-----------|------:|
| 1 | `/` | 70 | 1 | ❌ missing | 322 |
| 2 | `/home-page/` | 78 | 1 | ❌ missing | 1,005 |
| 3 | `/she-engineering-home-page-2/` | 74 | 1 | ❌ missing | 334 |
| 4 | `/about-us/` | 51 | 1 | ❌ missing | 181 |
| 5 | `/real-estate-agents/` | 61 | **0** | ❌ missing | 353 |

## Score Breakdown (Default Weights)

| Category | Weight | Status | Notes |
|---|---:|---|---|
| Technical SEO | 25% | ⚠️ 70 | HTTPS+HSTS pass, canonicals correct; sitemap uses `http://`; CSP + Permissions-Policy missing |
| Content Quality | 20% | ⚠️ 55 | Thin About + Home; Flesch 38 (college-level); E-E-A-T author entity not marked up |
| On-Page SEO | 15% | 🔴 45 | All 5 pages missing meta description; 1 page missing H1; titles all-caps + duplicate brand |
| Schema | 15% | ⚠️ 65 | WebPage/Org/WebSite/Breadcrumb present; **no LocalBusiness, no Person, no Service** |
| Performance (CWV) | 10% | ℹ️ Hyp | PageSpeed API rate-limited — Environment Limitation |
| Image Optimization | 10% | ⚠️ 60 | Logo `alt=""` empty, 4 tracking pixels with no alt, no responsive `<img srcset>` evidence |
| AI Search (GEO) | 5% | 🔴 30 | GPTBot/ClaudeBot/Google-Extended/Applebot-Extended/Bytespider/CCBot all blocked; no `/llms.txt` |

---

## 🔴 Critical Findings

### C-1. Meta description missing on every audited page
- **Evidence**: `parse_html.py` JSON for all 5 URLs returns `meta_description: null`. Verified via `grep '<meta name="description"' /tmp/3ri/p*.html` → 0 hits.
- **Impact**: Google synthesizes snippet from on-page text — unpredictable CTR, weaker SERP framing for "home inspection Pittsburgh", "structural engineer Pittsburgh", "PA professional engineer home inspection".
- **Fix**: Yoast SEO is installed (sitemap signature). In WP admin → each page → Yoast meta description. 140–160 chars, lead with primary phrase + Pittsburgh / Southwestern PA + differentiator (PE-led, 15,000 inspections).

### C-2. `/real-estate-agents/` has zero `<h1>`
- **Evidence**: `grep -c '<h1' /tmp/3ri/p5.html` → `0`. Parsed `h1: []`, only H2 elements.
- **Impact**: Page topical signal lost; accessibility tree starts at H2.
- **Fix**: Add `<h1>Real Estate Agent Resources & Referral Inspections</h1>` (or similar) at top of content area. Demote any current H2 that duplicates the topic.

### C-3. No `LocalBusiness` / `HomeAndConstructionBusiness` schema
- **Evidence**: JSON-LD `@graph` contains `Organization`, `WebSite`, `WebPage`, `BreadcrumbList`. No `LocalBusiness` subtype, no `address`, no `telephone`, no `geo`, no `openingHoursSpecification`. NAP is in About page text only ("4885-A McKnight Rd, 292 Pittsburgh 15237 / 412 331 5665").
- **Impact**: Pittsburgh Knowledge Panel weaker, lower local pack eligibility, AI assistants cannot reliably extract NAP.
- **Fix**: Replace `Organization` node in Yoast (Site → Knowledge Graph) with `HomeAndConstructionBusiness` (subclass of LocalBusiness). Include `address` (PostalAddress), `telephone`, `geo` lat/lng, `openingHoursSpecification` Mon–Fri 09:00–17:00, `areaServed`: "Southwestern Pennsylvania", `priceRange`, `image`, `sameAs` (Facebook, LinkedIn, Google Business Profile URL).

### C-4. No `Person` schema for Russell Kowalik, PE
- **Evidence**: `/about-us/` has E-E-A-T-grade biography (Carnegie Mellon BS, PA-licensed PE, 15,000+ inspections). Schema graph has zero `Person` node.
- **Impact**: Author authority not machine-readable. Google December 2025 E-E-A-T applies sitewide; entity disambiguation lost.
- **Fix**: Add `Person` JSON-LD on `/about-us/` and reference via `Organization.founder` / `WebPage.author`. Include `name`, `jobTitle`, `alumniOf` (Carnegie Mellon University), `hasCredential` ("Pennsylvania Professional Engineer"), `sameAs` (LinkedIn).

### C-5. Sitemap entries use `http://` (mixed protocol)
- **Evidence**: `https://threeriversinspection.com/sitemap_index.xml` lists `<loc>http://threeriversinspection.com/post-sitemap.xml</loc>` etc. Canonicals + site URL are HTTPS.
- **Impact**: Crawl friction; Yoast bug or stale `siteurl` option. Mixed-protocol URLs in `<loc>` violate sitemap protocol cleanliness even if served over redirect.
- **Fix**: WP admin → Settings → General → confirm both Site Address and WordPress Address are `https://`. Or in Yoast → flush sitemap cache. Verify `<loc>` rebuilds with `https://`.

### C-6. `og:image` missing → social previews broken
- **Evidence**: `social_meta.py` 54/100. `grep '<meta property="og:image"' p1.html` → 0 hits.
- **Impact**: Facebook/LinkedIn/Slack/iMessage shares render text-only; weaker referral CTR.
- **Fix**: Yoast → Social → Facebook → upload 1200×630 default OG image (logo + tagline on solid bg). Per-page overrides for top pages.

---

## ⚠️ Warnings

### W-1. AI crawlers fully blocked — kills GEO/AEO
- **Evidence**: `robots_checker.py` confirms `Disallow: /` for GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, Bytespider, CCBot, Amazonbot, meta-externalagent, CloudflareBrowserRenderingCrawler.
- **Impact**: Site cannot appear in ChatGPT browsing, Claude search results, Google AI Overviews (Google-Extended controls Gemini/AIO grounding), Apple Intelligence, Perplexity/Bytedance citations. For a local service biz this is direct lead loss as buyers shift to AI assistants.
- **Fix**: In `robots.txt` change to `Allow: /` for these agents (or remove the `Disallow: /` lines). Decide policy intentionally — current config likely a default theme/plugin "block AI" toggle that wasn't reviewed for SEO impact.

### W-2. Title pattern duplicates brand and exceeds 60 chars
- **Evidence**: 3 of 5 titles are 70–78 chars. Pattern: `THREE RIVERS - <SECTION> PAGE - Three Rivers Inspections and Engineering`. Brand appears twice; "PAGE" is filler.
- **Fix**: Rewrite per-page titles to lead with primary phrase + city, single brand suffix. Examples:
  - Home: `Pittsburgh Home Inspections by a Professional Engineer | Three Rivers`
  - `/home-page/`: `Home Inspection Services — Pittsburgh, PA | Three Rivers Inspections`
  - `/she-engineering-home-page-2/`: `Structural Engineering Assessments — Pittsburgh | Three Rivers`
  - `/about-us/`: keep current (51 chars, OK)
  - `/real-estate-agents/`: `Inspections for Real Estate Agents — Southwestern PA | Three Rivers`

### W-3. About page is thin for an E-E-A-T cornerstone
- **Evidence**: 181 words. Three bios (Russ, Natalie, Max) compressed to 1–2 sentences each.
- **Fix**: Expand to 600–900 words. Per-team-member: full credentials, years active, certifications (PA PE license #, ASHI/InterNACHI), notable projects/case-study counts, head-and-shoulder photo with descriptive `alt`. Add inline `Person` JSON-LD for each.

### W-4. Two orphan high-value pages
- **Evidence**: `internal_links.py` flags `/three-rivers-sample-home-inspection-report` and `/engineering-report-sample` with ≤1 incoming link.
- **Impact**: These are exactly the pages buyers want — proof of report quality. Currently undiscoverable from key landing pages.
- **Fix**: Link from `/home-page/`, `/she-engineering-home-page-2/`, `/real-estate-agents/`, and the home page hero. Anchor: "See a sample home inspection report" / "View a sample engineering report".

### W-5. Missing security headers (CSP, Permissions-Policy)
- **Evidence**: `security_headers.py` 75/100. HSTS, X-Frame-Options, X-CTO, Referrer-Policy present.
- **Fix**: Add `Permissions-Policy: camera=(), microphone=(), geolocation=()`. CSP requires inventory of inline scripts (Yoast, GA, Facebook Pixel) — start in Report-Only mode.

### W-6. No `/llms.txt`
- **Evidence**: `llms_txt_checker.py` → 404.
- **Fix**: Create `/llms.txt` listing site name, business description, hours, service area, NAP, and links to `/about-us/`, `/home-page/`, `/she-engineering-home-page-2/`, sample reports. Pairs with W-1 unblock.

### W-7. Broken Cloudflare email-protection link
- **Evidence**: `broken_links.py` flags `/cdn-cgi/l/email-protection` → 404. Caused by Cloudflare email obfuscation enabled but the script linked from a static `[email protected]` anchor whose `data-cfemail` attr did not render.
- **Fix**: Toggle Cloudflare → Scrape Shield → Email Address Obfuscation off OR fix the menu/widget that linked the obfuscated href as a real `mailto:`. Replace anchor with `mailto:info@threeriversinspection.com`.

### W-8. Logo `alt=""` (empty)
- **Evidence**: Both `<img>` references to `ThreeRivInspectEngin_logo_color_nobkgnd.png` have `alt=""`.
- **Impact**: Image SEO loses brand keyword; a11y screen-readers skip a meaningful navigation graphic when it is wrapped in a link.
- **Fix**: `alt="Three Rivers Inspections and Engineering — Pittsburgh, PA"` (since logo is wrapped in home-link).

### W-9. Readability Very Difficult (college)
- **Evidence**: Flesch 38.9 home, 38.8 about, 53 agents. Grade level 11.8–12.8.
- **Fix**: Shorter sentences, plain English on consumer-facing pages. Target Flesch 60+. Engineering page can stay technical.

### W-10. Author sitemap stale (2023-09-26)
- **Evidence**: `sitemap_index.xml` shows `author-sitemap.xml` lastmod 2023-09-26.
- **Fix**: Yoast → flush, or disable author archive sitemap if author pages are noindex.

---

## ✅ Passes

- HTTPS site-wide, HSTS preload-eligible (`max-age=31536000; includeSubDomains`)
- Canonical present and self-referential on every page
- `meta robots: index, follow, max-image-preview:large` set
- BreadcrumbList JSON-LD present and well-formed
- WebSite + SearchAction JSON-LD present (sitelinks search box eligible)
- `<html lang="en-US">` + viewport meta present
- Yoast-managed sitemap exists and lists post/page/category sitemaps
- 0 redirects on home (clean 200) — fast first byte path
- 0 mixed content / no insecure-protocol asset warnings flagged

---

## ℹ️ Environment Limitations

- **PageSpeed Insights API rate-limited** — Core Web Vitals (LCP, INP, CLS) not measured this run. Re-run `pagespeed.py --strategy mobile` and `--strategy desktop` with a Google API key, or use field data via Search Console CrUX. Performance score in the bundle is `Hypothesis`-grade.
- **LinkedIn 999 status** in broken-links report is a LinkedIn anti-bot response, not a real broken link — false positive.

---

## Per-URL Detail

### 1. `https://threeriversinspection.com/`
- Title 70 chars (over 60). Duplicate brand. **Fix per W-2.**
- Meta description **missing**. **Fix per C-1.**
- 1 H1 ✅. H2 count 1 (low — only "Three Rivers Gives Back" H2). Add H2 sections covering services, service area, why-PE-matters, sample reports.
- 322 words on a homepage targeting a high-intent local market — thin. Target 800+.
- Schema: WebPage, BreadcrumbList, WebSite, Organization. **Add LocalBusiness/HomeAndConstructionBusiness (C-3).**
- 7 images, 4 with `alt=null` (tracking pixels), 2 logo with empty alt. **Fix per W-8.**

### 2. `https://threeriversinspection.com/home-page/`
- Title 78 chars (over 60). Duplicate brand. **Fix per W-2.**
- Meta description **missing**.
- 1 H1, 10 H2 ✅ — best-structured page on the site.
- 1,005 words ✅.
- Add `Service` schema for "Home Inspection" with `provider` ref to Organization.
- Sample-report link is anchor-text "See a sample report" but page is orphaned (W-4).

### 3. `https://threeriversinspection.com/she-engineering-home-page-2/`
- URL slug `she-engineering-home-page-2` is poor. Rename to `/structural-engineering/` and 301 the old slug.
- Title 74 chars. Duplicate brand.
- Meta description **missing**.
- 1 H1, 7 H2 ✅.
- 334 words — thin for a service landing page. Expand with: assessment scope, sample deliverables, when you need a PE vs a home inspector, common findings (settlement, cracks, wall anchors), pricing/turnaround.
- Add `Service` schema referencing Russ Kowalik PE as `provider`.

### 4. `https://threeriversinspection.com/about-us/`
- Title 51 chars ✅.
- Meta description **missing**.
- Only 181 words — **expand per W-3**.
- NAP block in plain text: `4885-A McKnight Rd, 292 Pittsburgh 15237 / 412 331 5665`. Address looks malformed: should be `4885-A McKnight Rd, Suite 292, Pittsburgh, PA 15237`. **Add ZIP, state abbreviation, and "Suite" prefix; mark up with `PostalAddress` JSON-LD.**
- No `Person` schema for Russ — **C-4**.

### 5. `https://threeriversinspection.com/real-estate-agents/`
- Title 61 chars (1 over). Acceptable.
- Meta description **missing**.
- **0 H1** — **C-2**.
- 353 words.
- Add `Service` schema "Pre-Listing & Buyer-Side Home Inspections for Real Estate Agents".
- Add a CTA + lead-capture form for agent referrals.

---

## Methodology

LLM-first reasoning verified by 14 deterministic scripts: `fetch_page.py`, `parse_html.py`, `robots_checker.py`, `llms_txt_checker.py`, `security_headers.py`, `redirect_checker.py`, `social_meta.py`, `broken_links.py`, `internal_links.py`, `readability.py`, `entity_checker.py`, `link_profile.py`, `hreflang_checker.py`, `duplicate_content.py`. PageSpeed Insights blocked by API quota.

References applied: `quality-gates.md`, `eeat-framework.md`, `schema-types.md`, `cwv-thresholds.md`, `llm-audit-rubric.md`.
