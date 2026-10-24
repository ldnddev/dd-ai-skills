#!/usr/bin/env python3
"""Generate an HTML dashboard comparing multiple websites.

v1.3: 42 strictly-required fields. v1.1 added final_url/redirected/word_count/
h2/h3/images_missing_alt/external_link_count/has_favicon/has_canonical/
json_ld_count/server/powered_by. v1.3 adds homepage competitive signals
(h1_text, hero_subhead, nav_labels, primary_cta, cta_texts, cta_count,
form_field_count, offer_type, pricing_visible, trust_signals, page_types)
from the same homepage parse — no extra network. Parallel analysis
(ThreadPoolExecutor, default 4 workers). Still pure stdlib.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


def _resolve_default_template() -> Path:
    """Find templates/dashboard.html across the repo layout and a flattened install.

    Repo layout: <root>/skills/dd-site-compare/scripts/ -> parents[3]/templates.
    Flat (Codex) install: <skill>/scripts/ -> parents[1]/templates.
    First existing candidate wins; falls back to the repo-layout path.
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "templates" / "dashboard.html",
        here.parents[1] / "templates" / "dashboard.html",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


DEFAULT_TEMPLATE_PATH = _resolve_default_template()

FIELD_ORDER = [
    "URL",
    "final_url",
    "redirected",
    "status_code",
    "response_time",
    "page_size",
    "total_page_load_size",
    "resource_count",
    "js_file_count",
    "css_file_count",
    "largest_item",
    "trackers",
    "title",
    "meta_description",
    "h1_text",
    "hero_subhead",
    "nav_labels",
    "primary_cta",
    "cta_texts",
    "cta_count",
    "form_field_count",
    "offer_type",
    "pricing_visible",
    "trust_signals",
    "page_types",
    "h1_count",
    "h2_count",
    "h3_count",
    "image_count",
    "images_missing_alt",
    "link_count",
    "external_link_count",
    "technologies",
    "keywords",
    "mobile_responsive",
    "has_favicon",
    "has_canonical",
    "json_ld_count",
    "word_count",
    "server",
    "powered_by",
    "error",
]

TRACKING_PATTERNS: Dict[str, Sequence[str]] = {
    "Google Analytics": [
        r"google-analytics\.com",
        r"analytics\.google\.com",
        r"gtag\(",
        r"gtag/js",
        r"\bUA-\d+-\d+\b",
        r"\bG-[A-Z0-9]+\b",
        r"\bGA4\b",
    ],
    "Google Tag Manager": [
        r"googletagmanager\.com",
        r"gtm\.js",
        r"\bGTM-[A-Z0-9]+\b",
    ],
    "Google Ads": [
        r"googleadservices\.com",
        r"doubleclick\.net",
        r"conversion_async\.js",
    ],
    "Facebook Pixel": [
        r"connect\.facebook\.net",
        r"fbevents\.js",
        r"fbq\(",
        r"facebook\.com/tr",
    ],
    "Hotjar": [
        r"static\.hotjar\.com",
        r"hotjar\.js",
        r"hj\(",
    ],
    "LinkedIn Insight": [
        r"px\.ads\.linkedin\.com",
        r"linkedin\.com/px",
        r"li_fat_id",
        r"insight\.min\.js",
    ],
    "Twitter Pixel": [
        r"ads-twitter\.com",
        r"twitter\.com/i/adsct",
        r"twtrPixel",
    ],
    "TikTok Pixel": [
        r"analytics\.tiktok\.com",
        r"ttq\.",
        r"events\.js",
    ],
    "Generic Tracking Pixel": [
        r"pixel\.quantserve\.com",
        r"tracking\.[\w.-]+",
        r"1x1\.gif",
        r"clear\.gif",
    ],
    # v1.1 additions
    "Microsoft Clarity": [r"clarity\.ms", r"clarity.js"],
    "Plausible": [r"plausible\.io"],
    "Matomo": [r"matomo\.(js|php)", r"piwik\.(js|php)"],
    "Segment": [r"segment\.com", r"analytics\.segment", r"ajs_"],
    "Heap": [r"heap\.io", r"heap.js"],
}

TECH_PATTERNS: Dict[str, Sequence[str]] = {
    "Google Analytics": [r"google-analytics\.com", r"gtag/js", r"\bG-[A-Z0-9]+\b"],
    "Google Tag Manager": [r"googletagmanager\.com", r"\bGTM-[A-Z0-9]+\b"],
    "WordPress": [r"wp-content", r"wp-includes", r"wordpress"],
    "Drupal": [r"Drupal\.settings", r"drupalSettings", r"/sites/default/", r"\bDrupal\b"],
    "jQuery": [r"jquery(?:\.min)?\.js", r"\bjQuery\b"],
    "Bootstrap": [r"bootstrap(?:\.min)?\.(?:css|js)", r"\bbootstrap\b"],
    "React": [r"react(?:\.production)?(?:\.min)?\.js", r"data-reactroot", r"__REACT"],
    "Vue": [r"vue(?:\.runtime)?(?:\.min)?\.js", r"\bVue\b"],
    "Angular": [r"angular(?:\.min)?\.js", r"ng-version", r"\bng-app\b"],
    "Shopify": [r"cdn\.shopify\.com", r"Shopify\.theme"],
    "Squarespace": [r"squarespace\.com", r"static\.squarespace\.com"],
    "Webflow": [r"webflow\.js", r"webflow\.com"],
    # v1.1 additions (meta generator, headers, common modern signals)
    "Next.js": [r"__NEXT_DATA__", r"next/router", r"next/static"],
    "Nuxt": [r"__NUXT__", r"nuxt"],
    "Svelte": [r"svelte", r"__svelte"],
    "Astro": [r"astro", r"data-astro"],
    "Tailwind": [r"tailwind", r"tw-", r"bg-"],
    "Meta Generator": [r'name="generator"'],
    "Cloudflare": [r"cloudflare"],
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

STOPWORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}

