# dd-site-speed Issue Insights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured What / Why / How insights to every speed remediation task across all client deliverables (dashboard expandable rows, Markdown, DOCX, CSV), and make `pagespeed.py` default to `PAGESPEED_API_KEY` / `PSI_API_KEY`.

**Architecture:** Expand the in-code `PLAYBOOK` dict in `generate_report.py` with `what` / `why` / `how` per opportunity ID. `build_task_rows()` resolves insights via a small helper (playbook first, PSI description + generic fallbacks for unknown IDs). All renderers (MD, DOCX, CSV, HTML) consume those fields. Dashboard template gains expandable detail rows with keyboard-accessible toggles.

**Tech Stack:** Python 3 stdlib only (`unittest`, `argparse`, `csv`, `html`, `json`, `os`, `pathlib`). HTML/CSS/JS in `templates/dashboard.html`. No pip install.

**Spec:** `docs/superpowers/specs/2026-07-16-dd-site-speed-issue-insights-design.md`

---

## File structure

| Path | Role |
|------|------|
| `custom/dd-site-speed-audit/scripts/generate_report.py` | PLAYBOOK + `resolve_insights()` + task rows + all renderers |
| `custom/dd-site-speed-audit/scripts/test_generate_report.py` | Unit tests (TDD) |
| `custom/dd-site-speed-audit/templates/dashboard.html` | Expandable insight rows + JS |
| `custom/dd-site-speed-audit/scripts/pagespeed.py` | Env API key default on CLI |
| `custom/dd-site-speed-audit/skills/dd-site-speed/references/optimization-playbook.md` | Doc sync (What/Why/How pattern) |
| `custom/dd-site-speed-audit/skills/dd-site-speed/SKILL.md` | One-line deliverables note |
| `custom/dd-site-speed-audit/README.md` | Features bullet for insights |

**Conventions:**

- Work in `custom/dd-site-speed-audit/`
- Run tests: `python3 scripts/test_generate_report.py` from that directory
- Keep commits small and focused per task

---

### Task 1: `resolve_insights()` helper + failing tests

**Files:**
- Modify: `custom/dd-site-speed-audit/scripts/generate_report.py`
- Modify: `custom/dd-site-speed-audit/scripts/test_generate_report.py`

- [ ] **Step 1: Write failing tests for insight resolution**

Add to `test_generate_report.py` (import `resolve_insights` once it exists; for now import will fail until Step 3):

```python
from generate_report import (  # noqa: E402
    build_task_rows,
    generate_all,
    resolve_insights,
    score_label,
    _rating_badge,
    _score_bar_mod,
    _render_score_bars,
)


class TestResolveInsights(unittest.TestCase):
    def test_known_id_uses_playbook(self):
        what, why, how = resolve_insights(
            "render-blocking-resources",
            psi_description="PSI says something",
            metric="LCP",
        )
        self.assertTrue(len(what) > 20)
        self.assertTrue(len(why) > 20)
        self.assertTrue(len(how) > 20)
        self.assertNotIn("PSI says something", what)

    def test_unknown_id_falls_back_to_psi_description(self):
        what, why, how = resolve_insights(
            "totally-unknown-audit-xyz",
            psi_description="Custom PSI description about widgets.",
            metric="TBT",
        )
        self.assertIn("widgets", what)
        self.assertIn("TBT", why)
        self.assertTrue(len(how) > 10)

    def test_unknown_id_without_psi_uses_generic_what(self):
        what, why, how = resolve_insights(
            "totally-unknown-audit-xyz",
            psi_description="",
            metric="Performance",
        )
        self.assertIn("Lighthouse", what)
        self.assertIn("performance score", why.lower())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py TestResolveInsights -v
```

Expected: FAIL with `ImportError: cannot import name 'resolve_insights'` (or similar).

- [ ] **Step 3: Implement `resolve_insights` and minimal PLAYBOOK fields**

In `generate_report.py`, add this helper **after** the existing `PLAYBOOK` dict (before `load_brand_config`). For this task, only ensure the helper works; full prose is Task 2. Temporarily add `what`/`why` keys only for `render-blocking-resources` if needed so known-id test passes—or implement full dict in Task 2 and use stub text here.

```python
def resolve_insights(
    opportunity_id: str,
    *,
    psi_description: str = "",
    metric: str = "Performance",
    playbook_entry: dict | None = None,
) -> tuple[str, str, str]:
    """Return (what, why, how) for an opportunity or CWV task id.

    Prefer curated PLAYBOOK fields; fall back to PSI description / generics.
    """
    play = playbook_entry if playbook_entry is not None else PLAYBOOK.get(opportunity_id, {})
    what = (play.get("what") or "").strip()
    why = (play.get("why") or "").strip()
    how = (play.get("how") or "").strip()

    if not what:
        desc = (psi_description or "").strip()
        if len(desc) > 400:
            desc = desc[:397] + "..."
        what = desc or "Lighthouse flagged this opportunity during the performance audit."

    if not why:
        why = (
            f"Improves {metric} and the overall performance score when addressed."
        )

    if not how:
        how = "Review the Lighthouse opportunity and apply the documented fix."

    return what, why, how
```

Also ensure `PLAYBOOK["render-blocking-resources"]` has non-empty `what` and `why` (can use final prose from Task 2).

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py TestResolveInsights -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add custom/dd-site-speed-audit/scripts/generate_report.py \
        custom/dd-site-speed-audit/scripts/test_generate_report.py
