from __future__ import annotations

from pathlib import Path

from conftest import load_module_from_repo


collector = load_module_from_repo("Quantum Jobs Collector.py", "quantum_jobs_collector_for_migrations")
migrations = load_module_from_repo("migration_utils.py", "migration_utils_module")


def test_run_all_migrations_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "quantum_jobs.db"

    conn = collector.connect_db(db_path)
    try:
        collector.init_schema(conn)
        # Seed a row where pulled_date is NULL so backfill can be validated.
        conn.execute(
            """
            INSERT INTO job_snapshots (
                pulled_at, pulled_date, company, source, api_url,
                job_id, title, department, location, modality,
                apply_url, last_modified, requisition_id, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026-03-24T12:00:00+00:00",
                None,
                "TestCo",
                "test-source",
                "https://example.test/api",
                "job-1",
                "Role",
                None,
                None,
                None,
                "https://example.test/apply",
                None,
                None,
                "{}",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    conn = migrations.connect_db(str(db_path))
    try:
        applied_first = migrations.run_all_migrations(conn)
        applied_second = migrations.run_all_migrations(conn)

        assert applied_first == [
            "0001_add_pulled_date_job_snapshots",
            "0002_add_pulled_date_current_and_changes",
        ]
        assert applied_second == []

        pulled_date = conn.execute(
            "SELECT pulled_date FROM job_snapshots WHERE company='TestCo' AND job_id='job-1'"
        ).fetchone()[0]
        assert pulled_date == "2026-03-24"
    finally:
        conn.close()
