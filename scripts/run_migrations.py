from __future__ import annotations

from pathlib import Path

from quantum_jobs import migrations


SCRIPT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = SCRIPT_DIR / "quantum_jobs.db"


def main() -> None:
    conn = migrations.connect_db(str(DB_PATH))
    try:
        applied = migrations.run_all_migrations(conn)
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