git commit -m "feat(dd-site-speed): add resolve_insights helper with fallbacks"
```

---

### Task 2: Expand PLAYBOOK with what / why / how for all IDs

**Files:**
- Modify: `custom/dd-site-speed-audit/scripts/generate_report.py` (`PLAYBOOK` dict ~lines 32–183)

- [ ] **Step 1: Replace each PLAYBOOK entry** with the shape below. Keep existing `owner`, `effort`, `metric`, and upgrade `how` text only if improving clarity. Add `what` and `why` for every key.

Use this full dictionary (replace the entire `PLAYBOOK = { ... }` block):

```python
PLAYBOOK = {
    "render-blocking-resources": {
        "owner": "Frontend Development",
        "what": "Stylesheets or scripts block the browser from painting the first screen until they finish downloading and executing.",
        "why": "Increases Largest Contentful Paint and First Contentful Paint, delaying when users see primary content and lowering the performance score.",
        "how": "Defer non-critical CSS/JS, inline critical CSS, use async/defer on scripts, or split bundles so above-the-fold content is not blocked.",
        "effort": "M",
        "metric": "LCP",
    },
    "unused-javascript": {
        "owner": "Frontend Development",
        "what": "The page downloads and parses JavaScript that is never executed on the initial route or viewport.",
        "why": "Extra JS raises Total Blocking Time and can hurt Interaction to Next Paint by occupying the main thread.",
        "how": "Code-split routes, tree-shake, remove dead libraries, and delay non-critical third-party scripts until after interaction.",
        "effort": "M",
        "metric": "TBT",
    },
    "unused-css-rules": {
        "owner": "Frontend Development",
        "what": "Stylesheets include many rules that do not apply to elements on this page.",
        "why": "Larger CSS delays render and competes with critical path resources that affect LCP.",
        "how": "Purge unused CSS, split critical vs deferred stylesheets, avoid loading full design-system CSS on every page.",
        "effort": "M",
        "metric": "LCP",
    },
    "uses-responsive-images": {
        "owner": "Frontend / CMS",
        "what": "Images are served at larger pixel dimensions than the display size needs (especially on mobile).",
        "why": "Oversized images slow download and decode, often becoming the LCP element bottleneck.",
        "how": "Serve correctly sized images with srcset/sizes; avoid shipping desktop-resolution assets to mobile viewports.",
        "effort": "S",
        "metric": "LCP",
    },
    "modern-image-formats": {
        "owner": "Frontend / CMS",
        "what": "Photographic or complex images use older formats (JPEG/PNG) instead of AVIF or WebP.",
        "why": "Modern formats are smaller at similar quality, cutting bytes and improving LCP for image-heavy pages.",
        "how": "Convert hero and content images to AVIF/WebP with fallbacks; use a CDN image transform when available.",
        "effort": "S",
        "metric": "LCP",
    },
    "uses-webp-images": {
        "owner": "Frontend / CMS",
        "what": "Images that could be WebP/AVIF are still served as JPEG or PNG.",
        "why": "Smaller image payloads reduce LCP resource load duration and bandwidth cost.",
        "how": "Serve WebP/AVIF derivatives for photographic content; keep PNG only for UI icons that need transparency fidelity.",
        "effort": "S",
        "metric": "LCP",
    },
    "offscreen-images": {
        "owner": "Frontend Development",
        "what": "Images below the fold load immediately instead of when they approach the viewport.",
        "why": "Early loading of offscreen media steals bandwidth from the LCP resource and critical scripts.",
        "how": "Lazy-load below-the-fold images; never lazy-load the LCP/hero image. Use loading=\"lazy\" + decoding=\"async\" for others.",
        "effort": "S",
        "metric": "LCP",
    },
    "priority-hints": {
        "owner": "Frontend Development",
        "what": "The browser is not told which resource is the LCP candidate, so it may schedule less important work first.",
        "why": "Missing priority on the LCP image increases resource load delay and hurts LCP.",
        "how": "Add fetchpriority=\"high\" (and optionally preload) for the LCP image; demote non-critical resources.",
        "effort": "S",
        "metric": "LCP",
    },
    "server-response-time": {
        "owner": "Backend / DevOps",
        "what": "The origin or CDN takes too long to start returning the HTML document (high TTFB).",
        "why": "Everything else waits on the first byte; high TTFB directly delays FCP and LCP.",
        "how": "Cache HTML at the edge, optimize TTFB (DB queries, PHP/app workers), reduce redirects, enable full-page cache where safe.",
        "effort": "L",
        "metric": "TTFB",
    },
    "redirects": {
        "owner": "DevOps / SEO",
        "what": "The URL requires one or more HTTP redirects before the final document is reached.",
        "why": "Each hop adds round-trip latency to TTFB and can delay every subsequent metric.",
        "how": "Collapse multi-hop redirects to a single hop; fix http→https and www/non-www chains.",
        "effort": "S",
        "metric": "TTFB",
    },
    "uses-text-compression": {
        "owner": "DevOps",
        "what": "Text assets (HTML, CSS, JS, JSON, SVG) are not compressed with Brotli or gzip over the wire.",
        "why": "Uncompressed text increases transfer size and slows LCP for document and stylesheet loads.",
        "how": "Enable Brotli or gzip for HTML/CSS/JS/JSON/SVG at the origin or CDN.",
        "effort": "S",
        "metric": "LCP",
    },
    "uses-long-cache-ttl": {
        "owner": "DevOps",
        "what": "Static assets are cached for a short time or not at all, forcing repeat downloads on return visits.",
        "why": "Poor caching hurts repeat-view LCP and increases origin load (field data and lab cold-cache still matter differently).",
        "how": "Set long Cache-Control for fingerprinted static assets; use short TTL or revalidation for HTML.",
        "effort": "S",
        "metric": "LCP",
    },
    "uses-rel-preconnect": {
        "owner": "Frontend Development",
        "what": "Critical third-party origins are discovered late, so TCP/TLS setup happens on the critical path.",
        "why": "Late connections delay fonts, CDNs, or tags that block or compete with LCP.",
        "how": "Add preconnect/dns-prefetch for critical third-party origins (fonts, CDNs, analytics) used early in load.",
        "effort": "S",
        "metric": "LCP",
    },
    "font-display": {
        "owner": "Frontend / Design",
        "what": "Web fonts block or delay text rendering because font-display is not optimized.",
        "why": "Invisible or late text affects perceived performance and can contribute to layout shift when fonts swap.",
        "how": "Use font-display: swap (or optional) and subset web fonts; preload the primary text face.",
        "effort": "S",
        "metric": "LCP",
    },
    "bootup-time": {
        "owner": "Frontend Development",
        "what": "JavaScript takes substantial main-thread time to parse, compile, and evaluate on load.",
        "why": "Long bootup delays interactivity (INP/TBT) and can postpone rendering work.",
        "how": "Reduce main-thread JS parse/compile cost: smaller bundles, less polyfill, delay non-critical scripts.",
        "effort": "M",
        "metric": "INP",
    },
    "mainthread-work-breakdown": {
        "owner": "Frontend Development",
        "what": "The main thread spends too much time on script, style, layout, or other work during load or interaction.",
        "why": "Long tasks block input handling and raise Interaction to Next Paint.",
        "how": "Break long tasks, move heavy work off the main thread, reduce style/layout thrash on interaction.",
        "effort": "M",
        "metric": "INP",
    },
    "third-party-summary": {
        "owner": "Marketing + Frontend",
        "what": "Third-party scripts (tags, embeds, widgets) consume significant network and main-thread time.",
        "why": "Third parties often dominate TBT/INP regressions and are easy to overlook in app code reviews.",
        "how": "Audit tags; load non-essential third parties after consent/idle; self-host critical scripts when possible.",
        "effort": "M",
        "metric": "TBT",
    },
    "dom-size": {
        "owner": "Frontend Development",
        "what": "The document has a very large number of DOM nodes or deep nesting.",
        "why": "Large DOMs slow style/layout and make interactions more expensive (INP risk).",
        "how": "Reduce DOM depth/node count; paginate large lists; avoid mega-menus with thousands of nodes.",
        "effort": "M",
        "metric": "INP",
    },
    "total-byte-weight": {
        "owner": "Frontend Development",
        "what": "The total transfer size of the page is high across HTML, CSS, JS, media, and third parties.",
        "why": "Heavy pages load slowly on mobile networks and drag down LCP and overall score.",
        "how": "Cut total page weight: compress media, split bundles, remove unused libraries and duplicate assets.",
        "effort": "M",
        "metric": "LCP",
    },
    "legacy-javascript": {
        "owner": "Frontend Development",
        "what": "Bundles include polyfills or transforms for browsers the audience no longer needs.",
        "why": "Legacy JS increases download and parse cost without helping modern users (TBT).",
        "how": "Ship modern ES builds to evergreen browsers; drop unnecessary polyfills via differential serving.",
        "effort": "M",
        "metric": "TBT",
    },
    "unminified-css": {
        "owner": "Frontend Development",
        "what": "CSS is shipped with comments and whitespace that production builds should remove.",
        "why": "Unminified CSS increases transfer size and can delay render.",
        "how": "Minify CSS in production builds.",
        "effort": "S",
        "metric": "LCP",
    },
    "unminified-javascript": {
        "owner": "Frontend Development",
        "what": "JavaScript is shipped without minification in production.",
        "why": "Larger JS files cost more download and parse time (TBT).",
        "how": "Minify JS in production builds.",
        "effort": "S",
        "metric": "TBT",
    },
    "efficient-animated-content": {
        "owner": "Design + Frontend",
        "what": "Large animated GIFs or inefficient motion assets are used where video or CSS would be lighter.",
        "why": "Heavy animations inflate page weight and can dominate LCP when used above the fold.",
        "how": "Replace large GIFs with video (muted, playsinline) or CSS animation; compress motion assets.",
        "effort": "S",
        "metric": "LCP",
    },
    "unsized-images": {
        "owner": "Frontend Development",
        "what": "Images lack explicit width/height (or aspect-ratio), so the browser cannot reserve space before load.",
        "why": "When images load, surrounding content shifts—raising Cumulative Layout Shift.",
        "how": "Set explicit width/height (or aspect-ratio) on images to prevent CLS.",
        "effort": "S",
        "metric": "CLS",
    },
    "layout-shift-elements": {
        "owner": "Frontend / Design",
        "what": "Specific elements (ads, embeds, fonts, injected banners) move content after initial render.",
        "why": "Layout shifts harm CLS and make the page feel unstable while reading or tapping.",
        "how": "Reserve space for ads/embeds/fonts/images; avoid inserting content above existing content without skeleton space.",
        "effort": "M",
        "metric": "CLS",
    },
    # Synthetic CWV tasks (ids produced by build_task_rows)
    "cwv-lcp": {
        "owner": "Frontend Development",
        "what": "Largest Contentful Paint is slower than recommended thresholds for a good user experience.",
        "why": "LCP is a Core Web Vital; poor LCP means users wait too long for the main content to appear.",
        "how": "Optimize LCP element discovery, size, and server response: prioritize the hero resource, reduce TTFB, and remove render-blocking work.",
        "effort": "M",
        "metric": "LCP",
    },
    "cwv-inp": {
        "owner": "Frontend Development",
        "what": "Interaction to Next Paint is slower than recommended, so clicks and taps feel laggy.",
        "why": "INP is a Core Web Vital for responsiveness; poor INP frustrates users during interaction.",
        "how": "Reduce main-thread long tasks and heavy event handlers; break up work and defer non-essential scripts.",
        "effort": "M",
        "metric": "INP",
    },
    "cwv-cls": {
        "owner": "Frontend / Design",
        "what": "Cumulative Layout Shift is higher than recommended, so the page layout moves unexpectedly.",
        "why": "CLS is a Core Web Vital for visual stability; shifts cause mis-taps and a jarring experience.",
        "how": "Reserve space for media/embeds and avoid late-injected content; size images and ads before load.",
        "effort": "M",
        "metric": "CLS",
    },
}
```

- [ ] **Step 2: Smoke-check resolve_insights still passes**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py TestResolveInsights -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add custom/dd-site-speed-audit/scripts/generate_report.py
git commit -m "feat(dd-site-speed): expand PLAYBOOK with what/why/how insights"
```

