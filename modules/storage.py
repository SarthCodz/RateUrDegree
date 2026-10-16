import sqlite3
import time
from typing import Optional

DB_PATH = "rateurdegree.db"

def init_sqlite_db() -> None:
    """Initialize SQLite tables for bulletin caching and usage logging."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bulletin_cache (
                url TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                major TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        conn.commit()

def get_cached_bulletin(url: str, max_age_seconds: int = 86400) -> Optional[str]:
    """Retrieve scraped content if available and unexpired."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT content, timestamp FROM bulletin_cache WHERE url = ?", (url,))
        row = cursor.fetchone()
        if row:
            content, timestamp = row
            if time.time() - timestamp < max_age_seconds:
                return content
    return None

def set_cached_bulletin(url: str, content: str) -> None:
    """Cache bulletin scraper result in SQLite."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO bulletin_cache (url, content, timestamp) VALUES (?, ?, ?)",
            (url, content, time.time())
        )
        conn.commit()

def log_anonymous_usage(major_name: str) -> None:
    """Log an anonymous audit run for resume metrics tracking."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usage_logs (major, timestamp) VALUES (?, ?)",
            (major_name, time.time())
        )
        conn.commit()

def get_total_audit_count() -> int:
    """Retrieve total count of processed audits."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usage_logs")
        res = cursor.fetchone()
        return res[0] if res else 0