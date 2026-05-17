<!-- Updated: 2026-05-16 -->
# False-positive patterns

A diff fires when pixels change. That is not the same thing as a regression. Below are the patterns that produce diffs without representing a real bug, and how to recognize them from the report metrics.

## Rotating hero / carousel

**Symptom.** `topQuarterPct >= 10%` while `bodyPct < 1%`. Captured by the Severity rule that downgrades these to Warning with note `"Likely rotating hero — verify"`.

**Cause.** Banner, featured-product slider, or testimonial carousel that auto-advances or randomly seeds on each load.

**Verify.** Open the test and prod screenshots in the bundle. If the only difference is hero artwork while everything below the fold is identical, this is the pattern. Capture again — most heroes cycle within 5–10 seconds.

**Fix in the build (not the report).** If you control the site, add a `?vreg=1` query flag that pins the hero to slot 1. Then re-run with `https://test.example.com/?vreg=1`.

## A/B test cookie or experiment ID

**Symptom.** Diffs across multiple pages with no obvious pattern. Sometimes flips between Critical and Pass across consecutive runs.

**Cause.** The site assigns each Playwright session to a different test cohort, returning different layouts/copy.

**Verify.** Look at the diff overlay — if the changed regions are headline copy, CTA color, or button placement, suspect this.

**Fix.** Set a fixed cookie before navigation. Either patch the script's `capturePage()` to call `context.addCookies([{ name: 'ab_bucket', value: 'control', domain, path: '/' }])` or run against an environment with experiments disabled.

## Dynamic dates and timestamps

**Symptom.** `bodyPct` between 0.1–0.8% across many pages. Often clustered near footer (copyright year) or article metadata.

**Cause.** "Last updated", relative dates ("2 hours ago"), and copyright year strings render at request time.

**Verify.** Check footer area of the diff overlay. If you see numerical digits highlighted, this is the pattern.

**Fix.** Either accept as Pass (below 1% body threshold) or mock the system clock in the build via Playwright's `clock.install()` before navigation.

## Lazy-loaded images and IntersectionObserver triggers

**Symptom.** `bodyPct` 1–4% scattered across pages. Diffs sit at predictable offsets down the page.

**Cause.** Images load only when scrolled into view. Playwright's `page.screenshot({ fullPage: true })` triggers loads as it scrolls, but timing varies — fast networks finish, slow ones don't.

**Verify.** Compare the test and prod screenshots side by side at the diff locations. Empty boxes or placeholder skeletons in one and real images in the other = lazy loading.

**Fix.** Increase the post-navigation wait in `capturePage()`. Or call `page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))` then wait `1000ms` before screenshotting. Or set `waitUntil: 'networkidle'` if not already.

## Animated elements (CSS transitions, Lottie, GIF)

**Symptom.** Top-quarter or body diffs at low single-digit %, only when animations are mid-cycle.

**Cause.** CSS `@keyframes`, Lottie animations, autoplay GIFs are still in motion when the screenshot fires.

**Verify.** Inspect the animated regions in both screenshots — if one shows the element mid-frame and the other near the end, the diff is mid-cycle noise.

**Fix.** Inject CSS before screenshot:
```js
await page.addStyleTag({ content: '*, *::before, *::after { animation: none !important; transition: none !important; }' });
```

## Font swap / FOUT

**Symptom.** `bodyPct` 0.5–1.5% across every text-heavy page on first run, near zero on subsequent runs.

**Cause.** Web fonts not loaded yet when screenshot fires — system fallback renders briefly.

**Fix.** Await fonts before screenshotting:
```js
await page.evaluate(() => document.fonts.ready);
```

## Locale / geolocation gating

**Symptom.** Whole-page diffs across all pages, often Critical-tier.

**Cause.** Site is serving different content per IP geolocation. The Playwright instance sees one region, the prod URL another.

**Fix.** Set Playwright's `--proxy-server` or override geolocation via `context.setGeolocation()`. Or run both captures from the same egress point.

## Cookie consent banners

**Symptom.** Mobile-only `topQuarterPct` 15–30%, desktop unaffected, or vice versa.

**Cause.** EU/CCPA consent banner injects on first visit. Test environment may have it suppressed; prod doesn't.

**Fix.** Either accept the banner programmatically in `capturePage()` (click the accept button), or set the consent cookie before navigation.

## When in doubt

If a diff is flagged Warning with the rotating-hero note but you're not sure, capture a third time at a different hour. Three runs converging is signal; one run flagged with `topQuarterPct >= 10%` is noise until confirmed.
