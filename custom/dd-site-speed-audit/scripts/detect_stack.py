#!/usr/bin/env python3
"""
Detect CMS / framework / hosting signals from a page fetch.

Pure stdlib. Used to personalize speed recommendations.

Usage:
    python3 detect_stack.py https://example.com
    python3 detect_stack.py https://example.com --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

# (id, label, category, signals) — signals match against combined lowercased body+headers
STACK_RULES = [
    ("wordpress", "WordPress", "cms", [
        "wp-content", "wp-includes", "wordpress", "wp-json", "woocommerce",
    ]),
    ("drupal", "Drupal", "cms", ["drupal", "sites/default/files", "x-drupal"]),
    ("shopify", "Shopify", "cms", ["cdn.shopify.com", "shopify", "myshopify"]),
    ("squarespace", "Squarespace", "cms", ["squarespace", "static1.squarespace"]),
    ("wix", "Wix", "cms", ["wix.com", "parastorage", "wixstatic"]),
    ("webflow", "Webflow", "cms", ["webflow", "assets.website-files"]),
    ("nextjs", "Next.js", "framework", [
        "_next/static", "__next", "next-route-announcer", "x-nextjs",
    ]),
    ("nuxt", "Nuxt.js", "framework", ["_nuxt/", "__nuxt", "nuxt"]),
    ("react", "React", "framework", ["react", "react-dom", "data-reactroot"]),
    ("vue", "Vue.js", "framework", ["vue.js", "vue.min.js", "__vue__", "data-v-"]),
    ("angular", "Angular", "framework", ["ng-version", "angular", "ng-app"]),
    ("svelte", "Svelte", "framework", ["svelte"]),
    ("gatsby", "Gatsby", "framework", ["gatsby", "___gatsby"]),
    ("laravel", "Laravel", "backend", ["laravel_session", "x-powered-by: laravel"]),
    ("rails", "Ruby on Rails", "backend", ["x-powered-by: phusion", "rails", "csrf-token"]),
    ("django", "Django", "backend", ["csrfmiddlewaretoken", "django"]),
    ("cloudflare", "Cloudflare", "cdn", ["cloudflare", "cf-ray", "__cf_bm"]),
    ("fastly", "Fastly", "cdn", ["fastly", "x-served-by", "x-cache"]),
    ("akamai", "Akamai", "cdn", ["akamai", "x-akamai"]),
    ("vercel", "Vercel", "hosting", ["x-vercel", "vercel"]),
    ("netlify", "Netlify", "hosting", ["netlify", "x-nf-request-id"]),
    ("pantheon", "Pantheon", "hosting", ["pantheon", "x-pantheon"]),
    ("wpengine", "WP Engine", "hosting", ["wpengine", "wpe-backend"]),
    ("elementor", "Elementor", "builder", ["elementor"]),
    ("divi", "Divi", "builder", ["et-builder", "divi"]),
]


class _LinkMetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.generator = ""
        self.scripts: list[str] = []
        self.styles: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "meta" and ad.get("name", "").lower() == "generator":
            self.generator = ad.get("content", "")
        if tag == "script" and ad.get("src"):
            self.scripts.append(ad["src"])
        if tag == "link" and ad.get("rel") == "stylesheet" and ad.get("href"):
            self.styles.append(ad["href"])
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def fetch_page(url: str, timeout: int = 30) -> tuple[str, dict, str | None]:
    """Return (body, headers_dict, error)."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "dd-site-speed/1.0 (+https://ldnddev.com)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset, errors="replace")
            return body, headers, None
    except Exception as exc:
        return "", {}, str(exc)


def detect_stack(url: str, timeout: int = 30) -> dict:
    body, headers, error = fetch_page(url, timeout=timeout)
    header_blob = " ".join(f"{k}: {v}" for k, v in headers.items()).lower()
    body_lower = body.lower()
    combined = header_blob + "\n" + body_lower

    parser = _LinkMetaParser()
    if body:
        try:
            parser.feed(body[:500_000])
        except Exception:
            pass

    detected = []
    for stack_id, label, category, signals in STACK_RULES:
        hits = [s for s in signals if s.lower() in combined]
        if not hits:
            continue
        # Soft confidence: more distinct signal hits → higher confidence
        confidence = min(0.95, 0.35 + 0.15 * len(hits))
        # Boost for strong unique signals
        strong = {
            "wordpress": ["wp-content", "wp-includes"],
            "nextjs": ["_next/static", "x-nextjs"],
            "shopify": ["cdn.shopify.com"],
            "drupal": ["x-drupal"],
        }
        if any(s in combined for s in strong.get(stack_id, [])):
            confidence = max(confidence, 0.8)
        detected.append({
            "id": stack_id,
            "label": label,
            "category": category,
            "confidence": round(confidence, 2),
            "signals": hits[:6],
        })

    # Generator meta is high confidence
    gen = (parser.generator or "").strip()
    if gen:
        gen_lower = gen.lower()
        for stack_id, label, category, _ in STACK_RULES:
            if stack_id in gen_lower or label.lower() in gen_lower:
                existing = next((d for d in detected if d["id"] == stack_id), None)
                if existing:
                    existing["confidence"] = max(existing["confidence"], 0.9)
                    if "generator" not in existing["signals"]:
                        existing["signals"].append(f"generator:{gen[:80]}")
                else:
                    detected.append({
                        "id": stack_id,
                        "label": label,
                        "category": category,
                        "confidence": 0.9,
                        "signals": [f"generator:{gen[:80]}"],
                    })

    detected.sort(key=lambda d: d["confidence"], reverse=True)

    # Primary stack: prefer cms/framework over cdn/hosting for recommendations
    primary = None
    for preferred in ("cms", "framework", "builder", "backend", "hosting", "cdn"):
        for item in detected:
            if item["category"] == preferred:
                primary = item
                break
        if primary:
            break
    if not primary and detected:
        primary = detected[0]

    server = headers.get("server", "")
    powered = headers.get("x-powered-by", "")
    content_type = headers.get("content-type", "")

    # Resource hints for recommendations
    script_count = len(parser.scripts)
    style_count = len(parser.styles)
    large_third_party = []
    third_party_hosts = set()
    page_host = urlparse(url).netloc.lower()
    for src in parser.scripts + parser.styles:
        try:
            host = urlparse(src).netloc.lower()
        except Exception:
            continue
        if host and host != page_host and not host.endswith(page_host):
            third_party_hosts.add(host)

    return {
        "url": url,
        "error": error,
        "primary": primary,
        "detected": detected,
        "generator": gen,
        "server": server,
        "powered_by": powered,
        "content_type": content_type,
        "title": (parser.title or "").strip()[:200],
        "script_count": script_count,
        "stylesheet_count": style_count,
        "third_party_hosts": sorted(third_party_hosts)[:20],
        "labels": [d["label"] for d in detected],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect website technology stack")
    parser.add_argument("url", help="URL to inspect")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    result = detect_stack(args.url, timeout=args.timeout)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
    print(f"Stack detection — {result['url']}")
    if result.get("primary"):
        p = result["primary"]
        print(f"Primary: {p['label']} ({p['confidence']})")
    print(f"Detected: {', '.join(result.get('labels') or ['(none)'])}")
    if result.get("server"):
        print(f"Server: {result['server']}")
    if result.get("generator"):
        print(f"Generator: {result['generator']}")


if __name__ == "__main__":
    main()
