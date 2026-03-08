"""
tools/fetcher.py
=================
Fetches raw content from URLs based on their type.

WHAT YOU'LL LEARN HERE:
- yt-dlp: industry-standard tool for extracting YouTube metadata
- requests + BeautifulSoup: web scraping fundamentals
- Error handling patterns (try/except with meaningful fallbacks)
- Why we separate "fetching" from "processing" (single responsibility)
"""

import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional

from config.settings import MAX_CONTENT_LENGTH
from tools.link_detector import DetectedLink, LinkType


@dataclass
class FetchedContent:
    """
    Raw content pulled from a URL, before AI processing.
    
    LEARNING NOTE: We use Optional[str] for fields that might not exist
    (e.g., a web article doesn't have a video duration).
    """
    url: str
    platform: str
    title: str
    description: str
    content_text: str               # Main body text for articles
    duration_seconds: Optional[int] = None     # For videos
    author: Optional[str] = None
    tags: list = field(default_factory=list)
    thumbnail: Optional[str] = None
    error: Optional[str] = None     # If something went wrong during fetch


def fetch_youtube(detected: DetectedLink) -> FetchedContent:
    """
    Extract YouTube video metadata WITHOUT downloading the video.
    yt-dlp is a Python library AND command-line tool — very powerful.
    
    LEARNING NOTE: We use extract_info(url, download=False) to just get
    metadata. download=True would actually download the video file.
    """
    try:
        import yt_dlp

        # ydl_opts controls yt-dlp behavior
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "ignoreerrors": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # process=False skips format selection (avoids "format not available" errors)
            # We only need metadata, not actual video streams
            info = ydl.extract_info(detected.url, download=False, process=False)

        if not info:
            raise ValueError("yt-dlp returned no metadata for this URL")

        # process=False can return inaccurate duration when YouTube's API is partially blocked.
        # YouTube always embeds the true duration as `lengthSeconds` in the page HTML — use that.
        duration = None
        try:
            yt_page = requests.get(
                detected.url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            # Scope to "videoDetails" to get the main video duration,
            # not a related/recommended video that may appear first in the page
            match = re.search(r'"videoDetails".*?"lengthSeconds":"(\d+)"', yt_page.text, re.DOTALL)
            if match:
                duration = int(match.group(1))
        except Exception:
            pass
        if not duration:
            duration = info.get("duration")  # Fallback to yt-dlp value

        return FetchedContent(
            url=detected.clean_url,
            platform="YouTube",
            title=info.get("title", "Unknown Title"),
            description=(info.get("description") or "")[:2000],  # Cap at 2000 chars
            content_text=info.get("description") or "",
            duration_seconds=duration,
            author=info.get("uploader"),
            tags=info.get("tags", [])[:10],  # First 10 tags only
            thumbnail=info.get("thumbnail"),
        )

    except Exception as e:
        return FetchedContent(
            url=detected.url,
            platform="YouTube",
            title="Could not fetch",
            description="",
            content_text="",
            error=str(e)
        )


def fetch_github(detected: DetectedLink) -> FetchedContent:
    """
    Fetch GitHub repository info using GitHub's PUBLIC API (no auth needed
    for public repos, 60 requests/hour limit).
    
    LEARNING NOTE: GitHub API returns JSON — a common pattern for REST APIs.
    We parse it with response.json() which gives us a Python dictionary.
    """
    try:
        # Extract owner/repo from URL
        # e.g. https://github.com/langchain-ai/langchain  →  langchain-ai/langchain
        match = re.search(r"github\.com/([\w-]+/[\w-]+)", detected.url)
        if not match:
            raise ValueError("Could not parse GitHub URL")

        repo_path = match.group(1).rstrip("/")

        # GitHub REST API v3
        api_url = f"https://api.github.com/repos/{repo_path}"
        headers = {"Accept": "application/vnd.github.v3+json"}

        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises exception if status != 200
        data = response.json()

        # Also try to fetch the README
        readme_text = ""
        try:
            readme_url = f"https://api.github.com/repos/{repo_path}/readme"
            readme_resp = requests.get(readme_url, headers=headers, timeout=10)
            if readme_resp.status_code == 200:
                import base64
                readme_data = readme_resp.json()
                readme_text = base64.b64decode(readme_data["content"]).decode("utf-8")
                readme_text = readme_text[:3000]  # First 3000 chars of README
        except Exception:
            pass  # README fetch is optional

        return FetchedContent(
            url=detected.clean_url,
            platform="GitHub",
            title=data.get("full_name", repo_path),
            description=data.get("description") or "",
            content_text=readme_text,
            author=data.get("owner", {}).get("login"),
            tags=data.get("topics", []),
        )

    except Exception as e:
        return FetchedContent(
            url=detected.url,
            platform="GitHub",
            title="Could not fetch",
            description="",
            content_text="",
            error=str(e)
        )


def fetch_article(detected: DetectedLink) -> FetchedContent:
    """
    Scrape a generic web article using requests + BeautifulSoup.
    
    LEARNING NOTE: BeautifulSoup parses HTML. We look for <article>, <main>,
    or <p> tags to find the main content. Web scraping is messy because every
    site has a different structure — this is a best-effort approach.
    """
    try:
        headers = {
            # Pretend to be a browser — some sites block Python's default User-Agent
            "User-Agent": "Mozilla/5.0 (compatible; PocketAgent/1.0)"
        }
        response = requests.get(detected.url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # --- Extract title ---
        title = ""
        if soup.title:
            title = soup.title.string or ""
        # Try OG title (Open Graph — used by Twitter cards, Facebook previews)
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", title)

        # --- Extract description ---
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "")
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            description = og_desc.get("content", description)

        # --- Extract main content text ---
        # Remove nav, footer, scripts, styles — they're noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try to find main content area
        content_area = (
            soup.find("article") or
            soup.find("main") or
            soup.find(id=re.compile(r"content|article|post", re.I)) or
            soup.find(class_=re.compile(r"content|article|post", re.I)) or
            soup.body
        )

        content_text = ""
        if content_area:
            # Get all paragraph text
            paragraphs = content_area.find_all("p")
            content_text = " ".join(p.get_text(strip=True) for p in paragraphs)
            content_text = content_text[:MAX_CONTENT_LENGTH]

        return FetchedContent(
            url=detected.clean_url,
            platform=detected.platform_name,
            title=title.strip(),
            description=description.strip(),
            content_text=content_text.strip(),
        )

    except Exception as e:
        return FetchedContent(
            url=detected.url,
            platform=detected.platform_name,
            title="Could not fetch",
            description="",
            content_text="",
            error=str(e)
        )


def fetch_instagram(detected: DetectedLink) -> FetchedContent:
    """
    Fetch Instagram post/reel metadata via Open Graph tags.

    LEARNING NOTE: Instagram blocks most scrapers and requires login for most
    content. However, public posts still expose Open Graph meta tags (og:title,
    og:description, og:image) which give us the caption and thumbnail.
    We mimic a mobile browser UA to maximise chances of getting a response.
    """
    try:
        headers = {
            # Mobile Safari UA — Instagram serves lighter pages to mobile browsers
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                "Mobile/15E148 Safari/604.1"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = requests.get(detected.url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        def og(prop):
            tag = soup.find("meta", property=f"og:{prop}")
            return (tag.get("content") or "").strip() if tag else ""

        title       = og("title")
        description = og("description")
        thumbnail   = og("image")

        # Instagram og:title for reels is usually "username on Instagram: caption"
        # Extract author from it
        author = None
        if " on Instagram" in title:
            author = title.split(" on Instagram")[0].strip()

        if not title:
            raise ValueError(
                "Instagram returned no metadata — the post may be private or "
                "Instagram blocked the request. Try opening the link in a browser."
            )

        return FetchedContent(
            url=detected.clean_url,
            platform="Instagram",
            title=title,
            description=description,
            content_text=description,
            author=author,
            thumbnail=thumbnail,
        )

    except Exception as e:
        return FetchedContent(
            url=detected.url,
            platform="Instagram",
            title="Could not fetch",
            description="",
            content_text="",
            error=str(e),
        )


def fetch_content(detected: DetectedLink) -> FetchedContent:
    """
    MAIN ROUTER: calls the right fetcher based on link type.
    This is the "tool selector" pattern used in AI agents.
    """
    if detected.link_type == LinkType.YOUTUBE:
        return fetch_youtube(detected)
    elif detected.link_type == LinkType.GITHUB:
        return fetch_github(detected)
    elif detected.link_type == LinkType.INSTAGRAM:
        return fetch_instagram(detected)
    else:
        return fetch_article(detected)
