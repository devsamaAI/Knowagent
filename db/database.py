"""
db/database.py
===============
Database layer — supports both SQLite (local dev) and PostgreSQL (production).

WHAT YOU'LL LEARN HERE:
- SQLite: file-based database, zero setup, built into Python
- PostgreSQL: production-grade database used by most real apps
- How to write DB-agnostic code using a connection abstraction
- SQL basics: CREATE TABLE, INSERT, SELECT, WHERE, LIKE
- Why we store JSON blobs for flexible fields (tags, topics, prerequisites)

HOW IT WORKS:
- If DATABASE_URL env var is set → uses PostgreSQL (Neon/production)
- If not set → uses SQLite (local development)
This lets you develop locally with zero setup and deploy to the cloud seamlessly.
"""

import json
import logging
import os
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Detect which database to use ─────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")  # Set this on Koyeb
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    logger.info("Using PostgreSQL database")
else:
    import sqlite3
    from config.settings import DB_PATH
    logger.info(f"Using SQLite database at {DB_PATH}")


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


# ── Connection helpers ────────────────────────────────────────────────────────

def get_connection():
    """
    Get a database connection.
    Returns a psycopg2 connection (PostgreSQL) or sqlite3 connection (SQLite).
    """
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn


def _placeholder():
    """
    SQL uses ? for SQLite params, %s for PostgreSQL.
    Returns the right one based on which DB we're using.
    """
    return "%s" if USE_POSTGRES else "?"


def _rows_to_dicts(rows) -> list:
    """Convert DB rows to plain dicts regardless of which driver returned them."""
    return [dict(row) for row in rows]


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    """
    Create tables if they don't exist yet.
    Called once at startup — safe to call multiple times (IF NOT EXISTS).
    """
    if USE_POSTGRES:
        sql = """
            CREATE TABLE IF NOT EXISTS saved_items (
                id               SERIAL PRIMARY KEY,
                url              TEXT NOT NULL,
                platform         TEXT,
                title            TEXT,
                category         TEXT,
                summary          TEXT,
                difficulty       INTEGER,
                difficulty_label TEXT,
                time_estimate    TEXT,
                why_useful       TEXT,
                key_topics       TEXT,
                prerequisites    TEXT,
                tags             TEXT,
                saved_at         TIMESTAMP DEFAULT NOW(),
                telegram_user_id BIGINT,
                UNIQUE(url, telegram_user_id)
            )
        """
    else:
        sql = """
            CREATE TABLE IF NOT EXISTS saved_items (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                url              TEXT NOT NULL,
                platform         TEXT,
                title            TEXT,
                category         TEXT,
                summary          TEXT,
                difficulty       INTEGER,
                difficulty_label TEXT,
                time_estimate    TEXT,
                why_useful       TEXT,
                key_topics       TEXT,
                prerequisites    TEXT,
                tags             TEXT,
                saved_at         TEXT DEFAULT (datetime('now')),
                telegram_user_id INTEGER,
                UNIQUE(url, telegram_user_id)
            )
        """
    with get_connection() as conn:
        if USE_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        else:
            conn.execute(sql)
            conn.commit()
    logger.info("Database tables ready")