# v1.3: homepage competitive signals (same parse, no extra fetches)
CTA_PATTERN = re.compile(
    r"\b("
    r"free\s+trial|try\s+(it\s+)?free|start\s+(your\s+)?(free\s+)?(trial|now)|"
    r"get\s+started|book\s+(a\s+)?demo|request\s+(a\s+)?demo|schedule\s+(a\s+)?demo|"
    r"see\s+(a\s+)?demo|watch\s+(a\s+)?demo|get\s+(a\s+)?demo|"
    r"contact\s+sales|talk\s+to\s+(sales|us|an?\s+expert)|"
    r"request\s+(a\s+)?quote|get\s+a\s+quote|"
    r"sign\s*up|create\s+(an?\s+)?account|register|"
    r"buy\s+now|subscribe|request\s+access|join\s+(now|free|us)|"
    r"start\s+building|try\s+(it|now)"
    r")\b",
    re.I,
)
CTA_SKIP_PATTERN = re.compile(
    r"(?:"
    r"^(?:log\s*in|log\s*out|sign\s*in|sign\s*out|my\s+account|account|cart|"
    r"basket|search|menu|close|skip\s+to\b.*|accept(?:\s+all)?(?:\s+cookies)?|"
    r"reject(?:\s+all)?|cookie(?:\s+settings)?|privacy\s+settings|"
    r"learn\s+more|read\s+more|see\s+more|view\s+all|show\s+more)$"
    r"|\bsubmenu"
    r"|\b(?:open|close|toggle)\s+(?:menu|nav|navigation|search)\b"
    r")",
    re.I,
)
BUTTON_CLASS_PATTERN = re.compile(
    r"\bbtn\b|\bbutton\b|\bcta\b|btn-|button-|dd-button",
    re.I,
)
HERO_SKIP_PATTERN = re.compile(
    r"we use cookies|cookie policy|privacy policy|accept cookies|this site uses cookies",
    re.I,
)
VISIBLE_PRICE_PATTERN = re.compile(
    r"(?:[$£€]\s?\d|\b(?:usd|eur|gbp)\s?\d|"
    r"\d[\d,]*(?:\.\d+)?\s?(?:/\s*mo\b|per\s+month|/month|per\s+user))",
    re.I,
)
INPUT_FIELD_TYPES = {
    "",
    "text",
    "email",
    "tel",
    "password",
    "number",
    "search",
    "url",
    "date",
    "datetime-local",
    "month",
    "week",
    "time",
    "checkbox",
    "radio",
    "file",
    "color",
    "range",
}
SKIP_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}
CHROME_CLASS_PATTERN = re.compile(
    r"\b(navbar|nav-bar|main-nav|main-menu|primary-nav|site-nav|global-nav|"
    r"nav-menu|site-header|masthead|site-footer)\b",
    re.I,
)
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# (page_type, href patterns, label patterns) — nav/header links only
PAGE_TYPE_RULES: Sequence[Tuple[str, Sequence[str], Sequence[str]]] = (
    ("pricing", (r"/pricing\b", r"/plans?\b", r"/packages?\b"), (r"\bpricing\b", r"\bplans\b", r"\bpackages\b")),
    ("features", (r"/features?\b", r"/product(?:s)?\b", r"/platform\b", r"/capabilities\b"), (r"\bfeatures?\b", r"\bproduct\b", r"\bplatform\b")),
    ("integrations", (r"/integrations?\b", r"/apps\b", r"/connectors?\b", r"/marketplace\b"), (r"\bintegrations?\b", r"\bmarketplace\b")),
    ("alternatives", (r"/alternatives?\b", r"/compare\b", r"/vs\b", r"/competitors?\b"), (r"\balternatives?\b", r"\bcompare\b")),
    ("blog", (r"/blog\b", r"/news\b", r"/articles?\b", r"/resources?\b", r"/learn\b"), (r"\bblog\b", r"\bnews\b", r"\bresources?\b")),
    ("docs", (r"/docs?\b", r"/documentation\b", r"/help\b", r"/developers?\b", r"/api\b", r"/guides?\b"), (r"\bdocs?\b", r"\bdocumentation\b", r"\bhelp center\b", r"\bdevelopers?\b")),
    ("changelog", (r"/changelog\b", r"/releases?\b", r"/whats-new\b", r"/roadmap\b", r"/updates?\b"), (r"\bchangelog\b", r"\breleases?\b", r"\bwhat.?s new\b", r"\broadmap\b")),
)
TRUST_PATTERNS: Dict[str, Sequence[str]] = {
    "G2": [r"g2\.com", r"g2crowd", r"\bg2 leader\b", r"\bg2 crowd\b"],
    "Capterra": [r"capterra"],
    "Trustpilot": [r"trustpilot"],
    "Gartner": [r"gartner\.com", r"magic quadrant"],
    "Clutch": [r"clutch\.co"],
    "SOC 2": [r"\bsoc\s*2\b", r"soc-2"],
    "ISO 27001": [r"iso\s*27001", r"iso27001"],
    "PCI DSS": [r"\bpci[-\s]?dss\b"],
    "As seen in": [r"\bas seen in\b"],
}


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status_code: Optional[int]
    elapsed: float
    content: bytes
    content_type: str
    charset: Optional[str]
    server: Optional[str] = None
    powered_by: Optional[str] = None
    error: Optional[str] = None


@dataclass
class LargestItem:
    url: str
    bytes: int


