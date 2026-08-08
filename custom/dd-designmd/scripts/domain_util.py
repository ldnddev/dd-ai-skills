#!/usr/bin/env python3
"""Domain and URL helpers for dd-designmd."""

from __future__ import annotations

import re
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise ValueError("URL is empty")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def domain_from_url(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    host = (parsed.netloc or parsed.path or "site").lower()
    if "@" in host:
        host = host.split("@", 1)[-1]
    if ":" in host:
        host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    # filesystem-safe but keep dots
    host = re.sub(r"[^a-z0-9.-]+", "-", host).strip(".-") or "site"
    return host


def same_site(a: str, b: str) -> bool:
    return domain_from_url(a) == domain_from_url(b)