---

### Task 3: Wire insights into `build_task_rows`

**Files:**
- Modify: `custom/dd-site-speed-audit/scripts/generate_report.py` (`build_task_rows`)
- Modify: `custom/dd-site-speed-audit/scripts/test_generate_report.py`

- [ ] **Step 1: Write failing tests for task row insights**

```python
class TestTaskInsights(unittest.TestCase):
    def test_opportunity_rows_include_what_why_how(self):
        rows = build_task_rows(_fixture())
        rbr = next(r for r in rows if r["opportunity_id"] == "render-blocking-resources")
        self.assertIn("block", rbr["what"].lower())
        self.assertTrue(len(rbr["why"]) > 20)
        self.assertIn("Defer", rbr["how"])  # playbook how
        self.assertIn("WordPress", rbr["how"])  # stack tip still appended

    def test_unknown_opportunity_uses_psi_description(self):
        data = _fixture()
        data["pages"][0]["strategies"]["mobile"]["opportunities"].append({
            "id": "brand-new-audit-999",
            "title": "Brand new audit",
            "description": "Widgets are not optimized for speed.",
            "savings_ms": 900,
            "savings_bytes": 0,
            "display": "0.9s",
        })
        rows = build_task_rows(data)
        row = next(r for r in rows if r["opportunity_id"] == "brand-new-audit-999")
        self.assertIn("Widgets", row["what"])
        self.assertTrue(row["why"])
        self.assertTrue(row["how"])

    def test_cwv_tasks_use_curated_insights(self):
        # Fixture home page has poor LCP; may already have LCP-tagged opps.
        # Force a CWV-only page with poor INP and no INP-metric opportunities.
        data = {
            "metadata": {"stack_labels": []},
            "pages": [{
                "page_url": "https://example.com/cwv",
                "page_slug": "cwv",
                "stack": {"labels": []},
                "strategies": {
                    "mobile": {
                        "strategy": "mobile",
                        "performance_score": 40,
                        "metrics": {
                            "INP": {
                                "value": 400,
                                "unit": "ms",
                                "label": "Interaction to Next Paint",
                                "rating": "poor",
                                "source": "lab",
                            },
                        },
                        "opportunities": [],
                        "error": None,
                    },
                    "desktop": {
                        "strategy": "desktop",
                        "performance_score": 50,
                        "metrics": {},
                        "opportunities": [],
                        "error": None,
                    },
                },
                "error": None,
            }],
        }
        rows = build_task_rows(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["opportunity_id"], "cwv-inp")
        self.assertIn("Interaction", rows[0]["what"])
        self.assertIn("Core Web Vital", rows[0]["why"])
```

