"""
config/settings.py
==================
Central place for all configuration.

WHAT YOU'LL LEARN HERE:
- python-dotenv: loading secrets from a .env file (never hardcode API keys!)
- os.environ: reading environment variables
- Why we separate config from code
"""

import os
from dotenv import load_dotenv

# Load variables from .env file into environment
load_dotenv()

# ── Required secrets (bot will crash with a clear error if missing) ──────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set in .env file!")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not set in .env file!")

# SQLite database file location
DB_PATH = os.getenv("DB_PATH", "pocket_agent.db")

# Max characters to send to Gemini for web articles
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "8000"))
