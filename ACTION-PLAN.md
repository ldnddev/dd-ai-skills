# SEO Action Plan — threeriversinspection.com

- **Source audit**: `FULL-AUDIT-REPORT.md` (2026-05-07)
- **Bundle**: `web/threeriversinspection.com-seo-audit-2026-05-07/`
- **Stack**: WordPress + Yoast SEO + Cloudflare

## Priority Buckets

| P | Effort | When | Impact |
|---|---|---|---|
| **P0** | <1 day | Week 1 | Direct ranking + AI visibility unlock |
| **P1** | 1–3 days | Weeks 2–3 | Local pack + E-E-A-T uplift |
| **P2** | Backlog | Month 2 | Content depth + UX polish |

---

## P0 — Week 1 (do first)

### 1. Write meta descriptions for all 5 pages (C-1)
**Where**: WP admin → Pages → Yoast SEO box → "Meta description"
**Length**: 140–160 chars each
**Drafts**:
- `/` → `Pittsburgh home inspections led by a licensed Professional Engineer. 15,000+ inspections completed across Southwestern PA. Schedule today.`
- `/home-page/` → `Thorough home inspections in Pittsburgh, PA. PE-trained inspectors, narrative reports designed to strengthen your buyer negotiation.`
- `/she-engineering-home-page-2/` → `Structural engineering assessments by a PA-licensed PE. Settlement, foundation cracks, wall-anchor reviews across Southwestern Pennsylvania.`
- `/about-us/` → `Three Rivers Inspections is led by Russell Kowalik, PE — Carnegie Mellon engineer with 15,000+ home inspections across Pittsburgh, PA.`
- `/real-estate-agents/` → `Trusted home inspection partner for Pittsburgh-area real estate agents. PE-led, narrative reports, fast scheduling, agent referral support.`

### 2. Fix `/real-estate-agents/` H1 (C-2)
Add at top of page body: `<h1>Inspections Built for Real Estate Agents in Southwestern PA</h1>`. Remove any duplicate H2 covering the same topic.

### 3. Unblock AI crawlers (W-1, GEO)
**Edit `robots.txt`** — remove these `Disallow: /` lines:
```
User-agent: GPTBot       # remove Disallow: /
User-agent: ClaudeBot    # remove Disallow: /
User-agent: Google-Extended
User-agent: Applebot-Extended
User-agent: PerplexityBot # add explicit Allow if not already
```
Keep blocks only for crawlers you intentionally want excluded. For a local-service biz courting AI-assistant referrals, all major LLM crawlers should be allowed.

### 4. Add `og:image` (C-6)
WP admin → Yoast → Social → Facebook → upload 1200×630 default OG image. Same image works for Twitter Card.

### 5. Fix sitemap protocol (C-5)
WP admin → Settings → General → confirm Site Address (URL) and WordPress Address (URL) both `https://threeriversinspection.com`. Save. Yoast → Tools → File editor → flush. Re-fetch `https://threeriversinspection.com/sitemap_index.xml` — every `<loc>` must be `https://`.

### 6. Rewrite all 5 page titles (W-2)
Replace the all-caps "THREE RIVERS — X PAGE — Three Rivers Inspections and Engineering" template. Use the per-page rewrites in FULL-AUDIT-REPORT W-2.

### 7. Fix broken email-protection link (W-7)
Cloudflare dashboard → Scrape Shield → toggle Email Address Obfuscation **off** (or fix the static `[email protected]` anchor in the menu/footer to a proper `mailto:`).

---

## P1 — Weeks 2–3

### 8. Add `HomeAndConstructionBusiness` schema (C-3)
Use Yoast → Site → Knowledge Graph, set Organization → switch to LocalBusiness subtype. If Yoast lacks the subtype, add a custom JSON-LD block via a snippet plugin or `functions.php`:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "HomeAndConstructionBusiness",
  "@id": "https://threeriversinspection.com/#localbusiness",
  "name": "Three Rivers Inspections and Engineering",
  "url": "https://threeriversinspection.com/",
  "image": "https://threeriversinspection.com/wp-content/uploads/2022/02/ThreeRivInspectEngin_logo_color_nobkgnd.png",
  "telephone": "+1-412-331-5665",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "4885-A McKnight Rd, Suite 292",
    "addressLocality": "Pittsburgh",
    "addressRegion": "PA",
    "postalCode": "15237",
    "addressCountry": "US"
  },
  "geo": { "@type": "GeoCoordinates", "latitude": 40.5246, "longitude": -80.0223 },
  "openingHoursSpecification": [{
    "@type": "OpeningHoursSpecification",
    "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
    "opens": "09:00", "closes": "17:00"
  }],
  "areaServed": "Southwestern Pennsylvania",
  "priceRange": "$$",
  "sameAs": [
    "https://www.facebook.com/ThreeRiversInspection",
    "https://www.linkedin.com/in/russell-kowalik-23b8058/"
  ]
}
</script>
```

### 9. Add `Person` schema for Russell Kowalik (C-4)
On `/about-us/`:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Person",
  "@id": "https://threeriversinspection.com/about-us/#russ-kowalik",
  "name": "Russell Kowalik, PE",
  "jobTitle": "Owner, Lead Engineer & Home Inspector Trainer",
  "worksFor": { "@id": "https://threeriversinspection.com/#localbusiness" },
  "alumniOf": "Carnegie Mellon University",
  "hasCredential": [
    { "@type": "EducationalOccupationalCredential", "name": "Professional Engineer (Pennsylvania)" }
  ],
  "sameAs": ["https://www.linkedin.com/in/russell-kowalik-23b8058/"]
}
</script>
```
Add similar `Person` blocks for Natalie Hanchett and Max Echard.

