"""Phase 4: explicit durable, account-scoped learning preferences.

Educational single-user implementation. API identity is set server-side.
Do not use this SQLite store for secrets, medical or other sensitive data.
"""
from contextlib import contextmanager
import sqlite3
import re
from langchain.tools import tool
from config import PREFERENCE_DB

BLOCK = re.compile(r'(password|api\s*key|secret|access\s*key|private\s*key|token|credit\s*card)', re.I)


@contextmanager
def _connect():
    db = sqlite3.connect(PREFERENCE_DB, timeout=10)
    try:
        db.execute('''CREATE TABLE IF NOT EXISTS preferences (
            user_id TEXT NOT NULL, category TEXT NOT NULL, value TEXT NOT NULL,
            PRIMARY KEY (user_id, category))''')
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_memory_tools(user_id: str):
    # Never accept user_id from the LLM or user-supplied tool parameters.
    @tool
    def save_study_preference(category: str, value: str) -> str:
        """Save a user's EXPLICIT, non-sensitive learning preference for future sessions. Use only when asked to remember it."""
        if not 1 <= len(category) <= 60 or not re.fullmatch(r'[a-zA-Z_ -]+', category):
            return 'Category must be 1-60 letters/spaces/underscores.'
        if not 1 <= len(value) <= 250 or BLOCK.search(category + ' ' + value):
            return 'Rejected: empty, overly long, or potentially sensitive preference.'
        with _connect() as db:
            db.execute('INSERT INTO preferences (user_id, category, value) VALUES (?, ?, ?) '
                       'ON CONFLICT(user_id, category) DO UPDATE SET value=excluded.value',
                       (user_id, category.lower().strip(), value.strip()))
        return 'Study preference saved.'

    @tool
    def read_study_preferences() -> str:
        """Read this user's previously saved, non-sensitive study preferences when helpful."""
        with _connect() as db:
            rows = db.execute('SELECT category, value FROM preferences WHERE user_id=? ORDER BY category LIMIT 30',
                              (user_id,)).fetchall()
        return '; '.join(f'{k}: {v}' for k, v in rows) if rows else 'No saved study preferences.'

    return [save_study_preference, read_study_preferences]