- [ ] **Step 2: Run tests — expect FAIL** (rows lack `what`/`why` or wrong CWV how)

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py TestTaskInsights -v
```

- [ ] **Step 3: Update opportunity branch in `build_task_rows`**

Replace the block that sets `how` / builds the row (~lines 383–417) so it uses `resolve_insights` and stores all three fields. Pattern:

```python
        for opp in opps:
            oid = opp.get("id") or "unknown"
            play = PLAYBOOK.get(oid, {})
            savings_ms = int(opp.get("savings_ms") or 0)
            savings_bytes = int(opp.get("savings_bytes") or 0)
            sev = severity_from_savings(savings_ms, savings_bytes)
            tip = stack_tips(labels, oid)
            owner = play.get("owner") or "Frontend Development"
            metric = play.get("metric") or "Performance"
            effort = play.get("effort") or "M"
            what, why, how = resolve_insights(
                oid,
                psi_description=opp.get("description") or "",
                metric=metric,
                playbook_entry=play,
            )
            if tip:
                how = f"{how} {tip}"
            est = format_ms(savings_ms) if savings_ms else format_bytes(savings_bytes) or "—"
            rows.append({
                "task_id": f"SPEED-{idx:03d}",
                "page_url": page_url,
                "page_slug": page_slug,
                "priority": priority_from_severity(sev),
                "severity": sev,
                "title": opp.get("title") or oid,
                "opportunity_id": oid,
                "metric": metric,
                "est_savings": est,
                "est_savings_ms": savings_ms,
                "est_savings_bytes": savings_bytes,
                "effort": effort,
                "owner": owner,
                "stack": ", ".join(labels[:4]),
                "strategy": opp.get("strategy") or "mobile",
                "what": what,
                "why": why,
                "how": how,
                "evidence": opp.get("display") or opp.get("description", "")[:180],
                "timeline": timeline_from_severity(sev),
                "status": "Open",
            })
            idx += 1
