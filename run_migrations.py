# run_migrations.py
"""
run_migrations.py

A small runner script you can execute whenever you want to ensure your DB schema
is up-to-date.

Typical usage:
- Run this once after pulling code changes.
- Run this after adding a new migration.
- You can also call it before running your collector.

How to run:
- Preferred package-aligned runner:
    python scripts/run_migrations.py

- Legacy compatibility runner:
    python run_migrations.py

- Or from a notebook cell:
    %run run_migrations.py

Make sure DB_PATH points at the same DB file your collector uses.
"""

from quantum_jobs.cli.migrate import main as migrate_main


def main() -> None:
    migrate_main()


if __name__ == "__main__":
    main()
