from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List


def utc_now_iso() -> str:
    """UTC timestamp string suitable for logging/ledger."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect_db(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection with sensible defaults for this project."""
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
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return [r[1] for r in rows]


def ensure_column(conn: sqlite3.Connection, table: str, col: str, col_type: str) -> None:
    if not table_exists(conn, table):
        return

    cols = get_table_columns(conn, table)
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")


def ensure_index(conn: sqlite3.Connection, index_name: str, create_sql: str) -> None:
    del index_name  # create_sql is the source of truth here.
    conn.execute(create_sql)


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
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


@dataclass(frozen=True)
class Migration:
    id: str
    fn: Callable[[sqlite3.Connection], None]


def migration_0001_add_pulled_date(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "job_snapshots", "pulled_date", "TEXT")

    if table_exists(conn, "job_snapshots"):
        conn.execute(
            """
            UPDATE job_snapshots
            SET pulled_date = substr(pulled_at, 1, 10)
            WHERE pulled_date IS NULL AND pulled_at IS NOT NULL;
            """
        )

    ensure_index(
        conn,
        "idx_snapshots_company_date",
        """
        CREATE INDEX IF NOT EXISTS idx_snapshots_company_date
        ON job_snapshots(company, pulled_date);
        """,
    )


def migration_0002_optional_add_pulled_date_to_current_and_changes(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "job_current", "pulled_date", "TEXT")
    if table_exists(conn, "job_current"):
        conn.execute(
            """
            UPDATE job_current
            SET pulled_date = substr(pulled_at, 1, 10)
            WHERE pulled_date IS NULL AND pulled_at IS NOT NULL;
            """
        )

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


MIGRATIONS: List[Migration] = [
    Migration("0001_add_pulled_date_job_snapshots", migration_0001_add_pulled_date),
    Migration("0002_add_pulled_date_current_and_changes", migration_0002_optional_add_pulled_date_to_current_and_changes),
]


def run_all_migrations(conn: sqlite3.Connection) -> List[str]:
    ensure_migrations_table(conn)
    applied: List[str] = []

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