@dataclass
class SiteResult:
    url: str
    final_url: Optional[str] = None
    redirected: bool = False
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    page_size: Optional[int] = None
    total_page_load_size: Optional[int] = None
    resource_count: int = 0
    js_file_count: int = 0
    css_file_count: int = 0
    largest_item: Optional[LargestItem] = None
    trackers: List[str] = field(default_factory=list)
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1_text: Optional[str] = None
    hero_subhead: Optional[str] = None
    nav_labels: List[str] = field(default_factory=list)
    primary_cta: Optional[str] = None
    cta_texts: List[str] = field(default_factory=list)
    cta_count: int = 0
    form_field_count: int = 0
    offer_type: str = "unknown"
    pricing_visible: bool = False
    trust_signals: List[str] = field(default_factory=list)
    page_types: List[str] = field(default_factory=list)
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    image_count: int = 0
    images_missing_alt: int = 0
    link_count: int = 0
    external_link_count: int = 0
    technologies: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    mobile_responsive: Optional[bool] = None
    has_favicon: bool = False
    has_canonical: bool = False
    json_ld_count: int = 0
    word_count: int = 0
    server: Optional[str] = None
    powered_by: Optional[str] = None
    error: Optional[str] = None

    def to_output_row(self) -> Dict[str, object]:
        largest_item = None
        if self.largest_item:
            largest_item = asdict(self.largest_item)

        return {
            "URL": self.url,
            "final_url": self.final_url or self.url,
            "redirected": bool(self.redirected),
            "status_code": self.status_code,
            "response_time": self.response_time,
            "page_size": self.page_size,
            "total_page_load_size": self.total_page_load_size,
            "resource_count": self.resource_count,
            "js_file_count": self.js_file_count,
            "css_file_count": self.css_file_count,
            "largest_item": largest_item,
            "trackers": self.trackers,
            "title": self.title,
            "meta_description": self.meta_description,
            "h1_text": self.h1_text,
            "hero_subhead": self.hero_subhead,
            "nav_labels": self.nav_labels,
            "primary_cta": self.primary_cta,
            "cta_texts": self.cta_texts,
            "cta_count": self.cta_count,
            "form_field_count": self.form_field_count,
            "offer_type": self.offer_type,
            "pricing_visible": bool(self.pricing_visible),
            "trust_signals": self.trust_signals,
            "page_types": self.page_types,
            "h1_count": self.h1_count,
            "h2_count": self.h2_count,
            "h3_count": self.h3_count,
            "image_count": self.image_count,
            "images_missing_alt": self.images_missing_alt,
            "link_count": self.link_count,
            "external_link_count": self.external_link_count,
            "technologies": self.technologies,
            "keywords": self.keywords,
            "mobile_responsive": self.mobile_responsive,
            "has_favicon": self.has_favicon,
            "has_canonical": self.has_canonical,
            "json_ld_count": self.json_ld_count,
            "word_count": self.word_count,
            "server": self.server,
            "powered_by": self.powered_by,
            "error": self.error or "None",
        }


class ParsedHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: List[str] = []
        self.paragraph_parts: List[str] = []
        self.heading_parts: List[str] = []  # v1.1: for keyword weighting + word_count
        self.in_title = False
        self.paragraph_depth = 0
        self.capture_script = False
        self.current_script_parts: List[str] = []
        self.inline_scripts: List[str] = []
        self.script_srcs: List[str] = []
        self.stylesheets: List[str] = []
        self.images: List[Dict[str, Optional[str]]] = []
        self.sources: List[str] = []
        self.meta_description: Optional[str] = None
        self.mobile_responsive = False
        self.h1_count = 0
        self.h2_count = 0
        self.h3_count = 0
        self.image_count = 0
        self.images_missing_alt = 0  # v1.1
        self.link_count = 0
        self.external_link_count = 0  # computed later with base host
        self.has_favicon = False  # v1.1
        self.has_canonical = False  # v1.1
        self.json_ld_count = 0  # v1.1
        self._in_heading = False  # v1.1 temp flag for data capture
        # v1.3 competitive-signal capture
        self.h1_texts: List[str] = []
        self.h2_texts: List[str] = []
        self.flow: List[Tuple[str, str]] = []  # (h1|h2|p, text) outside nav/footer
        self.links: List[Dict[str, object]] = []
        self.buttons: List[str] = []
        self.form_field_count = 0
        self._open: List[Tuple[str, Optional[str]]] = []
        self._skip_depth = 0
        self._form_depth = 0
        self._current_heading_tag: Optional[str] = None
        self._current_heading_parts: List[str] = []
        self._current_p_parts: List[str] = []
        self._current_link: Optional[Dict[str, object]] = None
        self._link_parts: List[str] = []
        self._current_button = False
        self._button_parts: List[str] = []

    @property
    def title(self) -> Optional[str]:
        value = " ".join("".join(self.title_parts).split())
        return value or None

    @property
    def paragraph_text(self) -> str:
        return " ".join(" ".join(self.paragraph_parts).split())

    @property
    def heading_text(self) -> str:
        # v1.1: headings (h1/h2/h3) for better keyword extraction + word_count
        return " ".join(" ".join(self.heading_parts).split())

    def _in_region(self, *kinds: str) -> bool:
        return any(kind in kinds for _tag, kind in self._open if kind)

    def _chrome_kind(self, tag: str, attrs_dict: Dict[str, str]) -> Optional[str]:
        role = attrs_dict.get("role", "").lower()
        if tag == "nav" or role == "navigation":
            return "nav"
        if tag == "header" or role == "banner":
            return "header"
        if tag == "footer" or role == "contentinfo":
            return "footer"
        blob = f"{attrs_dict.get('class', '')} {attrs_dict.get('id', '')}"
        match = CHROME_CLASS_PATTERN.search(blob)
        if not match:
            return None
        token = match.group(1).lower()
        if "footer" in token:
            return "footer"
        if "header" in token or token == "masthead":
            return "header"
        return "nav"

    def _push_open(self, tag: str, attrs_dict: Dict[str, str]) -> None:
        if tag in VOID_TAGS:
            return
        self._open.append((tag, self._chrome_kind(tag, attrs_dict)))

    def _pop_open(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index][0] == tag:
                del self._open[index:]
                return

    def _is_button_like(self, attrs_dict: Dict[str, str]) -> bool:
        if attrs_dict.get("role", "").lower() == "button":
            return True
        return bool(BUTTON_CLASS_PATTERN.search(attrs_dict.get("class", "")))

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attrs_dict = {name.lower(): value or "" for name, value in attrs}

        if tag in ("script", "style"):
            self._skip_depth += 1
        self._push_open(tag, attrs_dict)
        if tag == "form":
            self._form_depth += 1

        if tag == "title":
            self.in_title = True
        elif tag == "p":
            self.paragraph_depth += 1
            self._current_p_parts = []
        elif tag in ("h1", "h2", "h3"):
            # v1.1 counts + capture text for keywords/word_count
            if tag == "h1":
                self.h1_count += 1
            elif tag == "h2":
                self.h2_count += 1
            else:
                self.h3_count += 1
            self._in_heading = True
            self._current_heading_tag = tag
            self._current_heading_parts = []
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            if name == "description" and attrs_dict.get("content") and not self.meta_description:
                self.meta_description = " ".join(attrs_dict["content"].split())
            if name == "viewport":
                self.mobile_responsive = True
            if prop == "og:description" and attrs_dict.get("content") and not self.meta_description:
                self.meta_description = " ".join(attrs_dict["content"].split())
            if name == "generator":
                # will be picked up by TECH_PATTERNS too, but record presence
                pass
        elif tag == "a":
            self.link_count += 1
            if self._current_link is not None:
                self._finish_link()
            self._current_link = {
                "href": attrs_dict.get("href", ""),
                "in_nav": self._in_region("nav", "header"),
                "in_footer": self._in_region("footer"),
                "button_like": self._is_button_like(attrs_dict),
                "aria": attrs_dict.get("aria-label", "").strip(),
            }
            self._link_parts = []
        elif tag == "button":
            if self._skip_depth:
                pass
            else:
                self._current_button = True
                self._button_parts = []
                aria = attrs_dict.get("aria-label", "").strip()
                if aria:
                    self._button_parts.append(aria)
        elif tag == "input":
            input_type = attrs_dict.get("type", "").strip().lower()
            if input_type in SKIP_INPUT_TYPES:
                if input_type in {"submit", "button"} and self._form_depth:
                    label = (attrs_dict.get("value") or attrs_dict.get("aria-label") or "").strip()
                    if label:
                        self.buttons.append(label)
            elif self._form_depth and (input_type in INPUT_FIELD_TYPES or input_type not in SKIP_INPUT_TYPES):
                self.form_field_count += 1
        elif tag in ("select", "textarea"):
            if self._form_depth and not self._skip_depth:
                self.form_field_count += 1
        elif tag == "img":
            self.image_count += 1
            alt = (attrs_dict.get("alt") or "").strip()
            if not alt:
                self.images_missing_alt += 1
            self.images.append(
                {
                    "src": attrs_dict.get("src"),
                    "srcset": attrs_dict.get("srcset"),
                    "width": attrs_dict.get("width"),
                    "height": attrs_dict.get("height"),
                    "alt": alt or None,
                }
            )
            if self._current_link is not None and alt and not self._link_parts:
                self._link_parts.append(alt)
        elif tag == "script":
            src = attrs_dict.get("src")
            typ = attrs_dict.get("type", "").lower()
            if src:
                self.script_srcs.append(src)
            else:
                self.capture_script = True
                self.current_script_parts = []
            if "ld+json" in typ or "application/ld+json" in typ:
                self.json_ld_count += 1
        elif tag == "link":
            rel = attrs_dict.get("rel", "").lower()
            href = attrs_dict.get("href")
            if href and "stylesheet" in rel:
                self.stylesheets.append(href)
            if "icon" in rel or "shortcut icon" in rel:
                self.has_favicon = True
            if "canonical" in rel:
                self.has_canonical = True
        elif tag == "source":
            src = attrs_dict.get("src")
            srcset = attrs_dict.get("srcset")
            if src:
                self.sources.append(src)
            if srcset:
                self.sources.extend(parse_srcset(srcset))

    def _finish_link(self) -> None:
        if self._current_link is None:
            return
        text = " ".join("".join(self._link_parts).split())
        if not text:
            text = str(self._current_link.get("aria") or "")
        self._current_link["text"] = text
        self.links.append(self._current_link)
        self._current_link = None
        self._link_parts = []

    def _finish_heading(self) -> None:
        text = " ".join("".join(self._current_heading_parts).split())
        tag = self._current_heading_tag
        if tag == "h1" and text:
            self.h1_texts.append(text)
        elif tag == "h2" and text:
            self.h2_texts.append(text)
        if tag in ("h1", "h2") and text and not self._in_region("nav", "footer") and not self._skip_depth:
            self.flow.append((tag, text))
        self._current_heading_tag = None
        self._current_heading_parts = []
        self._in_heading = False

    def _finish_paragraph(self) -> None:
        text = " ".join("".join(self._current_p_parts).split())
        if text and not self._in_region("nav", "footer") and not self._skip_depth:
            self.flow.append(("p", text))
        self._current_p_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == "p" and self.paragraph_depth:
            self.paragraph_depth -= 1
            self._finish_paragraph()
        elif tag in ("h1", "h2", "h3"):
            self._finish_heading()
        elif tag == "a":
            self._finish_link()
        elif tag == "button":
            if self._current_button:
                text = " ".join("".join(self._button_parts).split())
                if text:
                    self.buttons.append(text)
            self._current_button = False
            self._button_parts = []
        elif tag == "form" and self._form_depth:
            self._form_depth -= 1
        elif tag == "script" and self.capture_script:
            script_text = "".join(self.current_script_parts)
            if script_text.strip():
                self.inline_scripts.append(script_text)
            self.capture_script = False
            self.current_script_parts = []
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1
        self._pop_open(tag)

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.paragraph_depth:
            self.paragraph_parts.append(data)
            self._current_p_parts.append(data)
        if getattr(self, "_in_heading", False):
            self.heading_parts.append(data)
            self._current_heading_parts.append(data)
        if self.capture_script:
            self.current_script_parts.append(data)
        if self._current_link is not None and not self._skip_depth:
            self._link_parts.append(data)
        if self._current_button and not self._skip_depth:
            self._button_parts.append(data)


