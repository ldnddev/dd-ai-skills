#!/usr/bin/env python3
"""
Generate an interactive HTML SEO report.

Runs all analysis scripts and aggregates results into a single,
self-contained interactive HTML file with a premium dashboard UI.

Usage:
    python generate_report.py https://example.com
    python generate_report.py https://example.com --output my-report.html
"""

import argparse
import csv
import html as html_lib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from urllib.parse import urlparse
from zipfile import ZIP_DEFLATED, ZipFile

import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "templates"))


def run_script(script_name: str, args: list, timeout: int = 120) -> dict:
    """Run an analysis script and capture JSON output."""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.exists(script_path):
        return {"error": f"Script {script_name} not found"}

    cmd = [sys.executable, script_path] + args + ["--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        err_msg = result.stderr.strip() or f"Exit code {result.returncode}"
        return {"error": f"[{script_name}] {err_msg}"}
    except subprocess.TimeoutExpired:
        return {"error": f"Script timed out after {timeout}s"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON output from script"}
    except Exception as e:
        return {"error": str(e)}


def fetch_page(url: str) -> str:
    """Fetch page HTML to a temp file, return path."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SEOBot/1.0)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
        tmp.write(html)
        tmp.close()
        return tmp.name
    except Exception:
        return ""


def detect_environment(html_text: str, url: str) -> dict:
    """Infer site environment/CMS/framework from source signals."""
    lower = (html_text or "").lower()
    domain = urlparse(url).netloc.lower()
    scores = {}
    reasons = {}

    def hit(name: str, points: int, reason: str):
        scores[name] = scores.get(name, 0) + points
        reasons.setdefault(name, []).append(reason)

    # Managed CMS signals
    if any(s in lower for s in ("bloggerusercontent.com", "www.blogger.com", "data:blog.", "b:skin")):
        hit("Blogger", 6, "Blogger template/assets detected")
    if domain.endswith("blogspot.com"):
        hit("Blogger", 4, "Blogspot domain detected")

    if any(s in lower for s in ("wp-content/", "wp-includes/", "wp-json")):
        hit("WordPress", 6, "WordPress core paths detected")
    if re.search(r'generator[^>]+wordpress', lower):
        hit("WordPress", 3, "WordPress generator meta detected")

    if any(s in lower for s in ("cdn.shopify.com", "shopify.theme", "shopify-section")):
        hit("Shopify", 6, "Shopify assets/theme markers detected")

    if any(s in lower for s in ("wixstatic.com", "wix.com", "wixsite")):
        hit("Wix", 6, "Wix assets detected")

    if any(s in lower for s in ("webflow", "w-webflow")):
        hit("Webflow", 5, "Webflow markers detected")

    if any(s in lower for s in ("squarespace.com", "static1.squarespace")):
        hit("Squarespace", 6, "Squarespace assets detected")

    if re.search(r'generator[^>]+ghost', lower) or "ghost/" in lower:
        hit("Ghost", 5, "Ghost generator/assets detected")

    # Framework signals
    if any(s in lower for s in ("/_next/", "__next_data__")):
        hit("Next.js", 6, "Next.js runtime/build markers detected")
    if any(s in lower for s in ("/_nuxt/", "__nuxt")):
        hit("Nuxt", 6, "Nuxt runtime/build markers detected")

    if not scores:
        return {
            "primary": "Unknown",
            "runtime": "Unknown",
            "confidence": "low",
            "signals": ["No strong CMS/framework markers were found in HTML source."],
            "alternatives": [],
        }

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary, top_score = ranked[0]
    confidence = "high" if top_score >= 8 else "medium" if top_score >= 5 else "low"
    runtime_map = {
        "Blogger": "Managed CMS",
        "WordPress": "Managed CMS",
        "Shopify": "Managed CMS / Commerce",
        "Wix": "Managed CMS",
        "Webflow": "Managed CMS",
        "Squarespace": "Managed CMS",
        "Ghost": "Managed CMS",
        "Next.js": "JavaScript Framework",
        "Nuxt": "JavaScript Framework",
    }
    return {
        "primary": primary,
        "runtime": runtime_map.get(primary, "Unknown"),
        "confidence": confidence,
        "signals": reasons.get(primary, [])[:5],
        "alternatives": [name for name, _ in ranked[1:3]],
    }


def _platform_hint(primary: str, area: str) -> str:
    """Provide platform-specific implementation guidance."""
    blogger = {
        "metadata": "In Blogger, update Theme -> Edit HTML and add tags in the <head> section (title template, meta description, OG/Twitter tags).",
        "heading": "In Blogger templates, keep exactly one content H1 per page (post title on posts, site headline on homepage).",
        "headers": "Blogger cannot set most response headers directly. Add Cloudflare in front and configure Response Header Transform Rules.",
        "llms": "Blogger cannot natively serve arbitrary root files. Serve /llms.txt via Cloudflare Workers/Pages or reverse-proxy route.",
        "links": "Fix broken internal links in post content and navigation widgets; update outdated post URLs and labels.",
        "performance": "Optimize Blogger theme widgets/scripts, compress hero/media assets, and defer non-critical third-party scripts.",
    }
    wordpress = {
        "metadata": "Use your SEO plugin (Yoast/RankMath/AIOSEO) or theme templates to set title/meta and OG/Twitter tags.",
        "heading": "Ensure one H1 in theme templates and avoid duplicate H1 in builders/widgets.",
        "headers": "Set headers via server config (Nginx/Apache) or CDN edge rules.",
        "llms": "Create /llms.txt at web root or route it through your web server.",
        "links": "Fix links in menus, content blocks, and internal link plugin data.",
        "performance": "Use caching, image optimization, script deferral, and CWV-focused plugin settings.",
    }
    nextjs = {
        "metadata": "Use the Next.js Metadata API (`app/`) or `next/head` (`pages/`) for title/meta/OG/Twitter tags.",
        "heading": "Set a single semantic H1 in each route component.",
        "headers": "Set security headers in `next.config.js` `headers()` or at your edge/CDN.",
        "llms": "Serve `/llms.txt` from `/public/llms.txt`.",
        "links": "Fix links in route components and content source files; validate with link checks in CI.",
        "performance": "Use `next/image`, dynamic imports, script strategy controls, and reduce main-thread JS.",
    }
    fallback = {
        "metadata": "Update page templates to set complete title/meta/OG/Twitter tags.",
        "heading": "Ensure each page has exactly one descriptive H1 aligned to intent.",
        "headers": "Set missing security headers at web server or CDN layer.",
        "llms": "Add `/llms.txt` at site root with concise site description and key URLs.",
        "links": "Repair or remove broken internal links and refresh outdated navigation targets.",
        "performance": "Compress critical assets, reduce render-blocking scripts, and optimize CWV bottlenecks.",
    }

    platform_map = {
        "Blogger": blogger,
        "WordPress": wordpress,
        "Shopify": fallback,
        "Wix": fallback,
        "Webflow": fallback,
        "Squarespace": fallback,
        "Ghost": fallback,
        "Next.js": nextjs,
        "Nuxt": nextjs,
    }
    return platform_map.get(primary, fallback).get(area, fallback.get(area, ""))


def build_environment_fixes(data: dict) -> list:
    """Build actionable issue fixes tailored to detected environment."""
    env = data.get("environment", {})
    platform = env.get("primary", "Unknown")
    fixes = []

    def add(severity: str, title: str, reason: str, fix: str):
        fixes.append({
            "severity": severity,
            "title": title,
            "reason": reason,
            "fix": fix,
        })

    op = data["sections"].get("onpage", {})
    sec = data["sections"].get("security", {})
    soc = data["sections"].get("social", {})
    llm = data["sections"].get("llms_txt", {})
    bl = data["sections"].get("broken_links", {})
    rd = data["sections"].get("readability", {})
    psi = data["sections"].get("pagespeed", {})

    title = (op.get("title") or "").strip()
    meta = (op.get("meta_description") or "").strip()
    h1s = op.get("h1", []) if isinstance(op.get("h1"), list) else []

    if not h1s:
        add(
            "critical",
            "Missing H1 on page",
            "No primary content heading was detected, which weakens topical clarity.",
            _platform_hint(platform, "heading"),
        )

    if not meta or len(meta) < 110 or len(meta) > 170:
        add(
            "warning",
            "Meta description is missing or out of range",
            "This can reduce SERP CTR and snippet quality.",
            _platform_hint(platform, "metadata"),
        )

    if not title or len(title) < 30 or len(title) > 65:
        add(
            "warning",
            "Title tag needs optimization",
            "Title length/content is likely suboptimal for rankings and click-through.",
            _platform_hint(platform, "metadata"),
        )

    missing_headers = sec.get("headers_missing", {})
    if missing_headers:
        add(
            "critical" if len(missing_headers) >= 4 else "warning",
            f"{len(missing_headers)} security headers missing",
            "Missing headers reduce trust and can expose the site to browser/security risks.",
            _platform_hint(platform, "headers"),
        )

    if not llm.get("exists"):
        add(
            "warning",
            "No llms.txt found",
            "AI crawlers and assistants have no curated machine-readable guidance for key pages.",
            _platform_hint(platform, "llms"),
        )

    broken_count = bl.get("summary", {}).get("broken", 0)
    if broken_count > 0:
        add(
            "critical" if broken_count >= 5 else "warning",
            f"{broken_count} broken links detected",
            "Broken internal links hurt crawl flow and user trust.",
            _platform_hint(platform, "links"),
        )

    og_missing = soc.get("og_missing", [])
    tw_missing = soc.get("twitter_missing", [])
    if og_missing or tw_missing:
        add(
            "warning",
            "Social meta tags are incomplete",
            "Missing OG/Twitter tags weakens social previews and share quality.",
            _platform_hint(platform, "metadata"),
        )

    if psi.get("error"):
        add(
            "info",
            "Performance measurement incomplete",
            "PageSpeed API returned an error, so CWV recommendations are less reliable.",
            "Rerun `pagespeed.py` with `--api-key` and then prioritize LCP/INP/CLS fixes from that output.",
        )

    if rd.get("flesch_reading_ease", 100) < 40 or rd.get("avg_sentence_length", 0) > 25:
        add(
            "warning",
            "Content readability is difficult",
            "Long, complex text can reduce engagement and comprehension.",
            "Rewrite key sections with shorter sentences (15-20 words), shorter paragraphs (2-4 sentences), and clearer subheadings.",
        )

    if not fixes:
        add(
            "pass",
            "No major implementation blockers detected",
            "Core checks look healthy for current scope.",
            "Continue monitoring with regular crawls and keep metadata/security/performance baselines in CI.",
        )

    return fixes


def render_environment_fixes(fixes: list) -> str:
    """Render environment-specific fixes for HTML output."""
    if not fixes:
        return '<p style="color:var(--green)">✅ No environment-specific fixes needed.</p>'

    severity_order = {"critical": 0, "warning": 1, "info": 2, "pass": 3}
    html = ""
    for item in sorted(fixes, key=lambda x: severity_order.get(x.get("severity", "info"), 9)):
        sev = item.get("severity", "info")
        badge = sev.upper()
        title = html_lib.escape(item.get("title", ""), quote=True)
        reason = html_lib.escape(item.get("reason", ""), quote=True)
        fix = html_lib.escape(item.get("fix", ""), quote=True)
        html += (
            f'<div class="issue-item {sev if sev in ("critical","warning","info") else "info"}">'
            f'<span class="issue-badge">{badge}</span>'
            f'<div><strong>{title}</strong><br>'
            f'<span style="color:var(--text-muted)">{reason}</span><br>'
            f'<span><strong>Fix:</strong> {fix}</span></div></div>'
        )
    return html


def collect_data(url: str) -> dict:
    """Run all analysis scripts and collect results."""
    print(f"🔍 Analyzing {url}...")
    data = {
        "url": url,
        "domain": urlparse(url).netloc,
        "timestamp": datetime.now().isoformat(),
        "sections": {},
    }

    # Fetch page for parse_html and readability
    print("  ⏳ Fetching page HTML...")
    html_path = fetch_page(url)
    page_html = ""
    if html_path and os.path.exists(html_path):
        try:
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                page_html = f.read()
        except OSError:
            page_html = ""
    data["environment"] = detect_environment(page_html, url)

    analyses = [
        ("robots", "robots_checker.py", [url]),
        ("security", "security_headers.py", [url]),
        ("social", "social_meta.py", [url]),
        ("redirects", "redirect_checker.py", [url]),
        ("llms_txt", "llms_txt_checker.py", [url]),
        ("broken_links", "broken_links.py", [url, "--workers", "5", "--timeout", "8"]),
        ("internal_links", "internal_links.py", [url, "--depth", "1", "--max-pages", "15"]),
        ("pagespeed", "pagespeed.py", [url, "--strategy", "mobile"]),
        # New analysis scripts (supplementary — failures don't block report)
        ("entity", "entity_checker.py", [url]),
        ("link_profile", "link_profile.py", [url, "--max-pages", "20"]),
        ("hreflang", "hreflang_checker.py", [url]),
        ("duplicate_content", "duplicate_content.py", [url]),
    ]

    # Add parse_html and readability if page was fetched
    if html_path:
        analyses.append(("onpage", "parse_html.py", [html_path, "--url", url]))
        analyses.append(("readability", "readability.py", [html_path]))
        analyses.append(("article", "article_seo.py", [url]))

    for name, script, args in analyses:
        print(f"  ⏳ Running {script}...")
        start = time.time()
        result = run_script(script, args)
        elapsed = round(time.time() - start, 1)
        data["sections"][name] = result
        status = "⚠️ error" if "error" in result and result.get("error") else "✅"
        print(f"  {status} {script} ({elapsed}s)")

    # Cleanup temp file
    if html_path and os.path.exists(html_path):
        os.unlink(html_path)

    data["environment_fixes"] = build_environment_fixes(data)

    return data


def calculate_overall_score(data: dict) -> dict:
    """Calculate overall SEO score from all analyses."""
    scores = {}
    weights = {
        "security": 8,
        "social": 5,
        "robots": 8,
        "broken_links": 10,
        "internal_links": 8,
        "redirects": 3,
        "llms_txt": 5,
        "pagespeed": 13,
        "onpage": 10,
        "readability": 8,
        "entity": 5,
        "link_profile": 7,
        "hreflang": 5,
        "duplicate_content": 5,
    }

    # Security score
    sec = data["sections"].get("security", {})
    scores["security"] = sec.get("score", 0)

    # Social meta score
    soc = data["sections"].get("social", {})
    scores["social"] = soc.get("score", 0)

    # Robots score
    rob = data["sections"].get("robots", {})
    if rob.get("status") == 200:
        base = 60
        if rob.get("sitemaps"):
            base += 20
        ai_managed = sum(1 for s in rob.get("ai_crawler_status", {}).values()
                         if "not managed" not in s)
        base += min(20, ai_managed * 2)
        scores["robots"] = min(100, base)
    elif rob.get("status") == 404:
        scores["robots"] = 20
    else:
        scores["robots"] = 0

    # Article score (informational, not weighted heavily)
    art = data["sections"].get("article", {})
    if art and not art.get("error"):
        art_score = 50
        if art.get("target_keyword"): art_score += 25
        if art.get("lsi_keywords"): art_score += 25
        scores["article"] = min(100, art_score)
    else:
        scores["article"] = 0

    # Broken links score
    bl = data["sections"].get("broken_links", {})
    summary = bl.get("summary", {})
    total = summary.get("total", 1) or 1
    broken = summary.get("broken", 0)
    scores["broken_links"] = max(0, 100 - int((broken / total) * 300))

    # Internal links score
    il = data["sections"].get("internal_links", {})
    il_issues = len(il.get("issues", []))
    scores["internal_links"] = max(0, 100 - il_issues * 20)

    # Redirects score
    red = data["sections"].get("redirects", {})
    red_issues = len(red.get("issues", []))
    scores["redirects"] = max(0, 100 - red_issues * 25)

    # llms.txt score
    llm = data["sections"].get("llms_txt", {})
    if llm.get("exists"):
        scores["llms_txt"] = llm.get("quality", {}).get("score", 0)
    else:
        scores["llms_txt"] = 0

    # PageSpeed score
    psi = data["sections"].get("pagespeed", {})
    scores["pagespeed"] = psi.get("performance_score", 0)

    # On-page score
    op = data["sections"].get("onpage", {})
    if op and not op.get("error"):
        op_score = 50
        if op.get("title"): op_score += 15
        if op.get("meta_description"): op_score += 15
        if op.get("h1"): op_score += 10
        if op.get("canonical"): op_score += 10
        scores["onpage"] = min(100, op_score)
    else:
        scores["onpage"] = 0

    # Readability score
    rd = data["sections"].get("readability", {})
    flesch = rd.get("flesch_reading_ease", 0)
    if flesch >= 60:
        scores["readability"] = 100
    elif flesch >= 30:
        scores["readability"] = 50 + int((flesch - 30) * (50 / 30))
    else:
        scores["readability"] = max(0, int(flesch * (50 / 30)))

    # Entity SEO score
    ent = data["sections"].get("entity", {})
    if ent and not ent.get("error"):
        sameas = ent.get("sameas_analysis", {})
        found = sameas.get("total_found", 0)
        missing = sameas.get("total_missing_critical", 4)
        has_wikidata = 1 if ent.get("wikidata", {}).get("found") else 0
        has_wikipedia = 1 if ent.get("wikipedia", {}).get("found") else 0
        ent_score = min(100, found * 15 + has_wikidata * 25 + has_wikipedia * 25)
        issues_count = len(ent.get("issues", []))
        ent_score = max(0, ent_score - issues_count * 10)
        scores["entity"] = ent_score
    else:
        scores["entity"] = 0

    # Link profile score
    lp = data["sections"].get("link_profile", {})
    if lp and not lp.get("error"):
        avg_links = lp.get("avg_internal_links_per_page", 0)
        orphans = lp.get("orphan_pages", {}).get("count", 0)
        dead_ends = lp.get("dead_end_pages", {}).get("count", 0)
        lp_score = 70
        if avg_links >= 5: lp_score += 15
        elif avg_links >= 3: lp_score += 5
        else: lp_score -= 15
        lp_score -= min(30, orphans * 5)
        lp_score -= min(20, dead_ends * 3)
        scores["link_profile"] = max(0, min(100, lp_score))
    else:
        scores["link_profile"] = 0

    # Hreflang score (skip weight if not applicable)
    hf = data["sections"].get("hreflang", {})
    if hf and not hf.get("error"):
        if hf.get("hreflang_tags_found", 0) > 0:
            summary = hf.get("summary", {})
            hf_score = 100 - summary.get("critical", 0) * 30 - summary.get("high", 0) * 15 - summary.get("medium", 0) * 5
            scores["hreflang"] = max(0, min(100, hf_score))
        else:
            # No hreflang = single language site, skip from weighting
            scores["hreflang"] = None
    else:
        scores["hreflang"] = None

    # Duplicate content score
    dc = data["sections"].get("duplicate_content", {})
    if dc and not dc.get("error"):
        dupes = len(dc.get("near_duplicates", []))
        thin = len(dc.get("thin_pages", []))
        dc_score = 100 - dupes * 20 - thin * 10
        scores["duplicate_content"] = max(0, min(100, dc_score))
    else:
        scores["duplicate_content"] = 0

    # Weighted average (only scored categories)
    total_weight = 0
    weighted_sum = 0
    for k, w in weights.items():
        if k in scores:
            val = scores.get(k)
            if val is not None:
                total_weight += w
                weighted_sum += val * w
    
    overall = round(weighted_sum / total_weight) if total_weight else 0

    # Coerce any None scores to 0 to prevent UI crashes
    for k in list(scores.keys()):
        if scores[k] is None:
            scores[k] = 0

    return {
        "overall": overall,
        "categories": scores,
        "weights": weights,
    }


def render_recommendations(section_data: dict) -> str:
    """Render recommendations from a section's JSON data."""
    recs = section_data.get("recommendations", section_data.get("suggestions", []))
    if isinstance(recs, dict):
        items = [f"{k}: {v}" for k, v in recs.items()]
    elif isinstance(recs, list):
        items = recs
    else:
        items = []
    # Also check opportunities from pagespeed
    opps = section_data.get("opportunities", [])
    if isinstance(opps, list):
        items.extend(opps)

    # Render structured issues (used by entity_checker, hreflang_checker, etc.)
    issues = section_data.get("issues", [])
    issues_html = ""
    if isinstance(issues, list) and issues:
        severity_map = {"critical": "critical", "high": "critical", "warning": "warning", "medium": "warning", "info": "info", "low": "info"}
        for issue in issues[:15]:
            if isinstance(issue, dict):
                sev = severity_map.get(issue.get("severity", "info").lower(), "info")
                badge = html_lib.escape(issue.get("severity", "INFO").upper(), quote=True)
                finding = html_lib.escape(str(issue.get("finding", "")), quote=True)
                fix = html_lib.escape(str(issue.get("fix", "")), quote=True)
                issues_html += (
                    f'<div class="issue-item {sev}">'
                    f'<span class="issue-badge">{badge}</span>'
                    f'<div><strong>{finding}</strong>'
                    f'{f"<br><span style=&quot;color:var(--text-muted)&quot;>Fix: {fix}</span>" if fix else ""}'
                    f'</div></div>'
                )
            elif isinstance(issue, str):
                items.append(issue)

    html = ""
    if issues_html:
        html += f'<div style="margin-top:16px"><h3 style="font-size:0.95rem;margin-bottom:8px;">🔍 Issues Found</h3>{issues_html}</div>'
    if items:
        html += '<div style="margin-top:16px"><h3 style="font-size:0.95rem;margin-bottom:8px;">💡 Recommendations</h3>'
        for item in items[:15]:
            item_str = str(item) if not isinstance(item, str) else item
            html += f'<div class="issue-item info"><span class="issue-badge">FIX</span> {item_str}</div>'
        html += '</div>'
    return html


def render_readability_rewrites(readability_data: dict) -> str:
    """Render concrete sentence replacements for readability fixes."""
    rewrites = readability_data.get("sentence_rewrites", [])
    if not rewrites:
        return ""

    html = (
        '<div style="margin-top:16px">'
        '<h3 style="font-size:0.95rem;margin-bottom:8px;">✍️ What To Replace (Before/After)</h3>'
    )
    for item in rewrites[:5]:
        current = html_lib.escape(str(item.get("current", "")), quote=True)
        suggested = html_lib.escape(str(item.get("suggested", "")), quote=True)
        wc_raw = item.get("current_word_count", "")
        wc_label = f"{wc_raw}w" if isinstance(wc_raw, (int, float)) else str(wc_raw)
        wc = html_lib.escape(wc_label, quote=True)
        html += (
            '<div class="issue-item warning">'
            f'<span class="issue-badge">SENTENCE ({wc})</span>'
            '<div>'
            f'<div><strong>Current:</strong> {current}</div>'
            f'<div style="margin-top:6px;"><strong>Replace with:</strong> {suggested}</div>'
            '</div>'
            '</div>'
        )
    html += "</div>"
    return html


def render_all_recommendations(data: dict) -> str:
    """Render all recommendations from all sections."""
    section_names = {
        "security": "🔒 Security", "social": "📱 Social Meta", "robots": "🤖 Robots",
        "broken_links": "🔗 Links", "internal_links": "🕸️ Internal Links",
        "redirects": "↪️ Redirects", "llms_txt": "🧠 AI Search",
        "pagespeed": "⚡ Performance", "onpage": "📝 On-Page", "readability": "📖 Readability",
        "article": "📄 Article SEO", "entity": "🏛️ Entity SEO",
        "link_profile": "🔗 Link Profile", "hreflang": "🌍 Hreflang",
        "duplicate_content": "📋 Content Uniqueness",
    }
    html = ""
    env_fixes = data.get("environment_fixes", [])
    if env_fixes:
        html += '<h3 style="font-size:0.95rem;margin:16px 0 8px;">🛠️ Environment-Specific Fixes</h3>'
        for item in env_fixes[:8]:
            title = html_lib.escape(item.get("title", ""), quote=True)
            fix = html_lib.escape(item.get("fix", ""), quote=True)
            html += f'<div class="issue-item info"><span class="issue-badge">FIX</span> <strong>{title}</strong>: {fix}</div>'

    for key, label in section_names.items():
        section = data["sections"].get(key, {})
        recs = section.get("recommendations", section.get("suggestions", []))
        if isinstance(recs, dict):
            items = [f"{k}: {v}" for k, v in recs.items()]
        elif isinstance(recs, list):
            items = recs
        else:
            items = []
        opps = section.get("opportunities", [])
        if isinstance(opps, list):
            items.extend(opps)
        if key == "readability":
            for rw in section.get("sentence_rewrites", [])[:3]:
                cur = html_lib.escape(str(rw.get("current", ""))[:180], quote=True)
                sug = html_lib.escape(str(rw.get("suggested", ""))[:180], quote=True)
                items.append(f"Rewrite: {cur} → {sug}")
        if items:
            html += f'<h3 style="font-size:0.95rem;margin:16px 0 8px;">{label}</h3>'
            for item in items[:10]:
                html += f'<div class="issue-item info"><span class="issue-badge">FIX</span> {item}</div>'
    return html if html else '<p style="color:var(--green)">✅ No recommendations — everything looks good!</p>'


def _load_template_files() -> tuple:
    dashboard_path = os.path.join(TEMPLATES_DIR, "dashboard.html")
    brand_path = os.path.join(TEMPLATES_DIR, "brand.json")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        template = f.read()
    with open(brand_path, "r", encoding="utf-8") as f:
        brand = json.load(f)
    return template, brand


def _score_rating(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Needs Improvement"
    if score >= 30:
        return "Poor"
    return "Critical"


def _ring_color(score: int) -> str:
    if score >= 80:
        return "#1f5f33"
    if score >= 50:
        return "#7a4a00"
    return "#8a1a1a"


def _render_category_cards(scores: dict) -> str:
    icons = {
        "security": "🔒", "social": "📱", "robots": "🤖",
        "broken_links": "🔗", "internal_links": "🕸️", "redirects": "↪️",
        "llms_txt": "🧠", "pagespeed": "⚡", "onpage": "📝",
        "readability": "📖", "article": "📄", "entity": "🏛️",
        "link_profile": "🔗", "hreflang": "🌍", "duplicate_content": "📋",
    }
    cards = []
    for key, label in CATEGORY_LABELS.items():
        if key == "environment":
            continue
        raw = scores.get("categories", {}).get(key)
        if raw is None:
            continue
        score = int(raw)
        ring = _ring_color(score)
        dash = round(score * 2.51327, 1)
        icon = icons.get(key, "📊")
        anchor = f"#section-{key}"
        cards.append(
            f'<a class="category-card" href="{anchor}" '
            f'aria-label="{html_lib.escape(label)}: {score} of 100">'
            f'<div class="ring-wrap">'
            f'<svg viewBox="0 0 90 90" aria-hidden="true">'
            f'<circle cx="45" cy="45" r="40" fill="none" stroke="var(--line)" stroke-width="6"/>'
            f'<circle cx="45" cy="45" r="40" fill="none" stroke="{ring}" stroke-width="6" '
            f'stroke-dasharray="{dash} 251.327" stroke-linecap="round" '
            f'transform="rotate(-90 45 45)"/>'
            f'</svg>'
            f'<div class="ring-label">{score}</div>'
            f'</div>'
            f'<div class="category-name">{icon} {html_lib.escape(label)}</div>'
            f'</a>'
        )
    return "\n".join(cards)


def _render_category_chart_data(scores: dict) -> str:
    cats = scores.get("categories") or {
        k: v for k, v in scores.items()
        if k != "overall" and isinstance(v, (int, float))
    }
    label_map = {
        "technical": "Technical",
        "content": "Content",
        "onpage": "On-page",
        "schema": "Schema",
        "performance": "Performance",
        "images": "Images",
        "geo": "GEO",
    }
    palette = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#14B8A6", "#F43F5E"]
    ordered_keys = ["technical", "content", "onpage", "schema", "performance", "images", "geo"]
    keys = [k for k in ordered_keys if k in cats] or list(cats.keys())
    payload = {
        "labels": [label_map.get(k, k.title()) for k in keys],
        "values": [int(cats[k]) for k in keys],
        "colors": [palette[i % len(palette)] for i in range(len(keys))],
    }
    return json.dumps(payload)


def _render_download_links(artifacts: list) -> str:
    chunks = []
    for art in artifacts:
        kind = html_lib.escape(art["kind"])
        label = html_lib.escape(art["label"])
        filename = html_lib.escape(art["filename"])
        chunks.append(
            f'<a class="download-link" href="{filename}" download>'
            f'<span class="download-kind">{kind}</span>'
            f'<div class="download-label">{label}</div>'
            f'<div class="download-file">{filename}</div>'
            f'</a>'
        )
    return "\n".join(chunks)


def _render_task_rows(rows: list) -> str:
    if not rows:
        return (
            '<tr><td colspan="7" style="text-align:center;color:var(--muted)">'
            'No remediation tasks — site is healthy.'
            '</td></tr>'
        )
    out = []
    for r in rows:
        sev = r["priority"].lower()
        out.append(
            f'<tr>'
            f'<td>{html_lib.escape(r["task_id"])}</td>'
            f'<td><span class="priority-pill" data-severity="{sev}">'
            f'{html_lib.escape(r["priority"])}</span></td>'
            f'<td>{html_lib.escape(r["category_label"])}</td>'
            f'<td>{html_lib.escape(r["finding"])}</td>'
            f'<td>{html_lib.escape(r["owner"])}</td>'
            f'<td>{html_lib.escape(r["timeline"])}</td>'
            f'<td>{r["estimated_hours"]}h</td>'
            f'</tr>'
        )
    return "\n".join(out)


def _details_block(section_id: str, title: str, score, body_html: str) -> str:
    score_chip = ""
    if score is not None and score != "":
        score_chip = (
            f'<span style="font: 700 13px/1 var(--ui-font); color: var(--muted);">'
            f'{int(score)}/100</span>'
        )
    return (
        f'<details class="section-detail" id="section-{section_id}">'
        f'<summary>{html_lib.escape(title)} {score_chip}</summary>'
        f'<div class="section-body">{body_html}</div>'
        f'</details>'
    )


def _render_detailed_sections(data: dict, scores: dict) -> str:
    cats = scores.get("categories", {})
    sec = data["sections"].get("security", {})
    soc = data["sections"].get("social", {})
    rob = data["sections"].get("robots", {})
    bl = data["sections"].get("broken_links", {})
    il = data["sections"].get("internal_links", {})
    red = data["sections"].get("redirects", {})
    llm = data["sections"].get("llms_txt", {})
    psi = data["sections"].get("pagespeed", {})
    op = data["sections"].get("onpage", {})
    rd = data["sections"].get("readability", {})
    art = data["sections"].get("article", {})
    ent = data["sections"].get("entity", {})
    lp = data["sections"].get("link_profile", {})
    hf = data["sections"].get("hreflang", {})
    dc = data["sections"].get("duplicate_content", {})
    env = data.get("environment", {})
    env_fixes = data.get("environment_fixes", [])

    blocks = []

    sig_html = "".join(
        f'<li style="margin:4px 0;">{html_lib.escape(s)}</li>'
        for s in env.get("signals", [])
    ) or '<li style="color:var(--muted)">No strong platform markers found.</li>'
    env_body = (
        f'<p><strong>Primary platform:</strong> {html_lib.escape(env.get("primary","Unknown"))} · '
        f'<strong>Runtime:</strong> {html_lib.escape(env.get("runtime","Unknown"))} · '
        f'<strong>Confidence:</strong> {html_lib.escape(env.get("confidence","low"))}</p>'
        f'<h4 style="margin:12px 0 6px;">Detection signals</h4><ul>{sig_html}</ul>'
    )
    if env.get("alternatives"):
        env_body += (
            '<p style="color:var(--muted)"><strong>Alternative matches:</strong> '
            + ", ".join(html_lib.escape(a) for a in env["alternatives"])
            + "</p>"
        )
    blocks.append(_details_block("environment", "Environment detection", None, env_body))

    if env_fixes:
        blocks.append(_details_block(
            "env_fixes", "Environment-specific fix plan", None,
            render_environment_fixes(env_fixes),
        ))

    rows = ""
    for h, v in sec.get("headers_present", {}).items():
        rows += (
            f'<tr><td>{html_lib.escape(h)}</td>'
            f'<td><span class="priority-pill" data-severity="pass">Present</span></td>'
            f'<td class="url-cell">{html_lib.escape(str(v)[:80])}</td></tr>'
        )
    for h, d in sec.get("headers_missing", {}).items():
        rows += (
            f'<tr><td>{html_lib.escape(h)}</td>'
            f'<td><span class="priority-pill" data-severity="critical">Missing</span></td>'
            f'<td>{html_lib.escape(str(d))}</td></tr>'
        )
    sec_body = (
        '<table><thead><tr><th scope="col">Header</th><th scope="col">Status</th>'
        f'<th scope="col">Value / Description</th></tr></thead><tbody>{rows}</tbody></table>'
    )
    blocks.append(_details_block("security", "Security headers", cats.get("security"), sec_body))

    rows = ""
    og = soc.get("og_tags", {})
    tw = soc.get("twitter_tags", {})
    for tag in ["og:title", "og:description", "og:image", "og:url", "og:type", "og:site_name"]:
        v = og.get(tag, "")
        sev = "pass" if v else "critical"
        label = "Present" if v else "Missing"
        rows += (
            f'<tr><td>{tag}</td>'
            f'<td><span class="priority-pill" data-severity="{sev}">{label}</span></td>'
            f'<td>{html_lib.escape(str(v)[:80]) or "—"}</td></tr>'
        )
    for tag in ["twitter:card", "twitter:title", "twitter:description", "twitter:image"]:
        v = tw.get(tag, "")
        sev = "pass" if v else "warning"
        label = "Present" if v else "Missing"
        rows += (
            f'<tr><td>{tag}</td>'
            f'<td><span class="priority-pill" data-severity="{sev}">{label}</span></td>'
            f'<td>{html_lib.escape(str(v)[:80]) or "—"}</td></tr>'
        )
    soc_body = (
        '<table><thead><tr><th scope="col">Tag</th><th scope="col">Status</th>'
        f'<th scope="col">Value</th></tr></thead><tbody>{rows}</tbody></table>'
    )
    blocks.append(_details_block("social", "Social meta tags", cats.get("social"), soc_body))

    rows = ""
    for crawler, status in rob.get("ai_crawler_status", {}).items():
        if "blocked" in status:
            sev, label = "pass", "Blocked"
        elif "not managed" in status:
            sev, label = "warning", "Unmanaged"
        else:
            sev, label = "info", "Info"
        rows += (
            f'<tr><td>{html_lib.escape(crawler)}</td>'
            f'<td><span class="priority-pill" data-severity="{sev}">{label}</span></td>'
            f'<td>{html_lib.escape(status)}</td></tr>'
        )
    rob_body = (
        f'<p><strong>robots.txt:</strong> HTTP {rob.get("status","?")} · '
        f'<strong>Sitemaps:</strong> {len(rob.get("sitemaps", []))} · '
        f'<strong>User-agents:</strong> {len(rob.get("user_agents", {}))}</p>'
        '<table><thead><tr><th scope="col">Crawler</th><th scope="col">Status</th>'
        f'<th scope="col">Detail</th></tr></thead><tbody>{rows}</tbody></table>'
    )
    blocks.append(_details_block("robots", "Robots & AI crawlers", cats.get("robots"), rob_body))

    bl_summary = bl.get("summary", {})
    rows = ""
    for link in bl.get("broken", [])[:20]:
        loc = "Internal" if link.get("is_internal") else "External"
        sev = "critical" if link.get("is_internal") else "warning"
        status = link.get("status") or html_lib.escape(str(link.get("error", "?")))
        rows += (
            f'<tr><td><span class="priority-pill" data-severity="{sev}">{loc}</span></td>'
            f'<td>{status}</td>'
            f'<td class="url-cell">{html_lib.escape(str(link.get("url",""))[:80])}</td>'
            f'<td>{html_lib.escape(str(link.get("anchor_text",""))[:40])}</td></tr>'
        )
    bl_body = (
        f'<p><strong>Total:</strong> {bl_summary.get("total",0)} · '
        f'<strong>Healthy:</strong> {bl_summary.get("healthy",0)} · '
        f'<strong>Broken:</strong> {bl_summary.get("broken",0)} · '
        f'<strong>Redirected:</strong> {bl_summary.get("redirected",0)}</p>'
    )
    if rows:
        bl_body += (
            '<table><thead><tr><th scope="col">Type</th><th scope="col">Status</th>'
            '<th scope="col">URL</th><th scope="col">Anchor</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        )
    else:
        bl_body += '<p style="color:var(--pass-text)">No broken links detected.</p>'
    blocks.append(_details_block("broken_links", "Broken links", cats.get("broken_links"), bl_body))

    il_dist = il.get("link_distribution", {})
    rows = ""
    for orphan in il.get("orphan_candidates", [])[:15]:
        rows += (
            f'<tr><td class="url-cell">{html_lib.escape(str(orphan.get("url",""))[:80])}</td>'
            f'<td>{orphan.get("incoming_links","?")}</td></tr>'
        )
    il_body = (
        f'<p><strong>Pages crawled:</strong> {il.get("pages_crawled",0)} · '
        f'<strong>Internal links:</strong> {il.get("total_internal_links",0)} · '
        f'<strong>Avg per page:</strong> {il_dist.get("avg",0)} · '
        f'<strong>Orphans:</strong> {len(il.get("orphan_candidates", []))}</p>'
    )
    if rows:
        il_body += (
            '<h4 style="margin:12px 0 6px;">Potential orphan pages</h4>'
            '<table><thead><tr><th scope="col">URL</th>'
            f'<th scope="col">Incoming</th></tr></thead><tbody>{rows}</tbody></table>'
        )
    blocks.append(_details_block("internal_links", "Internal link structure", cats.get("internal_links"), il_body))

    rows = ""
    for hop in red.get("chain", []):
        status = hop.get("status", "?")
        if hop.get("final"):
            sev = "pass" if isinstance(status, int) and 200 <= status < 300 else "critical"
            tail = "FINAL"
        else:
            sev = "warning"
            tail = html_lib.escape(str(hop.get("redirect_type", "")))
        rows += (
            f'<tr><td>{hop.get("step","?")}</td>'
            f'<td><span class="priority-pill" data-severity="{sev}">{status}</span></td>'
            f'<td class="url-cell">{html_lib.escape(str(hop.get("url",""))[:80])}</td>'
            f'<td>{hop.get("time_ms",0)}ms</td><td>{tail}</td></tr>'
        )
    if rows:
        red_body = (
            '<table><thead><tr><th scope="col">#</th><th scope="col">Status</th>'
            '<th scope="col">URL</th><th scope="col">Time</th>'
            f'<th scope="col">Type</th></tr></thead><tbody>{rows}</tbody></table>'
        )
    else:
        red_body = '<p style="color:var(--pass-text)">No redirect chain — direct access.</p>'
    blocks.append(_details_block("redirects", "Redirect chain", cats.get("redirects"), red_body))

    suggestions = "".join(
        f'<li>{html_lib.escape(s)}</li>'
        for s in (llm.get("quality", {}).get("suggestions") or [])
    )
    llm_body = (
        f'<p><strong>llms.txt:</strong> {"Found" if llm.get("exists") else "Not found"} · '
        f'<strong>llms-full.txt:</strong> {"Found" if llm.get("full_exists") else "Not found"} · '
        f'<strong>Quality score:</strong> {llm.get("quality", {}).get("score", 0)}/100</p>'
    )
    if suggestions:
        llm_body += f'<h4 style="margin:12px 0 6px;">Suggestions</h4><ul>{suggestions}</ul>'
    blocks.append(_details_block("llms_txt", "AI search readiness (llms.txt)", cats.get("llms_txt"), llm_body))

    fd = psi.get("field_data") or psi.get("lab_data") or {}
    psi_body = (
        f'<p><strong>Performance score:</strong> {psi.get("performance_score","?")} · '
        f'<strong>LCP:</strong> {fd.get("LCP","?")} · '
        f'<strong>INP/TBT:</strong> {fd.get("INP", fd.get("TBT","?"))} · '
        f'<strong>CLS:</strong> {fd.get("CLS","?")}</p>'
    )
    if psi.get("error") or psi.get("performance_score", 0) == 0:
        psi_body += (
            '<p style="color:var(--warning-text)"><strong>Note:</strong> '
            'PageSpeed API returned an error or was rate-limited. '
            'Re-run pagespeed.py with --api-key for confirmed values.</p>'
        )
    psi_body += render_recommendations(psi)
    blocks.append(_details_block("pagespeed", "Performance & Core Web Vitals", cats.get("pagespeed"), psi_body))

    op_h1 = ""
    if isinstance(op.get("h1"), list) and op.get("h1"):
        op_h1 = op["h1"][0]
    elif isinstance(op.get("h1"), str):
        op_h1 = op["h1"]
    op_body = (
        '<table><thead><tr><th scope="col">Element</th>'
        '<th scope="col">Value</th><th scope="col">Length</th></tr></thead><tbody>'
        f'<tr><td>Title</td><td>{html_lib.escape(str(op.get("title","") or "—")[:120])}</td>'
        f'<td>{len(str(op.get("title","") or ""))}</td></tr>'
        f'<tr><td>Meta description</td>'
        f'<td>{html_lib.escape(str(op.get("meta_description","") or "—")[:160])}</td>'
        f'<td>{len(str(op.get("meta_description","") or ""))}</td></tr>'
        f'<tr><td>H1</td><td>{html_lib.escape(str(op_h1)[:120] or "—")}</td><td>—</td></tr>'
        f'<tr><td>Canonical</td>'
        f'<td class="url-cell">{html_lib.escape(str(op.get("canonical","") or "—")[:120])}</td>'
        '<td>—</td></tr></tbody></table>'
    )
    op_body += render_recommendations(op)
    blocks.append(_details_block("onpage", "On-page SEO", cats.get("onpage"), op_body))

    rd_body = (
        f'<p><strong>Flesch ease:</strong> {rd.get("flesch_reading_ease","?")} · '
        f'<strong>Grade:</strong> {rd.get("flesch_kincaid_grade","?")} · '
        f'<strong>Words:</strong> {rd.get("word_count","?")} · '
        f'<strong>Read time:</strong> {rd.get("estimated_reading_time_min","?")} min</p>'
    )
    rd_body += render_recommendations(rd)
    rd_body += render_readability_rewrites(rd)
    blocks.append(_details_block("readability", "Readability", cats.get("readability"), rd_body))

    art_body = (
        f'<p><strong>Words:</strong> {art.get("word_count","?")} · '
        f'<strong>H2s:</strong> {len(art.get("headings", {}).get("h2", []))} · '
        f'<strong>Images:</strong> {len(art.get("images", []))}</p>'
        '<table><thead><tr><th scope="col">Target keyword</th>'
        '<th scope="col">LSI / related</th></tr></thead><tbody>'
        f'<tr><td>{html_lib.escape(str(art.get("target_keyword","—") or "—"))}</td>'
        f'<td>{html_lib.escape(", ".join(art.get("lsi_keywords", [])) or "—")}</td></tr>'
        '</tbody></table>'
    )
    art_body += render_recommendations(art)
    blocks.append(_details_block("article", "Article info & keywords", cats.get("article"), art_body))

    sa = ent.get("sameas_analysis", {})
    ent_body = (
        f'<p><strong>Wikidata:</strong> {"Found" if ent.get("wikidata", {}).get("found") else "Missing"} · '
        f'<strong>Wikipedia:</strong> {"Found" if ent.get("wikipedia", {}).get("found") else "Missing"} · '
        f'<strong>sameAs links:</strong> {sa.get("total_found",0)}</p>'
    )
    ent_body += render_recommendations(ent)
    blocks.append(_details_block("entity", "Entity SEO", cats.get("entity"), ent_body))

    lp_body = (
        f'<p><strong>Pages crawled:</strong> {lp.get("pages_crawled","?")} · '
        f'<strong>Avg internal links:</strong> {lp.get("avg_internal_links_per_page","?")} · '
        f'<strong>Orphans:</strong> {lp.get("orphan_pages", {}).get("count",0)} · '
        f'<strong>Dead ends:</strong> {lp.get("dead_end_pages", {}).get("count",0)}</p>'
    )
    lp_body += render_recommendations(lp)
    blocks.append(_details_block("link_profile", "Link profile", cats.get("link_profile"), lp_body))

    hf_body = (
        f'<p><strong>Implementation:</strong> {html_lib.escape(str(hf.get("implementation_method","none")))} · '
        f'<strong>Tags found:</strong> {hf.get("hreflang_tags_found",0)}</p>'
    )
    if hf.get("hreflang_tags_found", 0) == 0:
        hf_body += '<p style="color:var(--muted)">No hreflang tags found — expected for single-language sites.</p>'
    else:
        hf_body += render_recommendations(hf)
    blocks.append(_details_block("hreflang", "Hreflang / international SEO", cats.get("hreflang"), hf_body))

    dc_body = (
        f'<p><strong>Pages analyzed:</strong> {dc.get("pages_analyzed","?")} · '
        f'<strong>Near-duplicates:</strong> {len(dc.get("near_duplicates", []))} · '
        f'<strong>Thin pages:</strong> {len(dc.get("thin_pages", []))}</p>'
    )
    dc_body += render_recommendations(dc)
    blocks.append(_details_block("duplicate_content", "Content uniqueness", cats.get("duplicate_content"), dc_body))

    blocks.append(_details_block(
        "recommendations", "All recommendations", None, render_all_recommendations(data),
    ))

    return "\n".join(blocks)


def generate_html(data: dict, scores: dict, artifacts: list, rows: list) -> str:
    """Render the SEO dashboard from templates/dashboard.html + brand.json."""
    template, brand = _load_template_files()
    overall = int(scores.get("overall", 0))
    rating = _score_rating(overall)
    domain = data.get("domain", "")
    url = data.get("url", "")
    audit_date = data.get("timestamp", datetime.now().isoformat())[:10]
    env_platform = data.get("environment", {}).get("primary", "Unknown")

    critical_count = sum(1 for r in rows if r["priority"] == "Critical")
    warning_count = sum(1 for r in rows if r["priority"] == "Warning")
    info_count = sum(1 for r in rows if r["priority"] == "Info")
    pass_count = sum(
        1 for fix in (data.get("environment_fixes") or [])
        if (fix.get("severity") or "").lower() == "pass"
    )

    substitutions = {
        "REPORT_TITLE": brand.get("report_title", "SEO Audit Dashboard"),
        "REPORT_SUBTITLE": brand.get("report_subtitle", ""),
        "AGENCY_NAME": brand.get("agency_name", ""),
        "AGENCY_KICKER": brand.get("agency_kicker", "SEO Audit"),
        "AGENCY_LOGO": brand.get("agency_logo", "assets/agency-logo.svg"),
        "AGENCY_LOGO_INITIAL": (brand.get("agency_logo_initial") or brand.get("agency_name", "A")[:1]).upper(),
        "DOWNLOADS_NOTE": brand.get("downloads_note", ""),
        "TASKS_NOTE": brand.get("tasks_note", ""),
        "FOOTER_TEXT": brand.get("footer_text", ""),
        "DISPLAY_FONT": brand.get("display_font", "Georgia, serif"),
        "BODY_FONT": brand.get("body_font", "system-ui, sans-serif"),
        "UI_FONT": brand.get("ui_font", "system-ui, sans-serif"),
        "BRAND_BG": brand.get("brand_bg", "#f4efe8"),
        "BRAND_BG_TOP": brand.get("brand_bg_top", "#ebe0cf"),
        "BRAND_SURFACE": brand.get("brand_surface", "#fcfcfc"),
        "BRAND_TEXT": brand.get("brand_text", "#121212"),
        "BRAND_MUTED": brand.get("brand_muted", "#665f57"),
        "BRAND_ACCENT": brand.get("brand_accent", "#007DA3"),
        "BRAND_ACCENT_2": brand.get("brand_accent_2", "#7F507A"),
        "BRAND_LINE": brand.get("brand_line", "#dfd3c3"),
        "BRAND_SHADOW": brand.get("brand_shadow", "rgba(32,22,12,0.12)"),
        "BRAND_GLOW_1": brand.get("brand_glow_1", "rgba(182,90,46,0.14)"),
        "BRAND_GLOW_2": brand.get("brand_glow_2", "rgba(15,118,110,0.12)"),
        "HERO_BG_1": brand.get("hero_bg_1", "#fcfcfc"),
        "HERO_BG_2": brand.get("hero_bg_2", "#fcfcfc"),
        "TABLE_HEAD_BG": brand.get("table_head_bg", "#f3eadb"),
        "PRIORITY_BG": brand.get("priority_bg", "#f8e0d7"),
        "PRIORITY_TEXT": brand.get("priority_text", "#8d3f1e"),
        "AUDIT_URL": url,
        "AUDIT_DOMAIN": domain,
        "AUDIT_DATE": audit_date,
        "ENV_PLATFORM": env_platform,
        "SCORE_VALUE": str(overall),
        "SCORE_RATING": rating,
        "CRITICAL_COUNT": str(critical_count),
        "WARNING_COUNT": str(warning_count),
        "INFO_COUNT": str(info_count),
        "PASS_COUNT": str(pass_count),
        "TOTAL_ISSUES": str(critical_count + warning_count + info_count),
        "TASK_COUNT": str(len(rows)),
        "CATEGORY_CARDS": _render_category_cards(scores),
        "DOWNLOAD_LINKS": _render_download_links(artifacts),
        "TASK_ROWS": _render_task_rows(rows),
        "DETAILED_SECTIONS": _render_detailed_sections(data, scores),
        "CATEGORY_CHART_DATA": _render_category_chart_data(scores),
    }

    html = template
    for key, val in substitutions.items():
        html = html.replace("{{" + key + "}}", str(val))
    return html


SEVERITY_RANK = {"Critical": 0, "Warning": 1, "Info": 2}

CATEGORY_LABELS = {
    "security": "Security Headers",
    "social": "Social Meta",
    "robots": "Robots & Crawlers",
    "broken_links": "Broken Links",
    "internal_links": "Internal Links",
    "redirects": "Redirects",
    "llms_txt": "AI Search (llms.txt)",
    "pagespeed": "Performance (CWV)",
    "onpage": "On-Page SEO",
    "readability": "Readability",
    "article": "Article Extractor",
    "entity": "Entity SEO",
    "link_profile": "Link Profile",
    "hreflang": "Hreflang",
    "duplicate_content": "Content Uniqueness",
    "environment": "Environment / Platform",
}

CATEGORY_OWNERS = {
    "security": "Web Engineering",
    "social": "Content / SEO",
    "robots": "Technical SEO",
    "broken_links": "Technical SEO",
    "internal_links": "Technical SEO",
    "redirects": "Technical SEO",
    "llms_txt": "Technical SEO",
    "pagespeed": "Performance / Frontend",
    "onpage": "Content / SEO",
    "readability": "Content / SEO",
    "article": "Content / SEO",
    "entity": "Content / SEO",
    "link_profile": "Technical SEO",
    "hreflang": "Technical SEO",
    "duplicate_content": "Content / SEO",
    "environment": "Web Engineering",
}


def normalize_severity(value: str) -> str:
    raw = (value or "info").strip().lower()
    if raw in ("critical", "high", "🔴"):
        return "Critical"
    if raw in ("warning", "warn", "medium", "⚠️"):
        return "Warning"
    return "Info"


def severity_from_text(text: str) -> str:
    if "🔴" in text:
        return "Critical"
    if "⚠️" in text:
        return "Warning"
    return "Info"


def timeline_for(severity: str) -> str:
    return {
        "Critical": "Week 1",
        "Warning": "Month 1",
        "Info": "Month 2-3",
    }.get(severity, "Triage")


def effort_for(severity: str) -> float:
    return {"Critical": 2.0, "Warning": 1.0, "Info": 0.5}.get(severity, 0.5)


def owner_for(category: str) -> str:
    return CATEGORY_OWNERS.get(category, "SEO Lead")


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category.replace("_", " ").title())


def _truncate(text: str, limit: int = 500) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def build_seo_tasks(data: dict) -> list:
    """Flatten section issues + environment fixes into prioritized task rows."""
    rows = []
    page_url = data.get("url", "")
    page_domain = data.get("domain", "")

    # Environment-specific fix plan
    for fix in data.get("environment_fixes", []) or []:
        sev = normalize_severity(fix.get("severity"))
        if sev == "Info" and (fix.get("severity") or "").lower() == "pass":
            continue
        rows.append({
            "page_url": page_url,
            "page_domain": page_domain,
            "category": "environment",
            "category_label": "Environment / Platform",
            "priority": sev,
            "finding": _truncate(fix.get("title") or fix.get("reason") or ""),
            "evidence": _truncate(fix.get("reason") or ""),
            "fix": _truncate(fix.get("fix") or ""),
        })

    # Per-section structured / string issues
    for section_name, section_data in (data.get("sections") or {}).items():
        if not isinstance(section_data, dict):
            continue
        for issue in section_data.get("issues", []) or []:
            if isinstance(issue, dict):
                finding = str(issue.get("finding") or issue.get("message") or "")
                if not finding:
                    continue
                rows.append({
                    "page_url": page_url,
                    "page_domain": page_domain,
                    "category": section_name,
                    "category_label": category_label(section_name),
                    "priority": normalize_severity(issue.get("severity")),
                    "finding": _truncate(finding),
                    "evidence": _truncate(str(issue.get("evidence") or "")),
                    "fix": _truncate(str(issue.get("fix") or "")),
                })
            elif isinstance(issue, str):
                rows.append({
                    "page_url": page_url,
                    "page_domain": page_domain,
                    "category": section_name,
                    "category_label": category_label(section_name),
                    "priority": severity_from_text(issue),
                    "finding": _truncate(issue),
                    "evidence": "",
                    "fix": "",
                })

        # Recommendations / opportunities surface as Info tasks when no fix text exists
        recs = section_data.get("recommendations") or section_data.get("suggestions") or []
        if isinstance(recs, dict):
            recs = [f"{k}: {v}" for k, v in recs.items()]
        opps = section_data.get("opportunities") or []
        if isinstance(opps, list):
            recs = list(recs) + list(opps)
        for rec in (recs or [])[:8]:
            if not isinstance(rec, str) or not rec.strip():
                continue
            rows.append({
                "page_url": page_url,
                "page_domain": page_domain,
                "category": section_name,
                "category_label": category_label(section_name),
                "priority": "Info",
                "finding": _truncate(rec),
                "evidence": "",
                "fix": _truncate(rec),
            })

    rows.sort(key=lambda r: (SEVERITY_RANK.get(r["priority"], 9), r["category"]))

    finalized = []
    for index, row in enumerate(rows, start=1):
        sev = row["priority"]
        finalized.append({
            "task_id": f"SEO-{index:03d}",
            "page_url": row["page_url"],
            "page_domain": row["page_domain"],
            "category": row["category"],
            "category_label": row["category_label"],
            "priority": sev,
            "finding": row["finding"],
            "evidence": row["evidence"],
            "fix": row["fix"],
            "owner": owner_for(row["category"]),
            "timeline": timeline_for(sev),
            "estimated_hours": effort_for(sev),
            "status": "Open",
        })
    return finalized


def write_seo_csv(path: str, rows: list) -> None:
    fieldnames = [
        "task_id", "page_url", "page_domain", "category", "category_label",
        "priority", "finding", "evidence", "fix",
        "owner", "timeline", "estimated_hours", "status",
    ]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _docx_paragraph(text: str) -> str:
    escaped = html_lib.escape(text or "")
    return (
        '<w:p><w:r><w:t xml:space="preserve">'
        f"{escaped}"
        "</w:t></w:r></w:p>"
    )


def _docx_heading(text: str, level: int = 1) -> str:
    size = {1: 36, 2: 30, 3: 26}.get(level, 24)
    escaped = html_lib.escape(text or "")
    return (
        f'<w:p><w:r><w:rPr><w:b/><w:sz w:val="{size}"/></w:rPr>'
        f'<w:t xml:space="preserve">{escaped}</w:t></w:r></w:p>'
    )


def _docx_pkg(path: str, title: str, body_xml: str) -> None:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body_xml}"
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" '
        'w:right="1440" w:bottom="1440" w:left="1440" w:header="708" '
        'w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>'
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""
    utc_now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    safe_title = html_lib.escape(title)
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{safe_title}</dc:title>
  <dc:creator>dd-seo skill</dc:creator>
  <cp:lastModifiedBy>dd-seo skill</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{utc_now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{utc_now}</dcterms:modified>
</cp:coreProperties>"""
    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>dd-seo skill</Application>
</Properties>"""
    with ZipFile(path, "w", ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("docProps/core.xml", core)
        docx.writestr("docProps/app.xml", app)
        docx.writestr("word/document.xml", document_xml)


def build_full_audit_docx(path: str, data: dict, scores: dict, rows: list) -> None:
    """Findings + scoring narrative — one DOCX per audit."""
    timestamp = data.get("timestamp", datetime.now().isoformat())
    overall = scores.get("overall", 0)
    rating = _score_rating(int(overall))
    domain = data.get("domain", "")
    url = data.get("url", "")
    summary = {
        "Critical": sum(1 for r in rows if r["priority"] == "Critical"),
        "Warning": sum(1 for r in rows if r["priority"] == "Warning"),
        "Info": sum(1 for r in rows if r["priority"] == "Info"),
    }

    body = []
    body.append(_docx_heading("SEO Full Audit Report", 1))
    body.append(_docx_paragraph(f"URL: {url}"))
    body.append(_docx_paragraph(f"Domain: {domain}"))
    body.append(_docx_paragraph(f"Generated: {timestamp}"))
    body.append(_docx_paragraph(f"Overall score: {overall}/100 — {rating}"))
    body.append(_docx_paragraph(
        f"Critical: {summary['Critical']} · Warning: {summary['Warning']} · Info: {summary['Info']}"
    ))
    body.append(_docx_paragraph(" "))

    body.append(_docx_heading("Category scores", 2))
    for key, label in CATEGORY_LABELS.items():
        if key == "environment":
            continue
        score = scores.get("categories", {}).get(key)
        if score is None:
            continue
        body.append(_docx_paragraph(f"{label}: {score}/100"))
    body.append(_docx_paragraph(" "))

    body.append(_docx_heading("Findings by severity", 2))
    if not rows:
        body.append(_docx_paragraph("No findings detected — site is healthy."))
    else:
        for sev_key in ("Critical", "Warning", "Info"):
            sev_rows = [r for r in rows if r["priority"] == sev_key]
            if not sev_rows:
                continue
            body.append(_docx_heading(f"{sev_key} ({len(sev_rows)})", 3))
            for r in sev_rows:
                body.append(_docx_paragraph(
                    f"[{r['task_id']}] {r['category_label']} — {r['finding']}"
                ))
                if r.get("evidence"):
                    body.append(_docx_paragraph(f"Evidence: {r['evidence']}"))
                if r.get("fix"):
                    body.append(_docx_paragraph(f"Fix: {r['fix']}"))
                body.append(_docx_paragraph(" "))

    _docx_pkg(path, "SEO Full Audit Report", "".join(body))


def build_action_plan_docx(path: str, data: dict, rows: list) -> None:
    """Prioritized remediation tasks — one DOCX per audit."""
    timestamp = data.get("timestamp", datetime.now().isoformat())
    domain = data.get("domain", "")
    url = data.get("url", "")

    body = []
    body.append(_docx_heading("SEO Action Plan", 1))
    body.append(_docx_paragraph(f"URL: {url}"))
    body.append(_docx_paragraph(f"Domain: {domain}"))
    body.append(_docx_paragraph(f"Generated: {timestamp}"))
    body.append(_docx_paragraph(f"Total tasks: {len(rows)}"))
    body.append(_docx_paragraph(" "))

    if not rows:
        body.append(_docx_paragraph("No remediation tasks needed."))
    else:
        for sev_key, label in (
            ("Critical", "P0 — Critical (Week 1)"),
            ("Warning",  "P1 — Important (Month 1)"),
            ("Info",     "P2 — Optimize (Month 2-3)"),
        ):
            sev_rows = [r for r in rows if r["priority"] == sev_key]
            if not sev_rows:
                continue
            body.append(_docx_heading(label, 2))
            for r in sev_rows:
                body.append(_docx_heading(f"{r['task_id']} — {r['finding']}", 3))
                body.append(_docx_paragraph(f"Category: {r['category_label']}"))
                body.append(_docx_paragraph(
                    f"Owner: {r['owner']} · Timeline: {r['timeline']} · "
                    f"Effort: {r['estimated_hours']}h"
                ))
                if r.get("evidence"):
                    body.append(_docx_paragraph(f"Evidence: {r['evidence']}"))
                if r.get("fix"):
                    body.append(_docx_paragraph(f"Fix: {r['fix']}"))
                body.append(_docx_paragraph(" "))

    _docx_pkg(path, "SEO Action Plan", "".join(body))


def derive_output_dir(url: str, override: str = None) -> str:
    """Default: web/<domain>-seo-audit-<YYYY-MM-DD>/"""
    if override:
        return os.path.abspath(override)
    domain = urlparse(url).netloc or "unknown"
    audit_date = datetime.now().strftime("%Y-%m-%d")
    return os.path.abspath(os.path.join("web", f"{domain}-seo-audit-{audit_date}"))


def _copy_template_assets(output_dir: str) -> None:
    src = os.path.join(TEMPLATES_DIR, "assets")
    if not os.path.isdir(src):
        return
    dst = os.path.join(output_dir, "assets")
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        s_path = os.path.join(src, name)
        if not os.path.isfile(s_path):
            continue
        with open(s_path, "rb") as fr:
            content = fr.read()
        with open(os.path.join(dst, name), "wb") as fw:
            fw.write(content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate SEO audit bundle (index.html + DOCX + CSV)"
    )
    parser.add_argument("url", help="Website URL to analyze")
    parser.add_argument(
        "--output-dir", "-o", default=None,
        help="Output directory (default: web/<domain>-seo-audit-<YYYY-MM-DD>/)",
    )
    args = parser.parse_args()

    data = collect_data(args.url)
    scores = calculate_overall_score(data)
    rows = build_seo_tasks(data)

    output_dir = derive_output_dir(args.url, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    _copy_template_assets(output_dir)

    artifacts = [
        {"kind": "DOCX", "label": "Full Audit Report",  "filename": "FULL-AUDIT-REPORT.docx"},
        {"kind": "DOCX", "label": "Action Plan",        "filename": "ACTION-PLAN.docx"},
        {"kind": "CSV",  "label": "Remediation Tasks",  "filename": "tasks.csv"},
    ]

    html = generate_html(data, scores, artifacts, rows)
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    csv_path = os.path.join(output_dir, "tasks.csv")
    write_seo_csv(csv_path, rows)

    full_docx_path = os.path.join(output_dir, "FULL-AUDIT-REPORT.docx")
    plan_docx_path = os.path.join(output_dir, "ACTION-PLAN.docx")
    build_full_audit_docx(full_docx_path, data, scores, rows)
    build_action_plan_docx(plan_docx_path, data, rows)

    print(f"\n✅ Bundle saved to: {output_dir}")
    print(f"   Dashboard:    {index_path}")
    print(f"   Full audit:   {full_docx_path}")
    print(f"   Action plan:  {plan_docx_path}")
    print(f"   Tasks CSV:    {csv_path}")
    print(f"   Overall:      {scores['overall']}/100  ({_score_rating(int(scores['overall']))})")
    print(f"   Tasks:        {len(rows)}")


if __name__ == "__main__":
    main()
