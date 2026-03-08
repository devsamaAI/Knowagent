"""
POCKET AI AGENT — Phase 1
=============================
Entry point. This starts your Telegram bot and registers all handlers.

WHAT YOU'LL LEARN HERE:
- How a Telegram bot listens for messages (polling vs webhooks)
- How handlers route different message types
- Application lifecycle (start/stop)
"""

import logging
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters

from config.settings import TELEGRAM_BOT_TOKEN
from handlers.link_handler import handle_link
from handlers.command_handler import (
    start_command, help_command, search_command,
    recent_command, stats_command, topics_command, list_command
)
from db.database import init_db

# ── Logging setup (always do this first — helps you debug) ──────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    # 1. Initialize SQLite database (creates tables if they don't exist)
    init_db()
    logger.info("✅ Database initialized")

    # 2. Build the Telegram bot application
    #    ApplicationBuilder is a "builder pattern" — common in Python libraries
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # 3. Register command handlers  (/start, /help, /search)
    app.add_handler(CommandHandler("start",  start_command))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(CommandHandler("stats",  stats_command))
    app.add_handler(CommandHandler("topics", topics_command))
    app.add_handler(CommandHandler("list",   list_command))

    # 4. Register a message handler for any text message containing a URL
    #    filters.Entity("url") catches messages with links automatically
    app.add_handler(MessageHandler(filters.Entity("url"), handle_link))

    logger.info("🤖 Pocket Agent is running... Send a link to your bot!")

    # 5. Start polling — bot keeps asking Telegram "any new messages?"
    #    run_polling() blocks here and runs forever until you Ctrl+C
    app.run_polling()


if __name__ == "__main__":
    main()