### 10. Expand About page to 600–900 words (W-3)
Add per-team-member detail: PE license number, inspection count, certifications (ASHI / InterNACHI / state license), notable structural projects, headshots with descriptive `alt`. Restate NAP with city/state/zip.

### 11. Link to orphan pages (W-4)
Add visible CTAs on `/`, `/home-page/`, `/she-engineering-home-page-2/`, `/real-estate-agents/`:
- "📄 See a sample home inspection report" → `/three-rivers-sample-home-inspection-report/`
- "📐 View a sample engineering report" → `/engineering-report-sample/`

### 12. Rename engineering page slug (W per-URL p3)
Change `/she-engineering-home-page-2/` → `/structural-engineering/`. Add 301 in Yoast → Redirects.

### 13. Fix logo `alt` (W-8)
Theme/header.php or theme customizer: `alt="Three Rivers Inspections and Engineering — Pittsburgh, PA"`.

### 14. Fix address formatting (per-URL p4)
On About page replace `4885-A McKnight Rd, 292 Pittsburgh 15237` with `4885-A McKnight Rd, Suite 292 · Pittsburgh, PA 15237`.

---

## P2 — Month 2 (depth)

### 15. Create `/llms.txt` (W-6)
File served at `https://threeriversinspection.com/llms.txt`:
```
# Three Rivers Inspections and Engineering
> PE-led home inspections and structural engineering across Southwestern Pennsylvania.

## About
- Owner: Russell Kowalik, PE (Carnegie Mellon, PA Professional Engineer)
- Address: 4885-A McKnight Rd, Suite 292, Pittsburgh, PA 15237
- Phone: 412-331-5665
- Hours: Mon–Fri 9:00–17:00 ET; Sat–Sun by appointment

## Key pages
- [Home Inspections](https://threeriversinspection.com/home-page/)
- [Structural Engineering](https://threeriversinspection.com/structural-engineering/)
- [About](https://threeriversinspection.com/about-us/)
- [Real Estate Agents](https://threeriversinspection.com/real-estate-agents/)
- [Sample Home Inspection Report](https://threeriversinspection.com/three-rivers-sample-home-inspection-report/)
- [Sample Engineering Report](https://threeriversinspection.com/engineering-report-sample/)
```

### 16. Add CSP + Permissions-Policy (W-5)
Cloudflare → Rules → Transform Rules → Modify Response Header:
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self' 'unsafe-inline' https://www.google-analytics.com https://connect.facebook.net; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; report-uri /csp-report` (tune after observing reports for 1–2 weeks, then promote to enforce).

### 17. Run PageSpeed Insights with API key
Get a free key at https://developers.google.com/speed/docs/insights/v5/get-started, then re-run:
```bash
python3 scripts/pagespeed.py https://threeriversinspection.com/ --strategy mobile --api-key $PSI_KEY
```
Address LCP/INP/CLS findings (likely image lazy-loading, hero image dimensions, render-blocking Yoast/Cloudflare scripts).

### 18. Improve readability (W-9)
Edit homepage and About to shorten sentences (target ≤20 words avg). Replace passive phrasing. Aim Flesch 60+.

### 19. Sitemap hygiene (W-10)
Yoast → flush. If author archive is noindex, exclude `author-sitemap.xml`. If kept, ensure regen happens on publish.

### 20. Add `Service` schema per service page
Add `Service` JSON-LD on `/home-page/`, `/she-engineering-home-page-2/`, `/real-estate-agents/`, with `provider` referring to the LocalBusiness `@id`.

### 21. Expand homepage to 800+ words
Cover: services overview, service area (cities/counties), why-a-PE-matters, sample reports, testimonials, FAQ. Pair with internal links to all P1/P2 destinations.

### 22. Set up Google Business Profile + Search Console
If not already, claim GBP, link to website, add business hours, photos, and request reviews. Connect Search Console (HTTPS property) to monitor index coverage and CWV field data.

---

## Verification After Implementation

| Check | Command | Pass criterion |
|---|---|---|
| Meta desc present | `python3 scripts/parse_html.py` | All 5 pages → `meta_description` length 120–160 |
| H1 fixed | `grep -c '<h1' p5.html` | ≥1 |
| Schema | https://validator.schema.org/ | No errors; LocalBusiness + Person nodes present |
| Sitemap | `curl https://.../sitemap_index.xml` | All `<loc>` start with `https://` |
| AI crawlers | `python3 scripts/robots_checker.py` | `Allow` (or no `Disallow: /`) for GPTBot, ClaudeBot, Google-Extended |
| OG image | `python3 scripts/social_meta.py` | Score ≥80, og:image present |
| Headers | `python3 scripts/security_headers.py` | Score ≥90, CSP + Permissions-Policy present |
| Broken links | `python3 scripts/broken_links.py` | 0 internal 4xx |
| CWV | `python3 scripts/pagespeed.py --api-key …` | LCP <2.5s, INP <200ms, CLS <0.1 (mobile) |

Re-run `python3 scripts/generate_report.py https://threeriversinspection.com/` after P0+P1 to confirm overall score moves from 65 → 85+.
