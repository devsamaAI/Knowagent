"""
db/database.py
===============
SQLite database layer — stores everything the agent saves.

WHAT YOU'LL LEARN HERE:
- SQLite: file-based database, zero setup, built into Python
- SQL basics: CREATE TABLE, INSERT, SELECT, WHERE, LIKE
- Context managers (with sqlite3.connect(...)) for safe DB connections
- Why we store JSON blobs for flexible fields (tags, topics, prerequisites)
- Database design: what columns do we need to enable future features?
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from config.settings import DB_PATH

logger = logging.getLogger(__name__)


@dataclass
class SavedItem:
    """Represents one row in our database."""
    id: Optional[int]
    url: str
    platform: str
    title: str
    category: str
    summary: str
    difficulty: int
    difficulty_label: str
    time_estimate: str
    why_useful: str
    key_topics: list
    prerequisites: list
    tags: list
    saved_at: str
    telegram_user_id: int


def get_connection():
    """
    Get a SQLite connection with some quality-of-life settings.
    
    LEARNING NOTE: 
    - detect_types enables Python datetime parsing from SQLite TEXT
    - Row factory lets us access columns by name: row["title"] not row[0]
    """
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create tables if they don't exist yet.
    Called once at startup — safe to call multiple times (IF NOT EXISTS).
    """
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_items (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                url             TEXT NOT NULL,
                platform        TEXT,
                title           TEXT,
                category        TEXT,
                summary         TEXT,
                difficulty      INTEGER,
                difficulty_label TEXT,
                time_estimate   TEXT,
                why_useful      TEXT,
                key_topics      TEXT,    -- stored as JSON array string
                prerequisites   TEXT,    -- stored as JSON array string
                tags            TEXT,    -- stored as JSON array string
                saved_at        TEXT DEFAULT (datetime('now')),
                telegram_user_id INTEGER,
                
                -- Prevent saving the exact same URL twice
                UNIQUE(url, telegram_user_id)
            )
        """)
        conn.commit()
    logger.info("Database tables ready")


def save_item(
    url: str,
    platform: str,
    title: str,
    category: str,
    summary: str,
    difficulty: int,
    difficulty_label: str,
    time_estimate: str,
    why_useful: str,
    key_topics: list,
    prerequisites: list,
    tags: list,
    telegram_user_id: int,
) -> Optional[int]:
    """
    Insert one saved item. Returns the new row's ID, or None if it already exists.
    
    LEARNING NOTE: json.dumps() converts a Python list to a JSON string for storage.
    json.loads() converts it back when reading. This is a common SQLite pattern
    for storing lists when you don't need to query individual list elements.
    """
    try:
        with get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO saved_items 
                (url, platform, title, category, summary, difficulty, difficulty_label,
                 time_estimate, why_useful, key_topics, prerequisites, tags, telegram_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                url, platform, title, category, summary, difficulty, difficulty_label,
                time_estimate, why_useful,
                json.dumps(key_topics),
                json.dumps(prerequisites),
                json.dumps(tags),
                telegram_user_id,
            ))
            conn.commit()
            
            if cursor.rowcount == 0:
                return None  # Already existed (UNIQUE constraint)
            return cursor.lastrowid

    except Exception as e:
        logger.error(f"DB save error: {e}")
        return None


def search_items(query: str, telegram_user_id: int, limit: int = 5) -> list:
    """
    Basic text search across title, summary, category, and tags.
    
    LEARNING NOTE: SQL LIKE with % wildcards does substring search.
    Phase 2 will replace this with vector similarity search (ChromaDB)
    which is much smarter — finds semantically similar items, not just
    exact keyword matches.
    """
    try:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM saved_items
                WHERE telegram_user_id = ?
                AND (
                    title    LIKE ? OR
                    summary  LIKE ? OR
                    category LIKE ? OR
                    tags     LIKE ? OR
                    key_topics LIKE ?
                )
                ORDER BY saved_at DESC
                LIMIT ?
            """, (
                telegram_user_id,
                f"%{query}%", f"%{query}%", f"%{query}%",
                f"%{query}%", f"%{query}%",
                limit
            )).fetchall()
            
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"DB search error: {e}")
        return []


def get_recent_items(telegram_user_id: int, limit: int = 10) -> list:
    """Get the most recently saved items for a user."""
    try:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM saved_items
                WHERE telegram_user_id = ?
                ORDER BY saved_at DESC
                LIMIT ?
            """, (telegram_user_id, limit)).fetchall()
            
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"DB fetch error: {e}")
        return []


def get_categories(telegram_user_id: int) -> list:
    """Return all categories the user has saved items in, with counts."""
    try:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT category, COUNT(*) as count
                FROM saved_items
                WHERE telegram_user_id = ?
                GROUP BY category
                ORDER BY count DESC
            """, (telegram_user_id,)).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"DB categories error: {e}")
        return []


def get_items_by_category(category: str, telegram_user_id: int, limit: int = 8) -> list:
    """Return saved items matching a category."""
    try:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM saved_items
                WHERE telegram_user_id = ?
                AND LOWER(category) LIKE LOWER(?)
                ORDER BY saved_at DESC
                LIMIT ?
            """, (telegram_user_id, f"%{category}%", limit)).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"DB category fetch error: {e}")
        return []


def get_stats(telegram_user_id: int) -> dict:
    """Get summary statistics for a user's saved items."""
    try:
        with get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM saved_items WHERE telegram_user_id = ?",
                (telegram_user_id,)
            ).fetchone()[0]

            by_platform = conn.execute("""
                SELECT platform, COUNT(*) as count 
                FROM saved_items 
                WHERE telegram_user_id = ?
                GROUP BY platform
                ORDER BY count DESC
            """, (telegram_user_id,)).fetchall()

            return {
                "total": total,
                "by_platform": {row["platform"]: row["count"] for row in by_platform}
            }
    except Exception as e:
        logger.error(f"DB stats error: {e}")
        return {"total": 0, "by_platform": {}}