def _clip(text: Optional[str], limit: int = 240) -> Optional[str]:
    if not text:
        return None
    collapsed = " ".join(text.split())
    if not collapsed:
        return None
    if len(collapsed) <= limit:
        return collapsed
    trimmed = collapsed[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:-")
    return (trimmed or collapsed[: limit - 1]) + "…"


def _unique_keep(values: Iterable[str], limit: int) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for raw in values:
        text = " ".join((raw or "").split())
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _is_hero_candidate(text: str, h1_text: Optional[str]) -> bool:
    collapsed = " ".join(text.split())
    if len(collapsed) < 20:
        return False
    if h1_text and collapsed.casefold() == h1_text.casefold():
        return False
    if HERO_SKIP_PATTERN.search(collapsed):
        return False
    return True


def _classify_offer(text: str) -> Optional[str]:
    lowered = text.lower()
    if re.search(r"\b(free\s+trial|try\s+(it\s+)?free|start\s+.*\bfree\b|\btrial\b)\b", lowered):
        return "trial"
    if re.search(r"\bdemo\b", lowered):
        return "demo"
    if re.search(
        r"\b(contact\s+sales|talk\s+to\s+sales|request\s+(a\s+)?quote|get\s+a\s+quote|"
        r"talk\s+to\s+(an?\s+)?expert)\b",
        lowered,
    ):
        return "contact_sales"
    if re.search(
        r"\b(sign\s*up|register|create\s+(an?\s+)?account|get\s+started|join\s+(now|free|us))\b",
        lowered,
    ):
        return "signup"
    return None


def _is_cta_label(text: str, button_like: bool) -> bool:
    collapsed = " ".join(text.split())
    if len(collapsed) < 2 or len(collapsed) > 60:
        return False
    if CTA_SKIP_PATTERN.search(collapsed):
        return False
    if CTA_PATTERN.search(collapsed):
        return True
    return bool(button_like)


def _page_types_from_links(links: Sequence[Dict[str, object]]) -> List[str]:
    found: List[str] = []
    seen: Set[str] = set()
    nav_links = [link for link in links if link.get("in_nav")]
    for name, href_pats, label_pats in PAGE_TYPE_RULES:
        for link in nav_links:
            href = str(link.get("href") or "")
            label = str(link.get("text") or "")
            href_hit = any(re.search(pat, href, flags=re.I) for pat in href_pats)
            label_hit = any(re.search(pat, label, flags=re.I) for pat in label_pats)
            if href_hit or label_hit:
                if name not in seen:
                    seen.add(name)
                    found.append(name)
                break
    return found


def derive_competitive_signals(parser: ParsedHTML, html_text: str) -> Dict[str, object]:
    """Homepage positioning / conversion / page-type fields from one parse."""
    h1_text = _clip(parser.h1_texts[0], 240) if parser.h1_texts else None

    hero_subhead: Optional[str] = None
    seen_h1 = False
    for kind, text in parser.flow:
        if kind == "h1":
            seen_h1 = True
            continue
        if seen_h1 and kind in ("p", "h2") and _is_hero_candidate(text, h1_text):
            hero_subhead = _clip(text, 280)
            break
    if hero_subhead is None:
        for kind, text in parser.flow:
            if kind == "p" and _is_hero_candidate(text, h1_text):
                hero_subhead = _clip(text, 280)
                break

    nav_labels = _unique_keep(
        (str(link.get("text") or "") for link in parser.links if link.get("in_nav")),
        24,
    )
    nav_labels = [label for label in nav_labels if 1 <= len(label) <= 60]

    cta_candidates: List[Tuple[str, bool, bool]] = []  # text, in_nav, conversion_hit
    for link in parser.links:
        text = str(link.get("text") or "")
        button_like = bool(link.get("button_like"))
        if _is_cta_label(text, button_like):
            cta_candidates.append((text, bool(link.get("in_nav")), bool(CTA_PATTERN.search(text))))
    for text in parser.buttons:
        if _is_cta_label(text, True):
            cta_candidates.append((text, False, bool(CTA_PATTERN.search(text))))

    cta_texts = _unique_keep((text for text, _nav, _conv in cta_candidates), 12)

    primary_cta: Optional[str] = None
    for text, in_nav, conv in cta_candidates:
        if in_nav and conv:
            primary_cta = _clip(text, 80)
            break
    if primary_cta is None:
        for text, _in_nav, conv in cta_candidates:
            if conv:
                primary_cta = _clip(text, 80)
                break
    if primary_cta is None and cta_texts:
        primary_cta = _clip(cta_texts[0], 80)

    offer_type = "unknown"
    for source in (primary_cta, *cta_texts, h1_text, hero_subhead):
        if not source:
            continue
        classified = _classify_offer(source)
        if classified:
            offer_type = classified
            break

    visible_bits = [
        h1_text or "",
        hero_subhead or "",
        parser.heading_text,
        parser.paragraph_text,
        " ".join(str(link.get("text") or "") for link in parser.links),
        " ".join(parser.buttons),
    ]
    page_types = _page_types_from_links(parser.links)
    pricing_visible = bool(VISIBLE_PRICE_PATTERN.search(" ".join(visible_bits))) or ("pricing" in page_types)

    trust_inputs = [
        html_text,
        " ".join(img.get("alt") or "" for img in parser.images),
        " ".join(str(link.get("href") or "") for link in parser.links),
        parser.paragraph_text,
        parser.heading_text,
    ]
    trust_signals = sorted(detect_patterns(TRUST_PATTERNS, trust_inputs))

    return {
        "h1_text": h1_text,
        "hero_subhead": hero_subhead,
        "nav_labels": nav_labels,
        "primary_cta": primary_cta,
        "cta_texts": cta_texts,
        "cta_count": len(cta_texts),
        "form_field_count": parser.form_field_count,
        "offer_type": offer_type,
        "pricing_visible": pricing_visible,
        "trust_signals": trust_signals,
        "page_types": page_types,
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare multiple websites and generate an HTML dashboard."
    )
    parser.add_argument("urls", nargs="*", help="Website URLs to compare.")
    parser.add_argument("--urls-file", help="Text file with one URL per line.")
    parser.add_argument(
        "-o",
        "--output",
        default="website_comparison_dashboard.html",
        help="HTML dashboard output path.",
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE_PATH),
        help="Dashboard HTML template path.",
    )
    parser.add_argument("--json-output", help="Optional JSON output path for raw results.")
    parser.add_argument("--timeout", type=float, default=12.0, help="Homepage request timeout.")
    parser.add_argument(
        "--resource-timeout",
        type=float,
        default=6.0,
        help="Linked resource request timeout.",
    )
    parser.add_argument(
        "--max-resources",
        type=int,
        default=150,
        help="Maximum linked resources to fetch per website.",
    )
    parser.add_argument(
        "--skip-resources",
        action="store_true",
        help="Skip linked resource fetching and only analyze homepage HTML.",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header for requests.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent site analyses (default 4; use 1 for old serial behavior).",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Place output into the project-level web/ folder using the naming convention "
             "<primary-domain>-compare-audit-YYYY-MM-DD/ (HTML as index.html, JSON as data.json). "
             "Uses the first URL's registrable domain. Recommended for audits.9rooftops.com runs. "
             "If --output is also given, only its basename is used inside the dated folder.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    urls = collect_urls(args.urls, args.urls_file)
    if not urls:
        print("No URLs provided. Pass URLs as arguments or use --urls-file.", file=sys.stderr)
        return 2

    # Handle --web: place into project web/<domain>-compare-audit-YYYY-MM-DD/
    if getattr(args, "web", False):
        primary = get_primary_domain(urls[0])
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        folder_name = f"{primary}-compare-audit-{date_str}"
        # Anchor to the directory the user invoked from (their project root),
        # not the script's install location — the script may live in a plugin dir.
        project_root = Path.cwd()
        target_dir = project_root / "web" / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)

        if args.output == "website_comparison_dashboard.html":
            out_basename = "index.html"
        else:
            out_basename = Path(args.output).name
        args.output = str(target_dir / out_basename)

        if args.json_output is None:
            json_basename = "data.json"
        else:
            json_basename = Path(args.json_output).name
        args.json_output = str(target_dir / json_basename)

        print(f"[web] Using output folder: {target_dir}", file=sys.stderr)

    workers = max(1, int(getattr(args, "workers", 4) or 1))
    start_all = time.perf_counter()

    results: List[SiteResult] = []
    if workers == 1 or len(urls) == 1:
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Analyzing {url} ...", file=sys.stderr)
            t0 = time.perf_counter()
            r = analyze_site(
                url=url,
                timeout=args.timeout,
                resource_timeout=args.resource_timeout,
                max_resources=max(args.max_resources, 0),
                skip_resources=args.skip_resources,
                user_agent=args.user_agent,
            )
            dt = time.perf_counter() - t0
            status = "OK" if not (r.error and r.error != "None") else "ERR"
            print(f"[{i}/{len(urls)}] {url} -> {status} in {dt:.2f}s", file=sys.stderr)
            results.append(r)
    else:
        print(f"Analyzing {len(urls)} site(s) with up to {workers} workers...", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            future_to_url = {
                ex.submit(
                    analyze_site,
                    url=url,
                    timeout=args.timeout,
                    resource_timeout=args.resource_timeout,
                    max_resources=max(args.max_resources, 0),
                    skip_resources=args.skip_resources,
                    user_agent=args.user_agent,
                ): url
                for url in urls
            }
            for i, fut in enumerate(as_completed(future_to_url), 1):
                url = future_to_url[fut]
                try:
                    r = fut.result()
                    results.append(r)
                    status = "OK" if not (r.error and r.error != "None") else "ERR"
                    print(f"[{i}/{len(urls)}] {url} -> {status}", file=sys.stderr)
                except Exception as exc:  # pragma: no cover - defensive
                    err_r = SiteResult(url=url, error=str(exc))
                    results.append(err_r)
                    print(f"[{i}/{len(urls)}] {url} -> EXC {exc}", file=sys.stderr)

    # preserve original URL order
    url_to_result = {r.url: r for r in results}
    ordered_results = [url_to_result.get(u, SiteResult(url=u, error="internal ordering")) for u in urls]

    total_dt = time.perf_counter() - start_all
    dashboard_payload = build_dashboard_payload(
        ordered_results,
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )
    html_output = render_dashboard(dashboard_payload, Path(args.template))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_output, encoding="utf-8")

    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(dashboard_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    error_count = sum(1 for result in ordered_results if result.error and result.error != "None")
    print(f"Wrote HTML dashboard: {output_path} (in {total_dt:.2f}s total)")
    if args.json_output:
        print(f"Wrote JSON results: {args.json_output}")
    if error_count:
        print(f"Completed with {error_count} URL error(s).", file=sys.stderr)
    return 0


def collect_urls(url_args: Sequence[str], urls_file: Optional[str]) -> List[str]:
    candidates: List[str] = list(url_args)
    if urls_file:
        for line in Path(urls_file).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                candidates.append(stripped)

    seen: Set[str] = set()
    urls: List[str] = []
    for candidate in candidates:
        normalized = normalize_url(candidate)
        if normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)
    return urls


