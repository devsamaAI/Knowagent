"""
tools/security_checker.py
==========================
Checks URLs for security risks and returns a score from 1 (dangerous) to 5 (safe).
Also extracts links embedded in text (e.g. YouTube description, article body).

WHAT YOU'LL LEARN HERE:
- Heuristic security scoring — rule-based risk assessment
- URL parsing with urllib
- Following redirects to reveal hidden destinations (URL shorteners)
- Regex for extracting URLs from free text
"""

import re
import logging
import requests
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ── Known-safe platforms (no further checks needed) ──────────────────────────

TRUSTED_DOMAINS = {
    "youtube.com", "youtu.be", "github.com", "stackoverflow.com",
    "medium.com", "dev.to", "arxiv.org", "wikipedia.org",
    "twitter.com", "x.com", "instagram.com", "linkedin.com",
    "reddit.com", "news.ycombinator.com", "substack.com",
    "notion.so", "figma.com", "npmjs.com", "pypi.org",
    "docs.python.org", "developer.mozilla.org", "w3schools.com",
    "cloudflare.com", "netlify.com", "vercel.com", "heroku.com",
    "huggingface.co", "kaggle.com", "colab.research.google.com",
}

# ── High-risk indicators ──────────────────────────────────────────────────────

SUSPICIOUS_TLDS = {
    ".xyz", ".tk", ".ml", ".ga", ".cf", ".gq",
    ".pw", ".top", ".click", ".download", ".work", ".party",
}

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "ow.ly", "goo.gl",
    "tiny.cc", "is.gd", "buff.ly", "rb.gy", "cutt.ly", "short.io",
}

# Regex patterns that suggest phishing / malicious URLs
PHISHING_PATTERNS = [
    # Lookalike domains: "paypal-secure.com", "amazon-login.net"
    r"(?:paypal|amazon|google|facebook|microsoft|apple|netflix|instagram|bank)[\w-]+\.\w+",
    # Phishing keywords in subdomain: "login.evil.com", "secure.fakecorp.com"
    r"\b(?:login|verify|account|secure|update|confirm|billing|suspended)\.",
    # Credential harvest page patterns
    r"/(?:login|signin|verify|account|update|confirm)\?",
]


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SecurityResult:
    score: int                          # 1 (dangerous) → 5 (safe)
    label: str                          # "Safe", "Likely Safe", etc.
    reasons: list = field(default_factory=list)
    final_url: Optional[str] = None     # Destination after redirects


SCORE_LABELS = {5: "Safe", 4: "Likely Safe", 3: "Unknown", 2: "Suspicious", 1: "Dangerous"}
SCORE_EMOJI  = {5: "🟢", 4: "🔵", 3: "⚪", 2: "🟡", 1: "🔴"}


# ── Main security check ───────────────────────────────────────────────────────

def check_url_security(url: str, _follow_redirects: bool = True) -> SecurityResult:
    """
    Analyse a URL and return a SecurityResult with a 1-5 score.

    LEARNING NOTE: This is a *heuristic* system — it uses rules, not ML.
    Real security tools (VirusTotal, Google Safe Browsing) check against
    live databases of known-bad URLs. Our approach is lightweight but covers
    the most common red flags.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return SecurityResult(score=1, label="Dangerous", reasons=["Invalid URL format"])

    hostname = (parsed.hostname or "").lower()
    base_domain = ".".join(hostname.split(".")[-2:]) if "." in hostname else hostname
    tld = "." + hostname.split(".")[-1] if "." in hostname else ""

    # ── Fast path: known-trusted domain ──────────────────────────────────────
    if base_domain in TRUSTED_DOMAINS:
        return SecurityResult(
            score=5, label="Safe",
            reasons=["Trusted platform"],
            final_url=url,
        )

    score = 3   # neutral start
    reasons = []

    # +1 HTTPS, -1 plain HTTP
    if parsed.scheme == "https":
        score += 1
        reasons.append("Uses HTTPS")
    else:
        score -= 1
        reasons.append("No HTTPS — connection is unencrypted")

    # -2  IP address as host (almost always suspicious)
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
        score -= 2
        reasons.append("IP address used instead of a domain name")

    # -1  High-risk TLD
    if tld in SUSPICIOUS_TLDS:
        score -= 1
        reasons.append(f"High-risk domain extension ({tld})")

    # -2  Phishing pattern
    for pattern in PHISHING_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            score -= 2
            reasons.append("URL matches known phishing pattern")
            break

    # ~   URL shortener → follow and re-check destination
    if base_domain in URL_SHORTENERS and _follow_redirects:
        reasons.append("URL shortener — checking destination")
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            final = resp.url
            if final and final != url:
                result = check_url_security(final, _follow_redirects=False)
                result.reasons.insert(0, f"Shortens to: {final[:70]}")
                return result
        except Exception:
            score -= 1
            reasons.append("Could not follow redirect to verify destination")

    # -1  Direct executable / archive download
    if re.search(r"\.(exe|zip|dmg|pkg|msi|bat|sh|ps1|apk)(\?|$)", parsed.path, re.I):
        score -= 1
        reasons.append("Direct file download link")

    score = max(1, min(5, score))
    if not reasons:
        reasons.append("No obvious red flags found")

    return SecurityResult(
        score=score,
        label=SCORE_LABELS[score],
        reasons=reasons,
        final_url=url,
    )


# ── Link extraction ───────────────────────────────────────────────────────────

def extract_urls_from_text(text: str) -> list:
    """
    Pull all http/https URLs out of a block of text.
    Used to find links mentioned in YouTube descriptions, article bodies, etc.
    """
    raw = re.findall(r'https?://[^\s\)\]\>\"\'<]+', text)

    seen = set()
    result = []
    for url in raw:
        url = url.rstrip(".,;:!?)")   # Strip trailing punctuation
        if url not in seen and len(url) > 12:
            seen.add(url)
            result.append(url)

    return result[:5]   # Cap at 5 to avoid flooding the reply
