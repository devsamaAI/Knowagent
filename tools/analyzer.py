"""
tools/analyzer.py
==================
The AI brain — sends fetched content to Gemini and gets structured insights back.

WHAT YOU'LL LEARN HERE:
- Prompt engineering: how you word instructions matters A LOT
- Structured output: asking LLMs to respond in JSON so you can parse it
- Pydantic: validating and parsing structured data (used by LangChain heavily)
- Why "temperature=0" makes outputs more consistent/deterministic
- The concept of a "system prompt" vs "user prompt"
"""

import json
import re
import logging
from groq import Groq
from dataclasses import dataclass, field
from typing import Optional

from config.settings import GROQ_API_KEY
from tools.fetcher import FetchedContent

logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)


@dataclass
class Analysis:
    """
    The structured output we want from the AI.
    Every field comes from parsing the LLM's JSON response.
    """
    category: str           # "Video Tutorial", "GitHub Repo", "Article", etc.
    summary: str            # 2-3 sentence summary
    key_topics: list        # ["Python", "Machine Learning", "APIs"]
    difficulty: int         # 1 (beginner) to 5 (expert)
    difficulty_label: str   # "Beginner", "Intermediate", "Advanced", "Expert"
    time_estimate: str      # "15 minutes", "2 hours", etc.
    prerequisites: list     # ["Basic Python", "Git basics"]
    why_useful: str         # One sentence on why this is worth saving
    tags: list              # Searchable tags for later retrieval
    
    # Optional fields that may not always be present
    error: Optional[str] = None


# ── Prompt Engineering ───────────────────────────────────────────────────────
# This is the most important part. How you write this prompt determines
# the quality of every analysis. Experiment with this!

SYSTEM_PROMPT = """You are a personal knowledge curator AI.
Your job is to analyze content that a user has saved and provide structured, 
useful metadata to help them decide when and how to consume it.

Always respond with ONLY valid JSON. No markdown, no explanation, just JSON.
"""

def build_analysis_prompt(content: FetchedContent) -> str:
    """
    Build the user prompt — we inject the fetched content here.
    
    LEARNING NOTE: f-strings with multi-line content like this are a common
    pattern for building LLM prompts programmatically.
    """
    
    # Format duration if available
    duration_str = ""
    if content.duration_seconds:
        mins = content.duration_seconds // 60
        secs = content.duration_seconds % 60
        duration_str = f"\nVideo Duration: {mins}m {secs}s (use this for time_estimate)"
    
    return f"""Analyze this saved content and return a JSON object.

Platform: {content.platform}
URL: {content.url}
Title: {content.title}
Author/Creator: {content.author or "Unknown"}
Description: {content.description[:500]}{duration_str}

Content Preview:
{content.content_text[:2000] if content.content_text else "(no content text available)"}

Return EXACTLY this JSON structure (fill in all fields):
{{
  "category": "one of: Video Tutorial, YouTube Talk, GitHub Repo, Tech Article, Blog Post, Course, Tool/Library, Research Paper, Other",
  "summary": "2-3 sentences explaining what this is and what you'll learn",
  "key_topics": ["topic1", "topic2", "topic3"],
  "difficulty": 1,
  "difficulty_label": "one of: Beginner, Intermediate, Advanced, Expert",
  "time_estimate": "for videos: estimate from duration or title context. For articles: reading time.",
  "prerequisites": ["prerequisite1", "prerequisite2"],
  "why_useful": "one sentence: the single most compelling reason to engage with this",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

For difficulty: 1=complete beginner, 2=some experience, 3=intermediate, 4=advanced, 5=expert only
For prerequisites: list concrete skills/knowledge needed BEFORE this makes sense
"""


def analyze_content(content: FetchedContent) -> Analysis:
    """
    Send content to Gemini, parse the JSON response into an Analysis object.
    
    LEARNING NOTE: LLMs can "hallucinate" invalid JSON. That's why we have
    multiple fallback strategies in the parsing section below.
    """
    
    # If fetching failed, we can still try to analyze with just the URL
    if content.error and not content.title:
        return Analysis(
            category="Unknown",
            summary=f"Could not fetch content from {content.url}",
            key_topics=[],
            difficulty=3,
            difficulty_label="Unknown",
            time_estimate="Unknown",
            prerequisites=[],
            why_useful="Save and review manually",
            tags=[content.platform.lower()],
            error=content.error
        )

    try:
        prompt = build_analysis_prompt(content)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=800,
        )
        response_text = response.choices[0].message.content

        # --- Parse the JSON response ---
        # Sometimes Gemini wraps JSON in ```json ... ``` markdown — strip it
        response_text = re.sub(r"```json\s*", "", response_text)
        response_text = re.sub(r"```\s*", "", response_text)
        response_text = response_text.strip()

        data = json.loads(response_text)

        return Analysis(
            category=data.get("category", "Unknown"),
            summary=data.get("summary", "No summary available"),
            key_topics=data.get("key_topics", []),
            difficulty=int(data.get("difficulty", 3)),
            difficulty_label=data.get("difficulty_label", "Intermediate"),
            time_estimate=data.get("time_estimate", "Unknown"),
            prerequisites=data.get("prerequisites", []),
            why_useful=data.get("why_useful", ""),
            tags=data.get("tags", []),
        )

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}\nResponse was: {response_text[:500]}")
        return Analysis(
            category="Unknown",
            summary="AI analysis failed — saved URL for manual review",
            key_topics=[],
            difficulty=3,
            difficulty_label="Unknown",
            time_estimate="Unknown",
            prerequisites=[],
            why_useful="Review manually",
            tags=[],
            error=f"JSON parse error: {e}"
        )
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return Analysis(
            category="Unknown",
            summary="AI analysis unavailable",
            key_topics=[],
            difficulty=3,
            difficulty_label="Unknown",
            time_estimate="Unknown",
            prerequisites=[],
            why_useful="",
            tags=[],
            error=str(e)
        )
