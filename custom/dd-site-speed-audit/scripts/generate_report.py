#!/usr/bin/env python3
"""
Generate client-facing page speed audit artifacts from audit JSON.

Outputs (in --output-dir):
  - SPEED-AUDIT-REPORT.md
  - ACTION-PLAN.md
  - SPEED-CLIENT-REPORT.docx
  - ACTION-PLAN.docx
  - tasks.csv
  - index.html
  - data.json (copy/normalized)
  - assets/ (framework branding)
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# Opportunity id → recommended owner / default how-to
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


def load_brand_config() -> dict:
    path = TEMPLATES_DIR / "brand.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def render_template(template_text: str, replacements: dict) -> str:
    rendered = template_text
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def ensure_brand_asset(output_dir: Path, relative_asset_path: str) -> str:
    for candidate in (TEMPLATES_DIR / relative_asset_path, SKILL_DIR / relative_asset_path):
        if candidate.exists():
            destination = output_dir / relative_asset_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate, destination)
            return relative_asset_path
    return relative_asset_path


def copy_framework_assets(output_dir: Path) -> None:
    src = TEMPLATES_DIR / "assets"
    if not src.is_dir():
        return
    dst = output_dir / "assets"
    for sub in ("css", "js", "favicon", "imgs"):
        candidate = src / sub
        if candidate.is_dir():
            shutil.copytree(candidate, dst / sub, dirs_exist_ok=True)


def score_label(score) -> str:
    if score is None:
        return "Unavailable"
    if score >= 90:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Needs Improvement"
    if score >= 30:
        return "Poor"
    return "Critical"


def severity_from_savings(savings_ms: int, savings_bytes: int = 0) -> str:
    if savings_ms >= 1000 or savings_bytes >= 500_000:
        return "Critical"
    if savings_ms >= 500 or savings_bytes >= 200_000:
        return "High"
    if savings_ms >= 200 or savings_bytes >= 50_000:
        return "Medium"
    return "Low"


def priority_from_severity(sev: str) -> str:
    return {"Critical": "P0", "High": "P1", "Medium": "P2", "Low": "P3"}.get(sev, "P2")


def timeline_from_severity(sev: str) -> str:
    return {
        "Critical": "Immediate (1-2 days)",
        "High": "Week 1",
        "Medium": "Month 1",
        "Low": "Backlog",
    }.get(sev, "Triage")


def format_ms(value) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if v >= 1000:
        return f"{v / 1000:.1f}s"
    return f"{int(round(v))}ms"


def format_bytes(value) -> str:
    if not value:
        return ""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} MB"
    if value >= 1000:
        return f"{value / 1000:.0f} KB"
    return f"{value} B"


def format_audit_date(timestamp: str | None) -> str:
    if not timestamp:
        return "—"
    try:
        ts = timestamp.replace("Z", "+00:00") if isinstance(timestamp, str) else timestamp
        return datetime.fromisoformat(ts).strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return str(timestamp)


def stack_tips(stack_labels: list[str], opportunity_id: str) -> str:
    labels = " ".join(stack_labels).lower()
    tips = []
    if "wordpress" in labels:
        if opportunity_id in ("modern-image-formats", "uses-webp-images", "uses-responsive-images"):
            tips.append("WordPress: use a reputable image optimization plugin or CDN (e.g. shortpixel, imagify, cloudinary) and regenerate thumbnails.")
        if opportunity_id == "server-response-time":
            tips.append("WordPress: enable full-page cache (host or plugin), object cache (Redis), and avoid heavy admin-ajax on the front end.")
        if opportunity_id in ("unused-javascript", "render-blocking-resources"):
            tips.append("WordPress: dequeue unused plugin/theme assets on templates that do not need them; consider Asset CleanUp or theme-level conditionals.")
    if "next.js" in labels or "nextjs" in labels:
        if opportunity_id in ("modern-image-formats", "uses-responsive-images", "offscreen-images"):
            tips.append("Next.js: prefer next/image with sizes; avoid unoptimized static <img> for LCP.")
        if opportunity_id in ("unused-javascript", "bootup-time"):
            tips.append("Next.js: use dynamic(() => import()) for heavy client components; audit bundle with @next/bundle-analyzer.")
    if "shopify" in labels:
        if opportunity_id in ("third-party-summary", "unused-javascript"):
            tips.append("Shopify: audit app embeds and remove unused apps; defer non-critical app scripts.")
    if "react" in labels and "next.js" not in labels:
        if opportunity_id in ("unused-javascript", "bootup-time"):
            tips.append("React SPA: code-split routes, SSR/SSG if SEO/LCP critical, hydrate only interactive islands.")
    return " ".join(tips)


def get_pages(results: dict) -> list[dict]:
    if results.get("pages"):
        return results["pages"]
    # Single-page shape fallback
    return [{
        "page_url": results.get("metadata", {}).get("url", ""),
        "page_slug": "page",
        "strategies": results.get("strategies", {}),
        "stack": results.get("stack", {}),
        "error": results.get("error"),
    }]


def pick_strategy_data(page: dict, prefer: str = "mobile") -> dict:
    strategies = page.get("strategies") or {}
    if prefer in strategies and not strategies[prefer].get("error"):
        return strategies[prefer]
    for key in ("mobile", "desktop"):
        data = strategies.get(key) or {}
        if data and not data.get("error"):
            return data
    return strategies.get(prefer) or strategies.get("mobile") or strategies.get("desktop") or {}


def page_score(page: dict) -> int | None:
    scores = []
    for key in ("mobile", "desktop"):
        data = (page.get("strategies") or {}).get(key) or {}
        if data.get("performance_score") is not None and not data.get("error"):
            scores.append(data["performance_score"])
    if not scores:
        return None
    return int(round(sum(scores) / len(scores)))


def build_task_rows(results: dict) -> list[dict]:
    rows = []
    idx = 1
    stack_labels = results.get("metadata", {}).get("stack_labels") or []

    for page in get_pages(results):
        page_url = page.get("page_url") or ""
        page_slug = page.get("page_slug") or "page"
        page_stack = page.get("stack") or {}
        labels = page_stack.get("labels") or stack_labels

        # Prefer mobile opportunities (usually stricter); merge desktop-only titles
        seen_ids = set()
        opps = []
        for strategy in ("mobile", "desktop"):
            data = (page.get("strategies") or {}).get(strategy) or {}
            for opp in data.get("opportunities") or []:
                oid = opp.get("id") or opp.get("title")
                if oid in seen_ids:
                    # keep higher savings
                    for existing in opps:
                        if (existing.get("id") or existing.get("title")) == oid:
                            if (opp.get("savings_ms") or 0) > (existing.get("savings_ms") or 0):
                                existing.update(opp)
                                existing["strategy"] = strategy
                            break
                    continue
                seen_ids.add(oid)
                item = dict(opp)
                item["strategy"] = strategy
                opps.append(item)

        opps.sort(key=lambda o: (o.get("savings_ms") or 0, o.get("savings_bytes") or 0), reverse=True)

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

        # Metric-based tasks when CWV is poor and no opportunity captured the metric
        primary = pick_strategy_data(page, "mobile")
        metrics = primary.get("metrics") or {}
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

    # Stable sort: P0 first, then savings
    pri_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    rows.sort(key=lambda r: (pri_order.get(r["priority"], 9), -(r.get("est_savings_ms") or 0)))
    # Re-number after sort
    for i, row in enumerate(rows, start=1):
        row["task_id"] = f"SPEED-{i:03d}"
    return rows


def summarize_results(results: dict) -> dict:
    pages = get_pages(results)
    scores = [s for s in (page_score(p) for p in pages) if s is not None]
    overall = int(round(sum(scores) / len(scores))) if scores else None
    mobile_scores = []
    desktop_scores = []
    for p in pages:
        m = (p.get("strategies") or {}).get("mobile") or {}
        d = (p.get("strategies") or {}).get("desktop") or {}
        if m.get("performance_score") is not None and not m.get("error"):
            mobile_scores.append(m["performance_score"])
        if d.get("performance_score") is not None and not d.get("error"):
            desktop_scores.append(d["performance_score"])

    rows = build_task_rows(results)
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for r in rows:
        counts[r["severity"]] = counts.get(r["severity"], 0) + 1

    return {
        "overall_score": overall,
        "mobile_score": int(round(sum(mobile_scores) / len(mobile_scores))) if mobile_scores else None,
        "desktop_score": int(round(sum(desktop_scores) / len(desktop_scores))) if desktop_scores else None,
        "page_count": len(pages),
        "task_count": len(rows),
        "critical_count": counts.get("Critical", 0),
        "high_count": counts.get("High", 0),
        "medium_count": counts.get("Medium", 0),
        "low_count": counts.get("Low", 0),
    }


def generate_markdown_report(results: dict, rows: list[dict]) -> str:
    meta = results.get("metadata") or {}
    summary = summarize_results(results)
    pages = get_pages(results)
    lines = [
        "# Page Speed Audit Report",
        f"<!-- Generated: {meta.get('timestamp', '')} -->",
        f"<!-- Primary URL: {meta.get('url', '')} -->",
        "",
        "## Executive Summary",
        "",
        f"**Overall Performance Score:** {summary['overall_score'] if summary['overall_score'] is not None else 'n/a'}/100 "
        f"({score_label(summary['overall_score'])})",
        f"**Mobile (avg):** {summary['mobile_score'] if summary['mobile_score'] is not None else 'n/a'}/100",
        f"**Desktop (avg):** {summary['desktop_score'] if summary['desktop_score'] is not None else 'n/a'}/100",
        f"**Pages audited:** {summary['page_count']}",
        f"**Tasks generated:** {summary['task_count']}",
        f"**Critical / High / Medium / Low:** "
        f"{summary['critical_count']} / {summary['high_count']} / {summary['medium_count']} / {summary['low_count']}",
        "",
        f"**Stack:** {', '.join(meta.get('stack_labels') or []) or 'Not detected'}",
        f"**Data source:** Google PageSpeed Insights API v5 (lab Lighthouse + field CrUX when available)",
        "",
        "## Core Web Vitals (primary page, mobile preferred)",
        "",
    ]

    primary_page = pages[0] if pages else {}
    primary_data = pick_strategy_data(primary_page, "mobile")
    metrics = primary_data.get("metrics") or {}
    if metrics:
        lines.extend([
            "| Metric | Value | Rating | Source |",
            "|--------|-------|--------|--------|",
        ])
        for name in ("LCP", "INP", "CLS", "FCP", "TTFB", "SI", "TBT"):
            m = metrics.get(name)
            if not m:
                continue
            val = m.get("value")
            unit = m.get("unit") or ""
            display = format_ms(val) if unit == "ms" else (f"{val}" if unit == "" else f"{val}{unit}")
            if name == "CLS":
                display = str(val)
            lines.append(
                f"| {name} — {m.get('label', name)} | {display} | {m.get('rating', '—')} | {m.get('source', '—')} |"
            )
        lines.append("")
    else:
        lines.append("No metrics available (API error or empty response).")
        lines.append("")

    lines.extend(["## Per-page scores", ""])
    lines.extend([
        "| Page | Mobile | Desktop | Average |",
        "|------|--------|---------|---------|",
    ])
    for page in pages:
        m = (page.get("strategies") or {}).get("mobile") or {}
        d = (page.get("strategies") or {}).get("desktop") or {}
        ms = m.get("performance_score")
        ds = d.get("performance_score")
        avg = page_score(page)
        url = page.get("page_url") or ""
        ms_s = f"{ms}" if ms is not None else (m.get("error") or "—")
        ds_s = f"{ds}" if ds is not None else (d.get("error") or "—")
        avg_s = f"{avg}" if avg is not None else "—"
        lines.append(f"| {url} | {ms_s} | {ds_s} | {avg_s} |")
    lines.append("")

    lines.extend(["## Findings & opportunities", ""])
    if not rows:
        lines.append("No performance opportunities or CWV failures were identified.")
        lines.append("")
    else:
        for row in rows:
            lines.extend([
                f"### {row['task_id']} — {row['title']}",
                f"- **Priority:** {row['priority']} ({row['severity']})",
                f"- **Page:** {row['page_url']}",
                f"- **Metric:** {row['metric']}",
                f"- **Est. savings:** {row['est_savings']}",
                f"- **Effort / Owner:** {row['effort']} / {row['owner']}",
                f"- **Stack context:** {row['stack'] or 'n/a'}",
                f"- **What it means:** {row['what']}",
                f"- **Why it matters:** {row['why']}",
                f"- **How to fix:** {row['how']}",
                f"- **Evidence:** {row['evidence']}",
                "",
            ])

    lines.extend([
        "## Methodology",
        "",
        "- Lab data from Lighthouse via PageSpeed Insights (simulated mobile/desktop).",
        "- Field data from Chrome UX Report (CrUX) when the origin has sufficient real-user traffic.",
        "- Core Web Vitals: LCP, INP, CLS (FID is deprecated — never report FID).",
        "- Recommendations combine Lighthouse opportunities with stack-aware playbook guidance.",
        "",
        "## Deliverables",
        "",
        "- `SPEED-AUDIT-REPORT.md`",
        "- `ACTION-PLAN.md`",
        "- `SPEED-CLIENT-REPORT.docx`",
        "- `ACTION-PLAN.docx`",
        "- `tasks.csv`",
        "- `index.html`",
        "- `data.json`",
        "",
    ])

    limitations = results.get("limitations") or []
    if limitations:
        lines.extend(["## Environment limitations", ""])
        for item in limitations:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def generate_action_plan(results: dict, rows: list[dict]) -> str:
    meta = results.get("metadata") or {}
    summary = summarize_results(results)
    lines = [
        "# Page Speed Action Plan",
        f"<!-- URL: {meta.get('url', '')} -->",
        f"<!-- Generated: {meta.get('timestamp', '')} -->",
        "",
        "## Priority matrix",
        "",
        "| Priority | Severity | Count | Timeline | Typical owner |",
        "|----------|----------|-------|----------|---------------|",
        f"| P0 | Critical | {summary['critical_count']} | Immediate (1-2 days) | Frontend / DevOps |",
        f"| P1 | High | {summary['high_count']} | Week 1 | Frontend Development |",
        f"| P2 | Medium | {summary['medium_count']} | Month 1 | Frontend + CMS |",
        f"| P3 | Low | {summary['low_count']} | Backlog | Product / Maintenance |",
        "",
        f"Pages in scope: {summary['page_count']}",
        f"Overall score: {summary['overall_score'] if summary['overall_score'] is not None else 'n/a'}/100",
        "",
        "## Remediation tasks",
        "",
    ]
    if not rows:
        lines.append("No remediation tasks were generated.")
    else:
        for row in rows:
            lines.extend([
                f"### {row['task_id']} — {row['title']}",
                f"- Priority: {row['priority']} ({row['severity']})",
                f"- Page: {row['page_url']}",
                f"- Metric: {row['metric']}",
                f"- Est. savings: {row['est_savings']}",
                f"- Owner: {row['owner']}",
                f"- Timeline: {row['timeline']}",
                f"- Effort: {row['effort']}",
                f"- What it means: {row['what']}",
                f"- Why it matters: {row['why']}",
                f"- How to fix: {row['how']}",
                "",
            ])
    return "\n".join(lines)


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


def paragraph_xml(text: str) -> str:
    escaped = html.escape(text)
    return (
        "<w:p><w:r><w:t xml:space=\"preserve\">"
        f"{escaped}"
        "</w:t></w:r></w:p>"
    )


def _write_simple_docx(path: Path, title: str, paragraphs: list[str]) -> None:
    utc_now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    body = [paragraph_xml(p) for p in paragraphs]
    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        f"<w:body>{''.join(body)}"
        "<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"1440\" "
        "w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" w:header=\"708\" "
        "w:footer=\"708\" w:gutter=\"0\"/></w:sectPr></w:body></w:document>"
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-package.extended-properties+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{html.escape(title)}</dc:title>
  <dc:creator>dd-site-speed</dc:creator>
  <cp:lastModifiedBy>dd-site-speed</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{utc_now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{utc_now}</dcterms:modified>
</cp:coreProperties>"""
    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>dd-site-speed</Application>
