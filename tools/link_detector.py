"""
tools/link_detector.py
=======================
Figures out WHAT TYPE of link the user shared.

WHAT YOU'LL LEARN HERE:
- Regular expressions (regex) for pattern matching
- urllib for URL parsing
- Python dataclasses — a clean way to group related data
- The concept of "routing" in agents (decide which tool to use based on input)
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse
from enum import Enum


class LinkType(Enum):
    """All the link types our agent can handle."""
    YOUTUBE   = "youtube"
    GITHUB    = "github"
    TWITTER   = "twitter"
    INSTAGRAM = "instagram"
    ARTICLE   = "article"   # Generic web article / blog post
    UNKNOWN   = "unknown"


@dataclass
class DetectedLink:
    """
    A dataclass holds structured data cleanly.
    Think of it like a typed dictionary with dot-access.
    """
    url: str
    link_type: LinkType
    clean_url: str          # URL without tracking params
    platform_name: str      # Human readable: "YouTube", "GitHub", etc.


# ── Pattern matching rules ───────────────────────────────────────────────────

YOUTUBE_PATTERNS = [
    r"youtube\.com/watch",
    r"youtu\.be/",
    r"youtube\.com/shorts/",
    r"youtube\.com/live/",
]

GITHUB_PATTERNS = [
    r"github\.com/[\w-]+/[\w-]+",   # github.com/user/repo
]

TWITTER_PATTERNS = [
    r"twitter\.com/",
    r"x\.com/",
]

INSTAGRAM_PATTERNS = [
    r"instagram\.com/",
    r"instagr\.am/",
]


def clean_url(url: str) -> str:
    """
    Remove tracking parameters from URLs.
    e.g. youtube.com/watch?v=abc123&feature=share  →  youtube.com/watch?v=abc123
    
    LEARNING NOTE: URL tracking params (utm_source, feature, si, etc.) are
    added by platforms to track where traffic comes from. We strip them.
    """
    parsed = urlparse(url)
    
    # Parameters to KEEP for each platform (everything else is tracking noise)
    keep_params = {
        "youtube.com": ["v", "t"],          # video ID and timestamp
        "youtu.be": [],                      # video ID is in the path
        "github.com": [],                    # no params needed
    }
    
    domain = parsed.netloc.replace("www.", "")
    
    # If we have rules for this domain, filter params
    if domain in keep_params:
        allowed = keep_params[domain]
        if allowed and parsed.query:
            # Rebuild query string with only allowed params
            from urllib.parse import parse_qs, urlencode
            params = parse_qs(parsed.query)
            filtered = {k: v for k, v in params.items() if k in allowed}
            clean_query = urlencode(filtered, doseq=True)
            return parsed._replace(query=clean_query).geturl()
        else:
            # Drop all query params
            return parsed._replace(query="", fragment="").geturl()
    
    return url


def detect_link(url: str) -> DetectedLink:
    """
    Main function: takes a URL string, returns a DetectedLink with type info.
    
    This is the "router" of our agent — decides which fetcher to call next.
    """
    url = url.strip()
    
    # Check each pattern set in order
    for pattern in YOUTUBE_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return DetectedLink(
                url=url,
                link_type=LinkType.YOUTUBE,
                clean_url=clean_url(url),
                platform_name="YouTube"
            )
    
    for pattern in GITHUB_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return DetectedLink(
                url=url,
                link_type=LinkType.GITHUB,
                clean_url=clean_url(url),
                platform_name="GitHub"
            )
    
    for pattern in TWITTER_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return DetectedLink(
                url=url,
                link_type=LinkType.TWITTER,
                clean_url=clean_url(url),
                platform_name="Twitter/X"
            )
    
    for pattern in INSTAGRAM_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return DetectedLink(
                url=url,
                link_type=LinkType.INSTAGRAM,
                clean_url=clean_url(url),
                platform_name="Instagram"
            )
    
    # Default: treat as a generic web article
    return DetectedLink(
        url=url,
        link_type=LinkType.ARTICLE,
        clean_url=url,
        platform_name="Web Article"
    )