def normalize_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url, flags=re.I):
        url = f"https://{url}"
    return url


def get_primary_domain(url: str) -> str:
    """Return a safe folder name from the first URL's domain (e.g. 'example.com')."""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().strip()
        if not host:
            host = parsed.path.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        if ":" in host:
            host = host.split(":", 1)[0]
        # Sanitize for filesystem (keep dots and hyphens)
        host = re.sub(r"[^a-z0-9.-]", "-", host).strip("-.")
        return host or "unknown-site"
    except Exception:
        return "unknown-site"


def analyze_site(
    url: str,
    timeout: float,
    resource_timeout: float,
    max_resources: int,
    skip_resources: bool,
    user_agent: str,
) -> SiteResult:
    result = SiteResult(url=url)
    try:
        homepage = fetch_url(url, timeout=timeout, user_agent=user_agent)
    except Exception as exc:
        result.error = str(exc)
        result.total_page_load_size = 0
        result.largest_item = None
        result.mobile_responsive = False
        result.final_url = url
        result.redirected = False
        result.server = None
        result.powered_by = None
        return result

    result.status_code = homepage.status_code
    result.response_time = homepage.elapsed
    result.page_size = len(homepage.content)
    result.total_page_load_size = len(homepage.content)
    result.largest_item = LargestItem(homepage.final_url or url, len(homepage.content))
    result.final_url = homepage.final_url or url
    result.redirected = (result.final_url != url)
    result.server = homepage.server
    result.powered_by = homepage.powered_by

    if homepage.error:
        result.error = homepage.error

    html_text = decode_content(homepage.content, homepage.charset)
    parser = ParsedHTML()
    parser.feed(html_text)

    result.title = parser.title
    result.meta_description = parser.meta_description
    result.h1_count = parser.h1_count
    result.h2_count = parser.h2_count
    result.h3_count = parser.h3_count
    result.image_count = parser.image_count
    result.images_missing_alt = parser.images_missing_alt
    result.link_count = parser.link_count
    result.mobile_responsive = parser.mobile_responsive
    result.has_favicon = parser.has_favicon
    result.has_canonical = parser.has_canonical
    result.json_ld_count = parser.json_ld_count

    signals = derive_competitive_signals(parser, html_text)
    for key, value in signals.items():
        setattr(result, key, value)

    # v1.1: compute external links using final base host
    base_url = homepage.final_url or url
    try:
        base_host = urlparse(base_url).netloc.lower()
    except Exception:
        base_host = ""
    # re-walk <a> via images? No -- parser doesn't store raw <a> hrefs yet.
    # We approximate by re-parsing? To keep cheap, we do a light second pass or
    # enhance parser later. For v1.1 we count via a simple re-scan of html_text
    # for external a tags (good enough, no double network).
    result.external_link_count = _count_external_links(html_text, base_host)

    # word_count from title+meta+headings+paragraphs (cheap)
    all_text_for_count = " ".join([
        result.title or "",
        result.meta_description or "",
        parser.heading_text,
        parser.paragraph_text,
    ])
    result.word_count = len(re.findall(r"[A-Za-z0-9']+", all_text_for_count))

    result.keywords = extract_keywords(
        title=result.title or "",
        meta_description=result.meta_description or "",
        body_text=parser.paragraph_text,
        heading_text=parser.heading_text,  # v1.1 extra source
    )

    resources = collect_resources(parser, base_url)
    resource_texts: List[str] = []
    resource_urls: List[str] = list(resources.keys())

    if not skip_resources:
        for resource_url, kinds in list(resources.items())[:max_resources]:
            fetched = fetch_resource(resource_url, timeout=resource_timeout, user_agent=user_agent)
            if not fetched or fetched.status_code is None or fetched.status_code >= 400:
                continue

            size = len(fetched.content)
            result.total_page_load_size = (result.total_page_load_size or 0) + size
            result.resource_count += 1
            if "js" in kinds:
                result.js_file_count += 1
            if "css" in kinds:
                result.css_file_count += 1
            if result.largest_item is None or size > result.largest_item.bytes:
                result.largest_item = LargestItem(fetched.final_url or resource_url, size)
            if should_scan_resource(fetched.content_type, resource_url, size):
                resource_texts.append(decode_content(fetched.content[:2_000_000], fetched.charset))

    tracking_inputs = [html_text, *parser.inline_scripts, *parser.script_srcs, *resource_urls, *resource_texts]
    result.trackers = sorted(detect_patterns(TRACKING_PATTERNS, tracking_inputs))
    if has_explicit_tracking_pixel(parser.images):
        result.trackers = sorted(set(result.trackers) | {"Generic Tracking Pixel"})

    technology_inputs = [
        html_text,
        *parser.inline_scripts,
        *parser.script_srcs,
        *parser.stylesheets,
        *resource_texts,
        # v1.1: include headers for server/powered_by detection too
        f"{result.server or ''} {result.powered_by or ''}",
    ]
    result.technologies = sorted(detect_patterns(TECH_PATTERNS, technology_inputs))

    if not result.error:
        result.error = None
    return result


