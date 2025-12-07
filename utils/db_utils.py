import os
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _resolve_db_path(override: Optional[str] = None) -> str:
    """Return the effective database path, honoring overrides and env vars."""
    if override:
        return override
    return os.getenv('JOB_APPS_DB_PATH', 'job_applications.db')


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a new SQLite connection with row factory enabled."""
    path = _resolve_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize required database tables and defaults."""
    path = _resolve_db_path(db_path)
    conn = None
    try:
        conn = sqlite3.connect(path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                job_type TEXT NOT NULL,
                country TEXT NOT NULL,
                source TEXT NOT NULL,
                date_applied TEXT NOT NULL,
                resume_version TEXT NOT NULL,
                status TEXT NOT NULL,
                status_date TEXT
            );
        ''')

        cursor = conn.execute("PRAGMA table_info(applications)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'status_date' not in columns:
            conn.execute("ALTER TABLE applications ADD COLUMN status_date TEXT")
            conn.execute("UPDATE applications SET status_date = date_applied")
            logger.info("Added status_date column to applications table")

        conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS scan_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                subject TEXT,
                sender TEXT,
                company TEXT,
                role TEXT,
                status_value TEXT,
                outcome TEXT NOT NULL,
                reason TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            );
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_scan_logs_created_at ON scan_logs(created_at DESC);')

        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        if not cursor.fetchone():
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                ('monitored_email', 'elyam.work@gmail.com')
            )

        conn.commit()
    except Exception as exc:
        logger.error("Database initialization error: %s", exc)
        raise
    finally:
        if conn:
            conn.close()