# ── Write operations ──────────────────────────────────────────────────────────

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
    """
    p = _placeholder()
    values = (
        url, platform, title, category, summary, difficulty, difficulty_label,
        time_estimate, why_useful,
        json.dumps(key_topics),
        json.dumps(prerequisites),
        json.dumps(tags),
        telegram_user_id,
    )
    try:
        with get_connection() as conn:
            if USE_POSTGRES:
                sql = f"""
                    INSERT INTO saved_items
                    (url, platform, title, category, summary, difficulty, difficulty_label,
                     time_estimate, why_useful, key_topics, prerequisites, tags, telegram_user_id)
                    VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
                    ON CONFLICT (url, telegram_user_id) DO NOTHING
                    RETURNING id
                """
                with conn.cursor() as cur:
                    cur.execute(sql, values)
                    row = cur.fetchone()
                conn.commit()
                return row["id"] if row else None
            else:
                sql = f"""
                    INSERT OR IGNORE INTO saved_items
                    (url, platform, title, category, summary, difficulty, difficulty_label,
                     time_estimate, why_useful, key_topics, prerequisites, tags, telegram_user_id)
                    VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})
                """
                cursor = conn.execute(sql, values)
                conn.commit()
                return cursor.lastrowid if cursor.rowcount > 0 else None

    except Exception as e:
        logger.error(f"DB save error: {e}")
        return None


# ── Read operations ───────────────────────────────────────────────────────────

def search_items(query: str, telegram_user_id: int, limit: int = 5) -> list:
    """Keyword search across title, summary, category, and tags."""
    p = _placeholder()
    like = f"%{query}%"
    sql = f"""
        SELECT * FROM saved_items
        WHERE telegram_user_id = {p}
        AND (title LIKE {p} OR summary LIKE {p} OR category LIKE {p}
             OR tags LIKE {p} OR key_topics LIKE {p})
        ORDER BY saved_at DESC
        LIMIT {p}
    """
    try:
        with get_connection() as conn:
            if USE_POSTGRES:
                with conn.cursor() as cur:
                    cur.execute(sql, (telegram_user_id, like, like, like, like, like, limit))
                    return _rows_to_dicts(cur.fetchall())
            else:
                rows = conn.execute(sql, (telegram_user_id, like, like, like, like, like, limit)).fetchall()
                return _rows_to_dicts(rows)
    except Exception as e:
        logger.error(f"DB search error: {e}")
        return []


def get_recent_items(telegram_user_id: int, limit: int = 10) -> list:
    """Get the most recently saved items for a user."""
    p = _placeholder()
    sql = f"SELECT * FROM saved_items WHERE telegram_user_id = {p} ORDER BY saved_at DESC LIMIT {p}"
    try:
        with get_connection() as conn:
            if USE_POSTGRES:
                with conn.cursor() as cur:
                    cur.execute(sql, (telegram_user_id, limit))
                    return _rows_to_dicts(cur.fetchall())
            else:
                return _rows_to_dicts(conn.execute(sql, (telegram_user_id, limit)).fetchall())
    except Exception as e:
        logger.error(f"DB fetch error: {e}")
        return []


def get_categories(telegram_user_id: int) -> list:
    """Return all categories the user has saved items in, with counts."""
    p = _placeholder()
    sql = f"""
        SELECT category, COUNT(*) as count FROM saved_items
        WHERE telegram_user_id = {p}
        GROUP BY category ORDER BY count DESC
    """
    try:
        with get_connection() as conn:
            if USE_POSTGRES:
                with conn.cursor() as cur:
                    cur.execute(sql, (telegram_user_id,))
                    return _rows_to_dicts(cur.fetchall())
            else:
                return _rows_to_dicts(conn.execute(sql, (telegram_user_id,)).fetchall())
    except Exception as e:
        logger.error(f"DB categories error: {e}")
        return []


def get_items_by_category(category: str, telegram_user_id: int, limit: int = 8) -> list:
    """Return saved items matching a category."""
    p = _placeholder()
    sql = f"""
        SELECT * FROM saved_items
        WHERE telegram_user_id = {p} AND LOWER(category) LIKE LOWER({p})
        ORDER BY saved_at DESC LIMIT {p}
    """
    try:
        with get_connection() as conn:
            if USE_POSTGRES:
                with conn.cursor() as cur:
                    cur.execute(sql, (telegram_user_id, f"%{category}%", limit))
                    return _rows_to_dicts(cur.fetchall())
            else:
                return _rows_to_dicts(conn.execute(sql, (telegram_user_id, f"%{category}%", limit)).fetchall())
    except Exception as e:
        logger.error(f"DB category fetch error: {e}")
        return []


def get_stats(telegram_user_id: int) -> dict:
    """Get summary statistics for a user's saved items."""
    p = _placeholder()
    try:
        with get_connection() as conn:
            if USE_POSTGRES:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) as c FROM saved_items WHERE telegram_user_id = {p}", (telegram_user_id,))
                    total = cur.fetchone()["c"]
                    cur.execute(f"""
                        SELECT platform, COUNT(*) as count FROM saved_items
                        WHERE telegram_user_id = {p} GROUP BY platform ORDER BY count DESC
                    """, (telegram_user_id,))
                    by_platform = {row["platform"]: row["count"] for row in cur.fetchall()}
            else:
                total = conn.execute(f"SELECT COUNT(*) FROM saved_items WHERE telegram_user_id = {p}", (telegram_user_id,)).fetchone()[0]
                rows = conn.execute(f"""
                    SELECT platform, COUNT(*) as count FROM saved_items
                    WHERE telegram_user_id = {p} GROUP BY platform ORDER BY count DESC
                """, (telegram_user_id,)).fetchall()
                by_platform = {row["platform"]: row["count"] for row in rows}
            return {"total": total, "by_platform": by_platform}
    except Exception as e:
        logger.error(f"DB stats error: {e}")
        return {"total": 0, "by_platform": {}}