def fetch_url(url: str, timeout: float, user_agent: str) -> FetchResult:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    start = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read()
            elapsed = time.perf_counter() - start
            return FetchResult(
                requested_url=url,
                final_url=response.geturl(),
                status_code=response.getcode(),
                elapsed=elapsed,
                content=content,
                content_type=response.headers.get("content-type", ""),
                charset=response.headers.get_content_charset(),
                server=response.headers.get("server"),
                powered_by=response.headers.get("x-powered-by")
                or response.headers.get("x-generator")
                or response.headers.get("x-aspnet-version"),
            )
    except HTTPError as exc:
        content = exc.read()
        elapsed = time.perf_counter() - start
        return FetchResult(
            requested_url=url,
            final_url=exc.geturl(),
            status_code=exc.code,
            elapsed=elapsed,
            content=content,
            content_type=exc.headers.get("content-type", "") if exc.headers else "",
            charset=exc.headers.get_content_charset() if exc.headers else None,
            server=exc.headers.get("server") if exc.headers else None,
            powered_by=(
                (exc.headers.get("x-powered-by") or exc.headers.get("x-generator"))
                if exc.headers else None
            ),
            error=f"HTTP {exc.code}: {exc.reason}",
        )
    except URLError as exc:
        elapsed = time.perf_counter() - start
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(f"Request failed after {elapsed:.2f}s: {reason}") from exc


def fetch_resource(url: str, timeout: float, user_agent: str) -> Optional[FetchResult]:
    try:
        return fetch_url(url, timeout=timeout, user_agent=user_agent)
    except Exception:
        return None


def decode_content(content: bytes, charset: Optional[str]) -> str:
    encodings = [charset, "utf-8", "latin-1"]
    for encoding in encodings:
        if not encoding:
            continue
        try:
            return content.decode(encoding, errors="replace")
        except LookupError:
            continue
    return content.decode("utf-8", errors="replace")


def collect_resources(parser: ParsedHTML, base_url: str) -> "OrderedDict[str, Set[str]]":
    resources: "OrderedDict[str, Set[str]]" = OrderedDict()

    def add(raw_url: Optional[str], kind: str) -> None:
        if not raw_url:
            return
        full_url = urljoin(base_url, raw_url.strip())
        parsed = urlparse(full_url)
        if parsed.scheme not in {"http", "https"}:
            return
        resources.setdefault(full_url, set()).add(kind)

    for image in parser.images:
        add(image.get("src"), "image")
        for srcset_url in parse_srcset(image.get("srcset")):
            add(srcset_url, "image")
    for href in parser.stylesheets:
        add(href, "css")
    for src in parser.script_srcs:
        add(src, "js")
    for src in parser.sources:
        add(src, "media")

    return resources