```

- [ ] **Step 4: Update CWV metric branch**

Replace the CWV row builder so it uses playbook ids `cwv-lcp` / `cwv-inp` / `cwv-cls`:

```python
        for mname, _legacy_note in (
            ("LCP", ""),
            ("INP", ""),
            ("CLS", ""),
        ):
            metric = metrics.get(mname) or {}
            rating = (metric.get("rating") or "").lower()
            if rating not in ("poor", "slow", "needs-improvement", "average"):
                continue
            if any(r["page_url"] == page_url and r["metric"] == mname for r in rows):
                continue
            sev = "Critical" if rating in ("poor", "slow") else "High"
            value = metric.get("value")
            unit = metric.get("unit") or ""
            display = f"{value}{unit}" if unit != "ms" else format_ms(value)
            oid = f"cwv-{mname.lower()}"
            play = PLAYBOOK.get(oid, {})
            what, why, how = resolve_insights(
                oid,
                psi_description="",
                metric=mname,
                playbook_entry=play,
            )
            tip = stack_tips(labels, "")
            if tip:
                how = f"{how} {tip}".strip()
            rows.append({
                "task_id": f"SPEED-{idx:03d}",
                "page_url": page_url,
                "page_slug": page_slug,
                "priority": priority_from_severity(sev),
                "severity": sev,
                "title": f"Improve {mname} ({display}, {rating})",
                "opportunity_id": oid,
                "metric": mname,
                "est_savings": "—",
                "est_savings_ms": 0,
                "est_savings_bytes": 0,
                "effort": play.get("effort") or "M",
                "owner": play.get("owner") or "Frontend Development",
                "stack": ", ".join(labels[:4]),
                "strategy": primary.get("strategy") or "mobile",
                "what": what,
                "why": why,
                "how": how,
                "evidence": f"{mname}={display} rating={rating} source={metric.get('source', 'lab')}",
                "timeline": timeline_from_severity(sev),
                "status": "Open",
            })
            idx += 1
```

- [ ] **Step 5: Run tests**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py TestTaskInsights test_task_rows_prioritized -v
```

Expected: PASS. (Existing `test_task_rows_prioritized` still checks WordPress in `how`.)

- [ ] **Step 6: Commit**

```bash
git add custom/dd-site-speed-audit/scripts/generate_report.py \
        custom/dd-site-speed-audit/scripts/test_generate_report.py
git commit -m "feat(dd-site-speed): attach what/why/how to every task row"
```

---

### Task 4: CSV + Markdown deliverables

**Files:**
- Modify: `custom/dd-site-speed-audit/scripts/generate_report.py` (`write_csv`, `generate_report_md`, `generate_action_plan`)
- Modify: `custom/dd-site-speed-audit/scripts/test_generate_report.py`

- [ ] **Step 1: Extend `test_full_bundle` (or add new test)**

```python
    def test_insights_in_markdown_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bundle"
            generate_all(_fixture(), out)
            csv_text = (out / "tasks.csv").read_text(encoding="utf-8")
            self.assertIn("what", csv_text.splitlines()[0])
            self.assertIn("why", csv_text.splitlines()[0])
            report = (out / "SPEED-AUDIT-REPORT.md").read_text(encoding="utf-8")
            plan = (out / "ACTION-PLAN.md").read_text(encoding="utf-8")
            for doc in (report, plan):
                self.assertIn("What it means", doc)
                self.assertIn("Why it matters", doc)
                self.assertIn("How to fix", doc)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py TestGenerateReport.test_insights_in_markdown_and_csv -v
```

- [ ] **Step 3: Update `write_csv` fieldnames**

```python
def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "task_id", "priority", "severity", "title",
        "what", "why", "how",
        "metric", "est_savings", "est_savings_ms", "effort", "owner",
        "stack", "page_url", "page_slug", "strategy", "timeline",
        "evidence", "opportunity_id", "status",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
```

- [ ] **Step 4: Update `generate_report_md` task loop**

Replace the findings bullets for each row with:

```python
            lines.extend([
                f"### {row['task_id']} — {row['title']}",
                f"- **Priority:** {row['priority']} ({row['severity']})",
                f"- **Page:** {row['page_url']}",
                f"- **Metric:** {row['metric']}",
                f"- **Est. savings:** {row['est_savings']}",
                f"- **Effort / Owner:** {row['effort']} / {row['owner']}",
                f"- **Stack context:** {row['stack'] or 'n/a'}",
                f"- **What it means:** {row.get('what') or ''}",
                f"- **Why it matters:** {row.get('why') or ''}",
                f"- **How to fix:** {row.get('how') or ''}",
                f"- **Evidence:** {row['evidence']}",
                "",
            ])
```

- [ ] **Step 5: Update `generate_action_plan` task loop**

```python
            lines.extend([
                f"### {row['task_id']} — {row['title']}",
                f"- Priority: {row['priority']} ({row['severity']})",
                f"- Page: {row['page_url']}",
                f"- Metric: {row['metric']}",
                f"- Est. savings: {row['est_savings']}",
                f"- Owner: {row['owner']}",
                f"- Timeline: {row['timeline']}",
                f"- Effort: {row['effort']}",
                f"- **What it means:** {row.get('what') or ''}",
                f"- **Why it matters:** {row.get('why') or ''}",
                f"- **How to fix:** {row.get('how') or ''}",
                "",
            ])
```

