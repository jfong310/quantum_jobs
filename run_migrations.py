# run_migrations.py
"""
run_migrations.py

A small runner script you can execute whenever you want to ensure your DB schema
is up-to-date.

Typical usage:
- Run this once after pulling code changes.
- Run this after adding a new migration to migration_utils.py
- You can also call it before running your collector.

How to run:
- From terminal (recommended):
    python run_migrations.py

- Or from a notebook cell:
    %run run_migrations.py

Make sure DB_PATH points at the same DB file your collector uses.
"""

from pathlib import Path

from migration_utils import connect_db, run_all_migrations


# Keep this consistent with your collector script.
SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "quantum_jobs.db"


def main() -> None:
    conn = connect_db(str(DB_PATH))
    try:
        applied = run_all_migrations(conn)
    finally:
        conn.close()

    print(f"DB: {DB_PATH.resolve()}")
    if applied:
        print("Applied migrations:")
        for mid in applied:
            print(f"  - {mid}")
    else:
        print("No migrations to apply (schema is up to date).")


if __name__ == "__main__":
    main()