def parse_srcset(srcset: Optional[str]) -> List[str]:
    if not srcset:
        return []
    urls: List[str] = []
    for item in srcset.split(","):
        first_part = item.strip().split(" ")[0]
        if first_part:
            urls.append(first_part)
    return urls


def should_scan_resource(content_type: str, url: str, size: int) -> bool:
    if size > 2_000_000:
        return False
    haystack = f"{content_type} {url}".lower()
    return any(
        token in haystack
        for token in (
            "javascript",
            "ecmascript",
            "json",
            "text/",
            ".js",
            ".css",
            ".html",
            ".htm",
        )
    )


def detect_patterns(patterns: Dict[str, Sequence[str]], texts: Iterable[str]) -> Set[str]:
    found: Set[str] = set()
    text_list = [text for text in texts if text]
    for name, name_patterns in patterns.items():
        for text in text_list:
            if any(re.search(pattern, text, flags=re.I) for pattern in name_patterns):
                found.add(name)
                break
    return found


def has_explicit_tracking_pixel(images: Sequence[Dict[str, Optional[str]]]) -> bool:
    for image in images:
        width = (image.get("width") or "").strip().lower().replace("px", "")
        height = (image.get("height") or "").strip().lower().replace("px", "")
        if width == "1" and height == "1":
            return True
    return False


def _count_external_links(html_text: str, base_host: str) -> int:
    """Lightweight external <a> counter (v1.1). Avoids full re-parse for speed."""
    if not html_text or not base_host:
        return 0
    count = 0
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\']', html_text, flags=re.I):
        href = m.group(1).strip()
        if href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
        try:
            p = urlparse(urljoin("https://dummy", href))  # normalize relative
            h = (p.netloc or "").lower()
            if h and h != base_host:
                count += 1
        except Exception:
            pass
    return count


def extract_keywords(
    title: str,
    meta_description: str,
    body_text: str,
    heading_text: str = "",  # v1.1
    top_n: int = 15,
    max_ngram: int = 3,
) -> List[str]:
    phrase_scores: Dict[str, float] = {}
    phrase_counts: Dict[str, int] = {}
    sources = (
        (title, 3.0),
        (meta_description, 2.0),
        (heading_text, 2.2),  # v1.1: headings are strong signals
        (body_text, 1.0),
    )

    for text, source_weight in sources:
        for tokens in keyword_token_segments(text):
            for ngram_size in range(1, max_ngram + 1):
                if len(tokens) < ngram_size:
                    continue
                for index in range(0, len(tokens) - ngram_size + 1):
                    phrase_tokens = tokens[index : index + ngram_size]
                    if len(set(phrase_tokens)) == 1 and ngram_size > 1:
                        continue
                    phrase = " ".join(phrase_tokens)
                    length_weight = 1.0 + ((ngram_size - 1) * 0.45)
                    phrase_scores[phrase] = phrase_scores.get(phrase, 0.0) + source_weight * length_weight
                    phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

    ranked = sorted(
        phrase_scores.items(),
        key=lambda item: (
            -(item[1] + (phrase_counts[item[0]] * 0.2)),
            -len(item[0].split()),
            item[0],
        ),
    )

    selected: List[str] = []
    for phrase, _score in ranked:
        if is_redundant_keyword(phrase, selected):
            continue
        selected.append(phrase)
        if len(selected) >= top_n:
            break
    return selected


def keyword_token_segments(text: str) -> List[List[str]]:
    segments: List[List[str]] = []
    for chunk in re.split(r"[.!?;:,\n\r\t()[\]{}<>/|]+", text.lower()):
        current: List[str] = []
        for raw_token in re.findall(r"[A-Za-z][A-Za-z0-9']+", chunk):
            token = raw_token.strip("'")
            if len(token) < 2 or token in STOPWORDS:
                if current:
                    segments.append(current)
                    current = []
                continue
            current.append(token)
        if current:
            segments.append(current)
    return segments


def is_redundant_keyword(phrase: str, selected: Sequence[str]) -> bool:
    phrase_words = phrase.split()
    if not phrase_words:
        return True
    phrase_word_set = set(phrase_words)

    for existing in selected:
        existing_words = existing.split()
        existing_word_set = set(existing_words)
        if phrase == existing:
            return True
        if len(phrase_words) == 1 and phrase_words[0] in existing_word_set:
            return True
        if len(existing_words) > len(phrase_words) and phrase_word_set.issubset(existing_word_set):
            return True
    return False


def build_dashboard_payload(results: Sequence[SiteResult], generated_at: str) -> Dict[str, object]:
    primary_url = results[0].url if results else ""
    return {
        "generated_at": generated_at,
        "primary_url": primary_url,
        "field_order": FIELD_ORDER,
        "results": [result.to_output_row() for result in results],
    }


def load_brand_config(template_path: Path) -> Dict[str, object]:
    """Load templates/brand.json beside the dashboard template (if present)."""
    brand_path = template_path.parent / "brand.json"
    if not brand_path.is_file():
        return {}
    return json.loads(brand_path.read_text(encoding="utf-8"))


def render_dashboard(payload: Dict[str, object], template_path: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    placeholder = "__DASHBOARD_DATA_JSON__"
    if placeholder not in template:
        raise ValueError(f"Dashboard template is missing {placeholder}")
    brand = load_brand_config(template_path)
    logo = str(brand.get("agency_logo") or "/assets/imgs/logo-full-black-text.svg")
    logo_dark = str(brand.get("agency_logo_dark") or "/assets/imgs/logo-full-white-text.svg")
    html = template.replace(placeholder, json_for_html(payload))
    html = html.replace("{{AGENCY_LOGO}}", logo)
    html = html.replace("{{AGENCY_LOGO_DARK}}", logo_dark)
    return html



def json_for_html(payload: Dict[str, object]) -> str:
    return (
        json.dumps(payload, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


if __name__ == "__main__":
    raise SystemExit(main())