- [ ] **Step 6: Run tests**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py -v
```

Expected: all PASS except possibly HTML-specific tests not yet added.

- [ ] **Step 7: Commit**

```bash
git add custom/dd-site-speed-audit/scripts/generate_report.py \
        custom/dd-site-speed-audit/scripts/test_generate_report.py
git commit -m "feat(dd-site-speed): include insights in Markdown reports and CSV"
```

---

### Task 5: DOCX deliverables

**Files:**
- Modify: `custom/dd-site-speed-audit/scripts/generate_report.py` (`build_client_docx`, `build_action_plan_docx`)
- Modify: `custom/dd-site-speed-audit/scripts/test_generate_report.py`

- [ ] **Step 1: Add test that DOCX XML contains insight labels**

```python
    def test_insights_in_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bundle"
            generate_all(_fixture(), out)
            from zipfile import ZipFile
            for name in ("SPEED-CLIENT-REPORT.docx", "ACTION-PLAN.docx"):
                with ZipFile(out / name) as zf:
                    xml = zf.read("word/document.xml").decode("utf-8")
                self.assertIn("What it means", xml)
                self.assertIn("Why it matters", xml)
                self.assertIn("How to fix", xml)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py TestGenerateReport.test_insights_in_docx -v
```

- [ ] **Step 3: Update DOCX builders**

In `build_client_docx`, replace the per-row how-only paragraphs:

```python
        for row in rows:
            paras.append(
                f"{row['task_id']} | {row['priority']} | {row['severity']} | {row['title']} | "
                f"Savings: {row['est_savings']} | Owner: {row['owner']}"
            )
            paras.append(f"What it means: {(row.get('what') or '')[:500]}")
            paras.append(f"Why it matters: {(row.get('why') or '')[:500]}")
            paras.append(f"How to fix: {(row.get('how') or '')[:500]}")
            paras.append(" ")
```

In `build_action_plan_docx`:

```python
    for row in rows:
        paras.append(
            f"{row['task_id']} [{row['priority']}] {row['title']} — "
            f"{row['timeline']} — {row['owner']} — effort {row['effort']}"
        )
        paras.append(f"What it means: {(row.get('what') or '')[:600]}")
        paras.append(f"Why it matters: {(row.get('why') or '')[:600]}")
        paras.append(f"How to fix: {(row.get('how') or '')[:600]}")
        paras.append(" ")
```

- [ ] **Step 4: Run full suite**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom/dd-site-speed-audit/scripts/generate_report.py \
        custom/dd-site-speed-audit/scripts/test_generate_report.py
git commit -m "feat(dd-site-speed): include insights in client and action-plan DOCX"
```

---

### Task 6: Dashboard expandable insight rows

**Files:**
- Modify: `custom/dd-site-speed-audit/scripts/generate_report.py` (`_render_task_rows`)
- Modify: `custom/dd-site-speed-audit/templates/dashboard.html`
- Modify: `custom/dd-site-speed-audit/scripts/test_generate_report.py`

- [ ] **Step 1: Write failing HTML test**

```python
    def test_dashboard_expandable_insights(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bundle"
            generate_all(_fixture(), out)
            html_text = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('aria-expanded="false"', html_text)
            self.assertIn("What it means", html_text)
            self.assertIn("Why it matters", html_text)
            self.assertIn("How to fix", html_text)
            self.assertIn("task-insight-detail", html_text)
            self.assertIn("data-filter-text", html_text)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py TestGenerateReport.test_dashboard_expandable_insights -v
```

- [ ] **Step 3: Replace `_render_task_rows`**

```python
def _render_task_rows(rows: list[dict]) -> str:
    if not rows:
        return (
            '<tr class="dd-data-table__row -empty">'
            '<td class="dd-data-table__td" colspan="9">'
            "No speed tasks — scores look healthy or data was unavailable.</td></tr>"
        )
    out = []
    for r in rows:
        tid = html.escape(r["task_id"])
        detail_id = f"task-insight-{html.escape(r['task_id'])}"
        filter_text = " ".join([
            r.get("task_id") or "",
            r.get("title") or "",
            r.get("what") or "",
            r.get("why") or "",
            r.get("how") or "",
            r.get("metric") or "",
            r.get("owner") or "",
            r.get("page_url") or "",
        ])
        filter_attr = html.escape(filter_text, quote=True)
        what = html.escape(r.get("what") or "")
        why = html.escape(r.get("why") or "")
        how = html.escape(r.get("how") or "")
        out.append(
            f'<tr class="dd-data-table__row" data-task-main="{tid}" data-filter-text="{filter_attr}">'
            f'<th scope="row" class="dd-data-table__td">{tid}</th>'
            f'<td class="dd-data-table__td">{_badge(r["priority"], r["priority"])}</td>'
            f'<td class="dd-data-table__td">{_badge(r["severity"], r["severity"])}</td>'
            f'<td class="dd-data-table__td">'
            f'<button type="button" class="dd-button -secondary task-insight-toggle" '
            f'aria-expanded="false" aria-controls="{detail_id}" '
            f'data-expanded-label="Hide details" data-collapsed-label="Show details">'
            f'{html.escape(r["title"])} <span class="muted">(details)</span></button>'
            f'</td>'
            f'<td class="dd-data-table__td">{html.escape(r["metric"])}</td>'
            f'<td class="dd-data-table__td">{html.escape(str(r["est_savings"]))}</td>'
            f'<td class="dd-data-table__td">{html.escape(r["owner"])}</td>'
            f'<td class="dd-data-table__td">{html.escape(r["timeline"])}</td>'
            f'<td class="dd-data-table__td">{html.escape(r["page_url"])}</td>'
            f"</tr>"
        )
        out.append(
            f'<tr class="dd-data-table__row task-insight-detail" id="{detail_id}" hidden>'
            f'<td class="dd-data-table__td" colspan="9">'
            f'<div class="task-insights l-box">'
            f'<section><h3 class="h5">What it means</h3><p>{what}</p></section>'
            f'<section><h3 class="h5">Why it matters</h3><p>{why}</p></section>'
            f'<section><h3 class="h5">How to fix</h3><p>{how}</p></section>'
            f"</div></td></tr>"
        )
    return "\n".join(out)
```