</Properties>"""
    with ZipFile(path, "w", ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("docProps/core.xml", core)
        docx.writestr("docProps/app.xml", app)
        docx.writestr("word/document.xml", document_xml)


def build_client_docx(path: Path, results: dict, rows: list[dict]) -> None:
    meta = results.get("metadata") or {}
    summary = summarize_results(results)
    paras = [
        "Page Speed Audit Client Report",
        f"URL: {meta.get('url', '')}",
        f"Generated: {meta.get('timestamp', '')}",
        f"Overall score: {summary['overall_score']}/100 ({score_label(summary['overall_score'])})",
        f"Mobile avg: {summary['mobile_score']} | Desktop avg: {summary['desktop_score']}",
        f"Pages: {summary['page_count']} | Tasks: {summary['task_count']}",
        f"Stack: {', '.join(meta.get('stack_labels') or []) or 'n/a'}",
        " ",
    ]
    if not rows:
        paras.append("No automated performance tasks were generated.")
    else:
        for row in rows:
            paras.append(
                f"{row['task_id']} | {row['priority']} | {row['severity']} | {row['title']} | "
                f"Savings: {row['est_savings']} | Owner: {row['owner']}"
            )
            paras.append(f"What it means: {(row.get('what') or '')[:500]}")
            paras.append(f"Why it matters: {(row.get('why') or '')[:500]}")
            paras.append(f"How to fix: {(row.get('how') or '')[:500]}")
            paras.append(" ")
    _write_simple_docx(path, "Page Speed Audit Client Report", paras)


def build_action_plan_docx(path: Path, results: dict, rows: list[dict]) -> None:
    meta = results.get("metadata") or {}
    summary = summarize_results(results)
    paras = [
        "Page Speed Action Plan",
        f"URL: {meta.get('url', '')}",
        f"Generated: {meta.get('timestamp', '')}",
        f"P0 Critical: {summary['critical_count']} | P1 High: {summary['high_count']} | "
        f"P2 Medium: {summary['medium_count']} | P3 Low: {summary['low_count']}",
        " ",
    ]
    for row in rows:
        paras.append(
            f"{row['task_id']} [{row['priority']}] {row['title']} — "
            f"{row['timeline']} — {row['owner']} — effort {row['effort']}"
        )
        paras.append(f"What it means: {(row.get('what') or '')[:600]}")
        paras.append(f"Why it matters: {(row.get('why') or '')[:600]}")
        paras.append(f"How to fix: {(row.get('how') or '')[:600]}")
        paras.append(" ")
    if not rows:
        paras.append("No remediation tasks.")
    _write_simple_docx(path, "Page Speed Action Plan", paras)


# Task priority/severity → dd-badge variant (-pass / -info / -warning / -critical)
_SEVERITY_MOD = {
    "critical": "-critical",
    "high": "-warning",
    "medium": "-info",
    "low": "-pass",
    "p0": "-critical",
    "p1": "-warning",
    "p2": "-info",
    "p3": "-pass",
}

# Core Web Vitals / Lighthouse metric ratings → dd-badge variant
# Meaning stays in the label text (WCAG 1.4.1); color reinforces only.
_RATING_MOD = {
    "good": "-pass",
    "fast": "-pass",
    "needs-improvement": "-warning",
    "needs_improvement": "-warning",
    "average": "-warning",
    "poor": "-critical",
    "slow": "-critical",
    "unknown": "",
    "—": "",
    "-": "",
}

_RATING_LABELS = {
    "good": "Good",
    "fast": "Good",
    "needs-improvement": "Needs improvement",
    "needs_improvement": "Needs improvement",
    "average": "Needs improvement",
    "poor": "Poor",
    "slow": "Poor",
    "unknown": "Unknown",
}

# Task-severity bar rows → dd-bar-chart row tone (-good / -warn / -bad)
_SEVERITY_BAR_MOD = {
    "Critical": "-bad",
    "High": "-warn",
    "Medium": "",
    "Low": "-good",
}

_DOWNLOAD_FORMATS = {
    "md": "Markdown", "csv": "CSV", "docx": "DOCX", "json": "JSON", "html": "HTML",
}


def _normalize_rating_key(kind: str) -> str:
    return (kind or "").strip().lower().replace(" ", "-").replace("_", "-")


def _badge(kind: str, label: str) -> str:
    """Render a dd-badge. ``kind`` selects the color modifier; ``label`` is shown."""
    key = _normalize_rating_key(kind)
    # Prefer rating map, then severity/priority map
    mod = _RATING_MOD.get(key)
    if mod is None:
        mod = _SEVERITY_MOD.get(key, "")
    cls = f"dd-badge {mod}".strip() if mod else "dd-badge"
    return (
        f'<span class="{cls}"><span class="dd-badge__label">'
        f"{html.escape(str(label))}</span></span>"
    )


def _rating_badge(rating: str | None) -> str:
    """Color-coded CWV/Lighthouse rating badge with a human-readable label."""
    if rating is None or str(rating).strip() in ("", "—", "-"):
        return _badge("", "—")
    key = _normalize_rating_key(str(rating))
    label = _RATING_LABELS.get(key) or str(rating).replace("-", " ").replace("_", " ").title()
    return _badge(key, label)


def _score_bar_mod(score) -> str:
    """Lighthouse score band → bar-chart row modifier (-good / -warn / -bad)."""
    if score is None:
        return ""
    try:
        value = int(score)
    except (TypeError, ValueError):
        return ""
    if value >= 90:
        return "-good"
    if value >= 50:
        return "-warn"
    return "-bad"


def _render_score_bars(summary: dict) -> str:
    items = [
        ("Mobile", summary.get("mobile_score")),
        ("Desktop", summary.get("desktop_score")),
        ("Overall", summary.get("overall_score")),
    ]
    rows = []
    for label, score in items:
        val = score if isinstance(score, int) else 0
        pct = max(0, min(100, val))
        display = str(score) if score is not None else "—"
        row_mod = _score_bar_mod(score)
        row_cls = f"dd-bar-chart__row {row_mod}".strip() if row_mod else "dd-bar-chart__row"
        rows.append(
            f'<li class="{row_cls}">'
            f'<span class="dd-bar-chart__label">{html.escape(label)}</span>'
            f'<span class="dd-bar-chart__track" aria-hidden="true">'
            f'<span class="dd-bar-chart__fill" style="inline-size: {pct}%"></span></span>'
            f'<span class="dd-bar-chart__value">{html.escape(display)}</span>'
            f"</li>"
        )
    return "\n".join(rows)


def _render_severity_bars(summary: dict) -> str:
    order = [
        ("Critical", summary.get("critical_count", 0)),
        ("High", summary.get("high_count", 0)),
        ("Medium", summary.get("medium_count", 0)),
        ("Low", summary.get("low_count", 0)),
    ]
    top = max((c for _, c in order), default=0) or 1
    rows = []
    for label, count in order:
        pct = round((count / top) * 100)
        row_mod = _SEVERITY_BAR_MOD.get(label, "")
        row_cls = f"dd-bar-chart__row {row_mod}".strip() if row_mod else "dd-bar-chart__row"
        rows.append(
            f'<li class="{row_cls}">'
            f'<span class="dd-bar-chart__label">{label}</span>'
            f'<span class="dd-bar-chart__track" aria-hidden="true">'
            f'<span class="dd-bar-chart__fill" style="inline-size: {pct}%"></span></span>'
            f'<span class="dd-bar-chart__value">{count}</span>'
            f"</li>"
        )
    return "\n".join(rows)


def _render_page_cards(pages: list[dict]) -> str:
    cards = []
    for page in pages:
        url = page.get("page_url") or ""
        esc_url = html.escape(url)
        avg = page_score(page)
        m = (page.get("strategies") or {}).get("mobile") or {}
        d = (page.get("strategies") or {}).get("desktop") or {}
        stack = page.get("stack") or {}
        primary = (stack.get("primary") or {}).get("label") or "—"
        ms = m.get("performance_score")
        ds = d.get("performance_score")
        cwv = pick_strategy_data(page, "mobile").get("metrics") or {}
        lcp = cwv.get("LCP", {})
        inp = cwv.get("INP", {})
        cls = cwv.get("CLS", {})

        def _m(mdict, name):
            if not mdict:
                return "—"
            v = mdict.get("value")
            if name == "CLS":
                return str(v) if v is not None else "—"
            return format_ms(v) if v is not None else "—"

        cards.append(
            f'<div class="dd-card__item l-box dd-u-1-1 dd-u-md-12-24" data-aos="fade-up">'
            f'<div class="dd-card__body dd-g">'
            f'<div class="dd-card__copy l-box">'
            f'<div class="dd-card__title"><h3>{esc_url}</h3></div>'
            f'<div class="dd-card__sub-title"><strong>Avg score: '
            f'{html.escape(str(avg) if avg is not None else "n/a")} / 100</strong></div>'
            f"<p>Mobile: {html.escape(str(ms) if ms is not None else '—')} · "
            f"Desktop: {html.escape(str(ds) if ds is not None else '—')}</p>"
            f"<p>LCP {_m(lcp, 'LCP')} · INP {_m(inp, 'INP')} · CLS {_m(cls, 'CLS')}</p>"
            f"<p class=\"muted\">Stack: {html.escape(str(primary))}</p>"
            f"</div></div></div>"
        )
    if not cards:
        return (
            '<div class="dd-card__item l-box dd-u-1-1"><div class="dd-card__body">'
            '<div class="dd-card__copy l-box">'
            '<p class="muted">No pages in this audit.</p>'
            "</div></div></div>"
        )
    return "\n".join(cards)


def _render_metric_rows(pages: list[dict]) -> str:
    page = pages[0] if pages else {}
    data = pick_strategy_data(page, "mobile")
    metrics = data.get("metrics") or {}
    if not metrics:
        return (
            '<tr class="dd-data-table__row -empty">'
            '<td class="dd-data-table__td" colspan="4">No metrics available.</td></tr>'
        )
    out = []
    for name in ("LCP", "INP", "CLS", "FCP", "TTFB", "SI", "TBT"):
        m = metrics.get(name)
        if not m:
            continue
        unit = m.get("unit") or ""
        val = m.get("value")
        display = str(val) if name == "CLS" or unit == "" else format_ms(val)
        rating = m.get("rating") or "—"
        out.append(
            f'<tr class="dd-data-table__row">'
            f'<th scope="row" class="dd-data-table__td">{html.escape(name)}</th>'
            f'<td class="dd-data-table__td">{html.escape(display)}</td>'
            f'<td class="dd-data-table__td">{_rating_badge(rating)}</td>'
            f'<td class="dd-data-table__td">{html.escape(m.get("source") or "—")}</td>'
            f"</tr>"
        )
    return "\n".join(out)


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


def _render_download_links(links: list[tuple[str, str]]) -> str:
    out = []
    for label, filename in links:
        fmt = _DOWNLOAD_FORMATS.get(filename.rsplit(".", 1)[-1].lower(), "File")
        text = f"{html.escape(label)} ({fmt})"
        out.append(
            f'<div class="dd-section__item dd-u-1-1 dd-u-lg-8-24 l-box">'
            f'<a href="{html.escape(filename)}" download class="dd-button -secondary" '
            f'aria-label="Download {text}">{text}</a></div>'
        )
    return "\n".join(out)


def build_dashboard(path: Path, results: dict, rows: list[dict]) -> None:
    template_path = TEMPLATES_DIR / "dashboard.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Dashboard template not found: {template_path}")

    brand = load_brand_config()
    output_dir = path.parent
    logo_path = ensure_brand_asset(
        output_dir, brand.get("agency_logo", "assets/imgs/logo-full-black-text.svg")
    )
    logo_dark_path = ensure_brand_asset(
        output_dir, brand.get("agency_logo_dark", "assets/imgs/logo-full-white-text.svg")
    )
    copy_framework_assets(output_dir)
    summary = summarize_results(results)
    pages = get_pages(results)
    meta = results.get("metadata") or {}
    overall = summary.get("overall_score")

    download_links = [
        ("Speed Audit Report", "SPEED-AUDIT-REPORT.md"),
        ("Action Plan", "ACTION-PLAN.md"),
        ("Client Report", "SPEED-CLIENT-REPORT.docx"),
        ("Action Plan (DOCX)", "ACTION-PLAN.docx"),
        ("Tasks CSV", "tasks.csv"),
        ("Raw data", "data.json"),
    ]

    html_doc = render_template(
        template_path.read_text(encoding="utf-8"),
        {
            "REPORT_TITLE": html.escape(brand.get("report_title", "Page Speed Audit Dashboard")),
            "REPORT_SUBTITLE": html.escape(
                brand.get(
                    "report_subtitle",
                    "Core Web Vitals, Lighthouse opportunities, and prioritized speed fixes.",
                )
            ),
            "AGENCY_NAME": html.escape(brand.get("agency_name", "ldnddev, LLC")),
            "AGENCY_KICKER": html.escape(brand.get("agency_kicker", "Page Speed Audit")),
            "AGENCY_LOGO": html.escape(logo_path),
            "AGENCY_LOGO_DARK": html.escape(logo_dark_path),
            "AUDIT_URL": html.escape(meta.get("url", "")),
            "AUDIT_DATE": html.escape(format_audit_date(meta.get("timestamp"))),
            "STACK_LABELS": html.escape(", ".join(meta.get("stack_labels") or []) or "—"),
            "SCORE_VALUE": html.escape(str(overall) if overall is not None else "—"),
            "SCORE_RATING": html.escape(score_label(overall)),
            "MOBILE_SCORE": html.escape(
                str(summary["mobile_score"]) if summary["mobile_score"] is not None else "—"
            ),
            "DESKTOP_SCORE": html.escape(
                str(summary["desktop_score"]) if summary["desktop_score"] is not None else "—"
            ),
            "PAGE_COUNT": html.escape(str(summary["page_count"])),
            "TASK_COUNT": html.escape(str(len(rows))),
            "CRITICAL_COUNT": html.escape(str(summary["critical_count"])),
            "HIGH_COUNT": html.escape(str(summary["high_count"])),
            "MEDIUM_COUNT": html.escape(str(summary["medium_count"])),
            "LOW_COUNT": html.escape(str(summary["low_count"])),
            "DOWNLOADS_NOTE": html.escape(
                brand.get(
                    "downloads_note",
                    "Use these links to review raw metrics and download packaged report files.",
                )
            ),
            "TASKS_NOTE": html.escape(
                brand.get(
                    "tasks_note",
                    "Tasks are ranked by estimated savings and severity.",
                )
            ),
            "SCORE_BARS": _render_score_bars(summary),
            "SEVERITY_BARS": _render_severity_bars(summary),
            "PAGE_CARDS": _render_page_cards(pages),
            "METRIC_ROWS": _render_metric_rows(pages),
            "FOOTER_TEXT": html.escape(
                brand.get("footer_text", "Prepared by © ldnddev, LLC")
            ),
            "DOWNLOAD_LINKS": _render_download_links(download_links),
            "TASK_ROWS": _render_task_rows(rows),
        },
    )
    path.write_text(html_doc, encoding="utf-8")


def generate_all(results: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_task_rows(results)
    summary = summarize_results(results)
    results = dict(results)
    results["summary"] = summary

    md_report = output_dir / "SPEED-AUDIT-REPORT.md"
    action_plan = output_dir / "ACTION-PLAN.md"
    csv_path = output_dir / "tasks.csv"
    client_docx = output_dir / "SPEED-CLIENT-REPORT.docx"
    plan_docx = output_dir / "ACTION-PLAN.docx"
    html_path = output_dir / "index.html"
    data_path = output_dir / "data.json"

    md_report.write_text(generate_markdown_report(results, rows), encoding="utf-8")
    action_plan.write_text(generate_action_plan(results, rows), encoding="utf-8")
    write_csv(csv_path, rows)
    build_client_docx(client_docx, results, rows)
    build_action_plan_docx(plan_docx, results, rows)
    data_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    build_dashboard(html_path, results, rows)

    return {
        "output_dir": str(output_dir),
        "report_markdown": str(md_report),
        "action_plan_markdown": str(action_plan),
        "tasks_csv": str(csv_path),
        "client_docx": str(client_docx),
        "action_plan_docx": str(plan_docx),
        "dashboard_html": str(html_path),
        "data_json": str(data_path),
        "summary": summary,
        "task_count": len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate page speed audit deliverables")
    parser.add_argument("--input", required=True, help="Path to audit JSON")
    parser.add_argument("--output-dir", default=".", help="Directory for generated artifacts")
    args = parser.parse_args()

    results = json.loads(Path(args.input).read_text(encoding="utf-8"))
    artifacts = generate_all(results, Path(args.output_dir))
    print(json.dumps(artifacts, indent=2))


if __name__ == "__main__":
    main()
