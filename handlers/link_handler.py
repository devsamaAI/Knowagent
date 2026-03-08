"""
handlers/link_handler.py
=========================
The main handler — called every time a user sends a URL to the bot.
Orchestrates: detect → fetch → analyze → save → reply

WHAT YOU'LL LEARN HERE:
- async/await: Telegram bots are async (handle many users simultaneously)
- The "pipeline" pattern: chain of steps, each transforming the data
- How to send "typing..." indicators for better UX
- Formatting Telegram messages with Markdown
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from tools.link_detector import detect_link
from tools.fetcher import fetch_content
from tools.analyzer import analyze_content
from tools.security_checker import check_url_security, extract_urls_from_text, SCORE_EMOJI
from db.database import save_item, get_stats

logger = logging.getLogger(__name__)


# ── Emoji maps for visual formatting ────────────────────────────────────────

DIFFICULTY_EMOJI = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "💀"}
PLATFORM_EMOJI = {
    "YouTube": "▶️",
    "GitHub": "💻",
    "Twitter/X": "𝕏",
    "Instagram": "📸",
    "Web Article": "📄",
}
CATEGORY_EMOJI = {
    "Video Tutorial": "🎬",
    "YouTube Talk": "🎤",
    "GitHub Repo": "⚙️",
    "Tech Article": "📰",
    "Blog Post": "✍️",
    "Course": "🎓",
    "Tool/Library": "🔧",
    "Research Paper": "🔬",
    "Other": "📦",
}


def format_reply(title, platform, category, summary, difficulty, difficulty_label,
                 time_estimate, prerequisites, why_useful, tags,
                 security=None, desc_links=None, is_duplicate=False) -> str:
    """
    Build the Telegram reply message using HTML formatting.

    security   — SecurityResult for the main URL
    desc_links — list of (url, SecurityResult) for links found in the description
    """
    diff_emoji = DIFFICULTY_EMOJI.get(difficulty, "⚪")
    plat_emoji = PLATFORM_EMOJI.get(platform, "🔗")
    cat_emoji  = CATEGORY_EMOJI.get(category, "📦")

    # Format prerequisites
    prereqs_str = ""
    if prerequisites:
        prereqs_str = "\n".join(f"  • {p}" for p in prerequisites[:4])
        prereqs_str = f"\n<b>📚 Learn first:</b>\n{prereqs_str}"

    # Format tags
    tags_str = " ".join(f"#{t.replace(' ', '_').lower()}" for t in tags[:6])

    # Format security score for the main URL
    security_str = ""
    if security:
        emoji = SCORE_EMOJI.get(security.score, "⚪")
        security_str = f"\n<b>🔒 Security:</b> {emoji} {security.label} ({security.score}/5)"
        # Show the first reason as context
        if security.reasons:
            security_str += f" — <i>{security.reasons[0]}</i>"

    # Format links found in the description
    desc_links_str = ""
    if desc_links:
        lines = []
        for url, result in desc_links:
            emoji = SCORE_EMOJI.get(result.score, "⚪")
            short = url[:55] + "…" if len(url) > 55 else url
            lines.append(f"  {emoji} <a href='{url}'>{short}</a> — {result.label}")
        desc_links_str = "\n<b>🔗 Links in description:</b>\n" + "\n".join(lines)

    duplicate_notice = "\n<i>⚠️ Already in your library — showing fresh analysis</i>" if is_duplicate else ""

    return f"""✅ <b>Saved to your Pocket!</b>{duplicate_notice}

{plat_emoji} <b>{title}</b>

{cat_emoji} {category}  |  ⏱ {time_estimate}  |  {diff_emoji} {difficulty_label}{security_str}

<b>💡 Summary:</b>
{summary}

<b>🎯 Why save this:</b>
{why_useful}{prereqs_str}{desc_links_str}

<b>🏷 Tags:</b> {tags_str}

<i>Use /search &lt;keyword&gt; to find this later</i>"""


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main handler function. Called by python-telegram-bot whenever a URL is sent.
    
    LEARNING NOTE: 'async def' means this is a coroutine. The 'await' keywords
    let Python handle other users while waiting for slow operations (API calls,
    web requests). This is why bots can handle multiple users simultaneously.
    """
    message = update.message
    user_id = message.from_user.id
    
    # Extract the URL from the message
    # Telegram gives us entity offsets — precise character positions of URLs
    url = None
    for entity in message.entities:
        if entity.type == "url":
            url = message.text[entity.offset: entity.offset + entity.length]
            break
    
    if not url:
        return  # No URL found, ignore

    # ── Step 1: Send typing indicator (shows "Bot is typing..." in Telegram) ──
    await message.chat.send_action("typing")
    status_msg = await message.reply_text("🔍 Analyzing your link...")

    try:
        # ── Step 2: Detect what kind of link this is ──────────────────────────
        detected = detect_link(url)
        logger.info(f"User {user_id} shared {detected.link_type.value}: {url}")
        
        await status_msg.edit_text(f"⬇️ Fetching content from {detected.platform_name}...")

        # ── Step 3: Fetch the actual content ──────────────────────────────────
        content = fetch_content(detected)

        await status_msg.edit_text("🤖 Running AI analysis...")

        # ── Step 4: Analyze with AI ───────────────────────────────────────────
        analysis = analyze_content(content)

        # ── Step 4b: Security checks ──────────────────────────────────────────
        await status_msg.edit_text("🔐 Running security checks...")

        # Check the main URL
        security = check_url_security(url)

        # Extract and check any links mentioned in the description
        raw_desc_urls = extract_urls_from_text(
            (content.description or "") + " " + (content.content_text or "")
        )
        desc_links = []
        for desc_url in raw_desc_urls[:4]:   # Check up to 4 description links
            result = check_url_security(desc_url)
            desc_links.append((desc_url, result))

        # ── Step 5: Save to database ──────────────────────────────────────────
        saved_id = save_item(
            url=detected.clean_url,
            platform=detected.platform_name,
            title=content.title,
            category=analysis.category,
            summary=analysis.summary,
            difficulty=analysis.difficulty,
            difficulty_label=analysis.difficulty_label,
            time_estimate=analysis.time_estimate,
            why_useful=analysis.why_useful,
            key_topics=analysis.key_topics,
            prerequisites=analysis.prerequisites,
            tags=analysis.tags,
            telegram_user_id=user_id,
        )

        is_duplicate = saved_id is None

        # ── Step 6: Format and send the reply ─────────────────────────────────
        reply = format_reply(
            title=content.title,
            platform=detected.platform_name,
            category=analysis.category,
            summary=analysis.summary,
            difficulty=analysis.difficulty,
            difficulty_label=analysis.difficulty_label,
            time_estimate=analysis.time_estimate,
            prerequisites=analysis.prerequisites,
            why_useful=analysis.why_useful,
            tags=analysis.tags,
            security=security,
            desc_links=desc_links if desc_links else None,
            is_duplicate=is_duplicate,
        )

        # Delete the "Analyzing..." message and send the real reply
        await status_msg.delete()
        await message.reply_text(reply, parse_mode=ParseMode.HTML)

        # Occasionally remind user of their library size
        stats = get_stats(user_id)
        if stats["total"] % 10 == 0 and stats["total"] > 0:
            await message.reply_text(
                f"🎉 Milestone! You've saved <b>{stats['total']} items</b> to your Pocket.",
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        logger.error(f"Error handling link from user {user_id}: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ Something went wrong analyzing that link. The URL has been noted.\n"
            f"Error: {str(e)[:100]}"
        )