- [ ] **Step 4: Update dashboard footer note** in `templates/dashboard.html`

Replace:

```html
<p class="muted">{{TASK_COUNT}} entries · full how-to text is in ACTION-PLAN.md and tasks.csv</p>
```

with:

```html
<p class="muted">{{TASK_COUNT}} entries · expand a task for What / Why / How · full text also in ACTION-PLAN.md, DOCX, and tasks.csv</p>
```

- [ ] **Step 5: Add expand/collapse + fix filter JS** in the first IIFE in `dashboard.html`

Replace the filter handler and add toggle logic:

```javascript
  <script>
    (function () {
      const table = document.getElementById('task-table');
      if (!table) return;
      const status = document.getElementById('task-status');
      const filter = document.getElementById('task-filter');
      let announce;

      function setDetailVisibility(mainRow, show) {
        const btn = mainRow.querySelector('.task-insight-toggle');
        if (!btn) return;
        const id = btn.getAttribute('aria-controls');
        const detail = id ? document.getElementById(id) : null;
        if (!detail) return;
        btn.setAttribute('aria-expanded', show ? 'true' : 'false');
        if (show) {
          detail.removeAttribute('hidden');
        } else {
          detail.setAttribute('hidden', '');
        }
      }

      table.addEventListener('click', (e) => {
        const btn = e.target.closest('.task-insight-toggle');
        if (!btn || !table.contains(btn)) return;
        const expanded = btn.getAttribute('aria-expanded') === 'true';
        const mainRow = btn.closest('tr');
        setDetailVisibility(mainRow, !expanded);
      });

      if (filter) {
        filter.addEventListener('input', () => {
          const q = filter.value.toLowerCase().trim();
          let shown = 0;
          table.querySelectorAll('tbody tr[data-task-main]').forEach((tr) => {
            const hay = (tr.getAttribute('data-filter-text') || tr.textContent).toLowerCase();
            const match = !q || hay.includes(q);
            tr.style.display = match ? '' : 'none';
            const btn = tr.querySelector('.task-insight-toggle');
            const detailId = btn && btn.getAttribute('aria-controls');
            const detail = detailId ? document.getElementById(detailId) : null;
            if (detail) {
              if (!match) {
                detail.style.display = 'none';
              } else {
                // keep expanded state: show detail row only if expanded
                const open = btn.getAttribute('aria-expanded') === 'true';
                detail.style.display = open ? '' : 'none';
                if (!open) detail.setAttribute('hidden', '');
              }
            }
            if (match) shown++;
          });
          if (status) {
            clearTimeout(announce);
            announce = setTimeout(() => {
              status.textContent = q
                ? (shown ? shown + ' matching tasks' : 'No matching tasks')
                : '';
            }, 400);
          }
        });
      }

      const csvBtn = document.getElementById('task-csv');
      if (csvBtn) {
        csvBtn.addEventListener('click', () => {
          // Export main rows only (skip hidden detail markup noise when collapsed)
          const rows = Array.from(table.querySelectorAll('tr[data-task-main], thead tr')).filter(
            (tr) => tr.style.display !== 'none'
          );
          const csv = rows.map((tr) =>
            Array.from(tr.querySelectorAll('th,td')).map((c) => {
              const t = c.textContent.trim().replace(/"/g, '""');
              return /[",\n]/.test(t) ? '"' + t + '"' : t;
            }).join(',')
          ).join('\n');
          const blob = new Blob([csv], { type: 'text/csv' });
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = 'speed-tasks.csv';
          a.click();
          URL.revokeObjectURL(a.href);
        });
      }
    })();
```

Keep the second IIFE (hash focus) unchanged.

Optional minimal CSS (inline in `<head>` or at end of existing style block if present)—only if buttons look broken. Prefer existing `dd-button` classes; no new framework.

- [ ] **Step 6: Run full suite**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add custom/dd-site-speed-audit/scripts/generate_report.py \
        custom/dd-site-speed-audit/templates/dashboard.html \
        custom/dd-site-speed-audit/scripts/test_generate_report.py
git commit -m "feat(dd-site-speed): expandable What/Why/How insights on dashboard"
```

---

### Task 7: `pagespeed.py` env API key default

**Files:**
- Modify: `custom/dd-site-speed-audit/scripts/pagespeed.py`

- [ ] **Step 1: Add `import os`** if missing (top of file with other imports).

- [ ] **Step 2: Change argparse for `--api-key`**

```python
    parser.add_argument(
        "--api-key",
        default=os.environ.get("PAGESPEED_API_KEY") or os.environ.get("PSI_API_KEY"),
        help="Google PageSpeed API key (optional; also PAGESPEED_API_KEY / PSI_API_KEY env)",
    )
