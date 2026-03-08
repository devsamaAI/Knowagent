"""
handlers/command_handler.py
============================
Handles bot commands: /start, /help, /search

WHAT YOU'LL LEARN HERE:
- Telegram command handlers
- How to parse command arguments (e.g. /search python agents)
- Building multi-line formatted Telegram messages
"""

import json
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from db.database import search_items, get_recent_items, get_stats, get_categories, get_items_by_category

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start — sent automatically when user first opens the bot."""
    name = update.effective_user.first_name or "there"
    
    await update.message.reply_text(
        f"👋 Hey <b>{name}</b>! I'm your <b>Pocket AI Agent</b>.\n\n"
        "Just send me any link and I'll:\n"
        "  ▶️  Detect if it's YouTube, GitHub, article, etc.\n"
        "  🤖  Summarize what it's about\n"
        "  ⏱  Estimate how long it'll take\n"
        "  📚  List what you need to know first\n"
        "  🏷  Tag it for easy search later\n\n"
        "<b>Commands:</b>\n"
        "  /topics — browse your library by topic/category\n"
        "  /list &lt;topic&gt; — show items in a topic\n"
        "  /search &lt;keyword&gt; — keyword search across all items\n"
        "  /recent — your last 10 saved items\n"
        "  /stats — library stats by platform\n"
        "  /help — show this message\n\n"
        "Send a link to get started! 🚀",
        parse_mode=ParseMode.HTML
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help"""
    await start_command(update, context)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /search <keyword>
    
    context.args contains everything after the command as a list of words.
    /search python async  →  context.args = ["python", "async"]
    """
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/search &lt;keyword&gt;</code>\n\n"
            "Examples:\n"
            "  /search python\n"
            "  /search machine learning\n"
            "  /search github",
            parse_mode=ParseMode.HTML
        )
        return

    query = " ".join(context.args)
    await update.message.chat.send_action("typing")
    
    results = search_items(query, user_id, limit=5)
    
    if not results:
        await update.message.reply_text(
            f"🔍 No results for <b>'{query}'</b>\n\n"
            "Try different keywords or check your spelling.",
            parse_mode=ParseMode.HTML
        )
        return

    # Build results message
    lines = [f"🔍 <b>Results for '{query}'</b> ({len(results)} found)\n"]
    
    for i, item in enumerate(results, 1):
        tags = json.loads(item.get("tags") or "[]")
        tags_str = " ".join(f"#{t}" for t in tags[:3])
        
        lines.append(
            f"<b>{i}. {item['title']}</b>\n"
            f"   {item['category']} | ⏱ {item['time_estimate']} | "
            f"{'🟢🟡🟠🔴💀'[item['difficulty']-1]} {item['difficulty_label']}\n"
            f"   {item['summary'][:120]}...\n"
            f"   🔗 {item['url']}\n"
            f"   {tags_str}\n"
        )
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /recent — shows last 10 saved items."""
    user_id = update.effective_user.id
    items = get_recent_items(user_id, limit=10)
    
    if not items:
        await update.message.reply_text(
            "📭 Your Pocket is empty! Send me a link to get started."
        )
        return

    lines = [f"📚 <b>Your last {len(items)} saved items:</b>\n"]
    
    for i, item in enumerate(items, 1):
        lines.append(
            f"<b>{i}.</b> {item['title']}\n"
            f"   {item['platform']} | {item['time_estimate']}\n"
            f"   <a href='{item['url']}'>Open link</a> | Saved: {item['saved_at'][:10]}\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /topics — show all categories in the user's library with item counts.
    Use /list <category> to see items within a category.
    """
    user_id = update.effective_user.id
    categories = get_categories(user_id)

    if not categories:
        await update.message.reply_text(
            "📭 Your Pocket is empty! Send me a link to get started."
        )
        return

    lines = ["📂 <b>Your Library by Topic</b>\n"]
    for cat in categories:
        lines.append(f"  • <b>{cat['category']}</b> — {cat['count']} item{'s' if cat['count'] > 1 else ''}")

    lines.append("\n<i>Use /list &lt;topic&gt; to browse items in a topic</i>")
    lines.append("<i>Example: /list Tutorial  or  /list GitHub</i>")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /list <category> — show saved items within a specific category/topic.
    Partial matches work: /list tutorial  matches "Video Tutorial".
    """
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/list &lt;topic&gt;</code>\n\n"
            "Examples:\n"
            "  /list Tutorial\n"
            "  /list GitHub\n"
            "  /list Article\n\n"
            "Use /topics to see all your categories.",
            parse_mode=ParseMode.HTML,
        )
        return

    query = " ".join(context.args)
    await update.message.chat.send_action("typing")

    items = get_items_by_category(query, user_id)

    if not items:
        await update.message.reply_text(
            f"📭 No items found in topic <b>'{query}'</b>.\n\n"
            "Use /topics to see all your categories.",
            parse_mode=ParseMode.HTML,
        )
        return

    lines = [f"📂 <b>{query.title()} ({len(items)} items)</b>\n"]
    for i, item in enumerate(items, 1):
        diff_emoji = "🟢🟡🟠🔴💀"[max(0, item["difficulty"] - 1)]
        lines.append(
            f"<b>{i}. {item['title']}</b>\n"
            f"   {item['platform']} | ⏱ {item['time_estimate']} | {diff_emoji} {item['difficulty_label']}\n"
            f"   {item['summary'][:100]}…\n"
            f"   <a href='{item['url']}'>Open link</a>  · Saved {item['saved_at'][:10]}\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stats — shows library statistics."""
    user_id = update.effective_user.id
    stats = get_stats(user_id)
    
    platform_breakdown = "\n".join(
        f"  {p}: {c}" for p, c in stats["by_platform"].items()
    ) or "  (none yet)"

    await update.message.reply_text(
        f"📊 <b>Your Pocket Stats</b>\n\n"
        f"Total saved: <b>{stats['total']}</b>\n\n"
        f"By platform:\n{platform_breakdown}",
        parse_mode=ParseMode.HTML
    )
