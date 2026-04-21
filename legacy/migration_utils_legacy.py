# migration_utils.py
"""
migration_utils.py

A lightweight, SQLite-friendly schema migration system for the Quantum Jobs project.

What this gives you:
- A migrations ledger table (schema_migrations) so migrations run only once.
- Simple helpers: ensure_column, ensure_index, table_exists.
- A set of versioned migrations you can extend over time.
- A single entrypoint: run_all_migrations(conn)

Design goals:
- Safe to run repeatedly (idempotent).
- Minimal dependencies (stdlib only).
- Easy to read and extend.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List, Optional


# -----------------------------
# Basic DB utilities
# -----------------------------

def utc_now_iso() -> str:
    """UTC timestamp string suitable for logging/ledger."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect_db(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection with sensible defaults for this project.

    Notes:
    - WAL improves concurrent read/write behavior.
    - foreign_keys=ON makes FK constraints actually enforce (SQLite default is OFF).
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def get_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """
    Returns list of column names for a table using PRAGMA table_info.
    This is the source of truth for what columns exist.
    """
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
    return [r[1] for r in rows]


def ensure_column(conn: sqlite3.Connection, table: str, col: str, col_type: str) -> None:
    """
    Ensure a column exists. If missing, add it via ALTER TABLE.
    Safe to call repeatedly.
    """
    if not table_exists(conn, table):
        # If your base schema hasn't created this table yet, skip here.
        # The collector script's init_schema() should create tables.
        return

    cols = get_table_columns(conn, table)
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")


def ensure_index(conn: sqlite3.Connection, index_name: str, create_sql: str) -> None:
    """
    Ensure an index exists. Provide the full CREATE INDEX IF NOT EXISTS statement.
    """
    # You can just execute CREATE INDEX IF NOT EXISTS safely; SQLite won't recreate it.
    conn.execute(create_sql)


# -----------------------------
# Migration ledger
# -----------------------------

def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    """
    A simple ledger so we can record which migrations have run.
    This prevents re-running backfills or other one-time operations.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id   TEXT PRIMARY KEY,
            applied_at     TEXT NOT NULL
        );
        """
    )


def has_migration_run(conn: sqlite3.Connection, migration_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
        (migration_id,),
    ).fetchone()
    return row is not None


def record_migration(conn: sqlite3.Connection, migration_id: str) -> None:
    conn.execute(
        "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
        (migration_id, utc_now_iso()),
    )


# -----------------------------
# Define migrations
# -----------------------------

@dataclass(frozen=True)
class Migration:
    """
    A migration is:
    - id: unique, stable string (never change once used)
    - fn: function that performs schema changes/backfills
    """
    id: str
    fn: Callable[[sqlite3.Connection], None]


def migration_0001_add_pulled_date(conn: sqlite3.Connection) -> None:
    """
    Adds pulled_date to job_snapshots and backfills it from pulled_at.

    Why:
    - pulled_at is a full timestamp: YYYY-MM-DDTHH:MM:SS+00:00
    - pulled_date is a date dimension for easier grouping and filtering.

    Backfill strategy:
    - If pulled_date is NULL, set it to the first 10 characters of pulled_at (YYYY-MM-DD).
    """
    ensure_column(conn, "job_snapshots", "pulled_date", "TEXT")

    # Backfill for existing rows (safe if rerun because WHERE pulled_date IS NULL)
    if table_exists(conn, "job_snapshots"):
        conn.execute(
            """
            UPDATE job_snapshots
            SET pulled_date = substr(pulled_at, 1, 10)
            WHERE pulled_date IS NULL AND pulled_at IS NOT NULL;
            """
        )

    # Helpful index for common queries: company + date
    ensure_index(
        conn,
        "idx_snapshots_company_date",
        """
        CREATE INDEX IF NOT EXISTS idx_snapshots_company_date
        ON job_snapshots(company, pulled_date);
        """,
    )


def migration_0002_optional_add_pulled_date_to_current_and_changes(conn: sqlite3.Connection) -> None:
    """
    Optional: adds pulled_date to job_current and job_changes.

    If you don't care about a date column on these tables, you can remove this migration.
    Keeping it can make certain reporting/queries more convenient.
    """
    # job_current: pulled_date can help quickly group current table by date last seen
    ensure_column(conn, "job_current", "pulled_date", "TEXT")
    if table_exists(conn, "job_current"):
        conn.execute(
            """
            UPDATE job_current
            SET pulled_date = substr(pulled_at, 1, 10)
            WHERE pulled_date IS NULL AND pulled_at IS NOT NULL;
            """
        )

    # job_changes: pulled_date can make daily diffs simpler
    ensure_column(conn, "job_changes", "pulled_date", "TEXT")
    if table_exists(conn, "job_changes"):
        conn.execute(
            """
            UPDATE job_changes
            SET pulled_date = substr(pulled_at, 1, 10)
            WHERE pulled_date IS NULL AND pulled_at IS NOT NULL;
            """
        )

    ensure_index(
        conn,
        "idx_changes_company_date",
        """
        CREATE INDEX IF NOT EXISTS idx_changes_company_date
        ON job_changes(company, pulled_date);
        """,
    )


# Register migrations in the order they should be applied.
MIGRATIONS: List[Migration] = [
    Migration("0001_add_pulled_date_job_snapshots", migration_0001_add_pulled_date),
    Migration("0002_add_pulled_date_current_and_changes", migration_0002_optional_add_pulled_date_to_current_and_changes),
]


def run_all_migrations(conn: sqlite3.Connection) -> List[str]:
    """
    Run any migrations that have not yet been applied.

    Returns:
        A list of migration IDs that were applied in this run.
    """
    ensure_migrations_table(conn)
    applied: List[str] = []

    # Use an explicit transaction so either a migration fully applies, or it rolls back.
    # We commit after each migration and record it in the ledger.
    for m in MIGRATIONS:
        if has_migration_run(conn, m.id):
            continue

        try:
            conn.execute("BEGIN;")
            m.fn(conn)
            record_migration(conn, m.id)
            conn.execute("COMMIT;")
            applied.append(m.id)
        except Exception:
            conn.execute("ROLLBACK;")
            raise

    return applied