```

- [ ] **Step 3: Manual smoke (no commit if offline)**

```bash
cd custom/dd-site-speed-audit
# With key in environment after source ~/.bashrc:
python3 scripts/pagespeed.py https://example.com --strategy mobile --json 2>&1 | head -c 400
```

Expected: JSON with `"performance_score": 100` (or similar) and `"error": null` — **not** a free-tier 429 if key is valid. If quota exhausted, still verify `args.api_key` is non-None by adding a one-off debug print then removing it, or:

```bash
python3 -c "
import os, argparse
os.environ['PAGESPEED_API_KEY']='test-key-value'
# re-import logic: default expression
assert (os.environ.get('PAGESPEED_API_KEY') or os.environ.get('PSI_API_KEY')) == 'test-key-value'
print('env default ok')
"
```

- [ ] **Step 4: Commit**

```bash
git add custom/dd-site-speed-audit/scripts/pagespeed.py
git commit -m "fix(dd-site-speed): pagespeed.py defaults to PAGESPEED_API_KEY env"
```

---

### Task 8: Docs sync (playbook reference + skill README)

**Files:**
- Modify: `custom/dd-site-speed-audit/skills/dd-site-speed/references/optimization-playbook.md`
- Modify: `custom/dd-site-speed-audit/skills/dd-site-speed/SKILL.md`
- Modify: `custom/dd-site-speed-audit/README.md`

- [ ] **Step 1: Prepend a short note to `optimization-playbook.md` after the intro**

```markdown
## Issue insights (report fields)

Every remediation task in the client bundle includes three fields resolved from the in-code PLAYBOOK in `scripts/generate_report.py`:

| Field | Label in reports | Purpose |
|-------|------------------|---------|
| `what` | What it means | Plain-language description of the issue |
| `why` | Why it matters | Impact on CWV / score / UX |
| `how` | How to fix | Actionable remediation (stack tips may append) |

Unknown Lighthouse IDs fall back to the PSI audit description for `what`, a generic metric-based `why`, and a generic `how`. Agents enriching recommendations should **not** invent savings numbers or reintroduce FID.
```

Keep existing tables; no need to duplicate full prose in MD (runtime source remains Python).

- [ ] **Step 2: SKILL.md deliverables table** — update the tasks/report rows:

In the Deliverables table, change the ACTION-PLAN / dashboard descriptions to mention What/Why/How insights, e.g.:

| `index.html` | Branded dashboard (scores, CWV, expandable task insights, CSV download) |
| `ACTION-PLAN.md` | Prioritized remediation plan with What / Why / How per task |
| `tasks.csv` | Tracker-ready tasks including what, why, how columns |

- [ ] **Step 3: README features bullet**

Add under Features:

```markdown
- **Issue insights** — What it means, Why it matters, How to fix on every task (dashboard expand + MD/DOCX/CSV)
```

- [ ] **Step 4: Commit**

```bash
git add custom/dd-site-speed-audit/skills/dd-site-speed/references/optimization-playbook.md \
        custom/dd-site-speed-audit/skills/dd-site-speed/SKILL.md \
        custom/dd-site-speed-audit/README.md
git commit -m "docs(dd-site-speed): document per-issue What/Why/How insights"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run full unit suite**

```bash
cd custom/dd-site-speed-audit && python3 scripts/test_generate_report.py -v
```

Expected: all tests OK.

- [ ] **Step 2: Optional live audit** (if API quota allows)

```bash
source ~/.bashrc
cd custom/dd-site-speed-audit
python3 scripts/run_speed_audit.py https://example.com --output-dir /tmp/speed-insights-smoke/
# Inspect:
grep -n "What it means" /tmp/speed-insights-smoke/ACTION-PLAN.md | head
grep -n "task-insight-detail" /tmp/speed-insights-smoke/index.html | head
head -1 /tmp/speed-insights-smoke/tasks.csv
```

- [ ] **Step 3: Spec success criteria checklist**

- [ ] Every generated task has non-empty `what`, `why`, `how`
- [ ] Dashboard expandable sections work (manual open of `index.html`)
- [ ] MD, DOCX, CSV include all three fields
- [ ] Unknown IDs get fallbacks
- [ ] Tests pass
- [ ] `pagespeed.py` uses env key by default
- [ ] No new pip dependencies

- [ ] **Step 4: No extra commit unless smoke found bugs** — if bugs, fix + commit with message `fix(dd-site-speed): …`

---

## Spec coverage self-review

| Spec requirement | Task |
|------------------|------|
| Three fields what/why/how | 1–3 |
| Curated PLAYBOOK + PSI fallback | 1–2 |
| All deliverables: MD | 4 |
| All deliverables: CSV | 4 |
| All deliverables: DOCX | 5 |
| All deliverables: dashboard expandable | 6 |
| CWV synthetic tasks curated | 2–3 |
| Filter includes insight text | 6 |
| Keyboard-accessible toggle + aria-expanded | 6 |
| pagespeed.py env key | 7 |
| optimization-playbook / skill docs | 8 |
| Unit tests | 1, 3–6, 9 |
| No new deps | all |

Placeholder scan: none (full PLAYBOOK text, full function bodies, exact commands).

Type consistency: fields always named `what`, `why`, `how`; opportunity ids `cwv-lcp` / `cwv-inp` / `cwv-cls`; helper `resolve_insights(...) -> tuple[str, str, str]`.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-16-dd-site-speed-issue-insights.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration  
2. **Inline Execution** — Execute tasks in this session with batch checkpoints  

Which approach?
