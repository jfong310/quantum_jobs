from __future__ import annotations

import json

from quantum_jobs import db


def test_db_make_row_from_normalized_keeps_existing_behavior() -> None:
    row = db.make_row_from_normalized(
        pulled_at="2026-03-24T12:00:00+00:00",
        company="  IonQ  ",
        source=" greenhouse ",
        api_url=" https://example.test/jobs ",
        job_id=123,
        title=" Quantum Engineer ",
        raw_json_obj={"id": 123},
    )

    assert row["pulled_date"] == "2026-03-24"
    assert row["company"] == "IonQ"
    assert row["source"] == "greenhouse"
    assert row["job_id"] == "123"
    assert row["raw_json"] == json.dumps({"id": 123}, ensure_ascii=False, separators=(",", ":"))


def test_db_log_changes_no_change_branch() -> None:
    conn = db.connect_db(":memory:")
    try:
        db.init_schema(conn)
        stable = {
            "a": {
                "job_id": "a",
                "title": "T",
                "department": None,
                "location": None,
                "modality": None,
                "apply_url": None,
                "last_modified": None,
            }
        }
        db.log_changes(
            conn,
            pulled_at="2026-03-24T13:00:00+00:00",
            company="NoChangeCo",
            prev_map=stable,
            new_map=stable,
        )
        rows = conn.execute(
            "SELECT change_type, details_json FROM job_changes WHERE company='NoChangeCo'"
        ).fetchall()
        assert rows == [("no_change", "{}")]
    finally:
        conn.close()


def test_load_canonical_daily_job_counts_uses_latest_snapshot_and_distinct_job_ids() -> None:
    conn = db.connect_db(":memory:")
    try:
        db.init_schema(conn)

        rows = [
            db.make_row_from_normalized(
                pulled_at="2026-02-22T09:00:00+00:00",
                company="Quantum Machines",
                source="greenhouse",
                api_url="https://example.test/jobs",
                job_id="job-1",
            ),
            db.make_row_from_normalized(
                pulled_at="2026-02-22T09:00:00+00:00",
                company="Quantum Machines",
                source="greenhouse",
                api_url="https://example.test/jobs",
                job_id="job-2",
            ),
            db.make_row_from_normalized(
                pulled_at="2026-02-22T12:00:00+00:00",
                company="Quantum Machines",
                source="greenhouse",
                api_url="https://example.test/jobs",
                job_id="job-2",
            ),
            db.make_row_from_normalized(
                pulled_at="2026-02-22T12:00:00+00:00",
                company="Quantum Machines",
                source="greenhouse",
                api_url="https://example.test/jobs",
                job_id="job-3",
            ),
            # Additional company/date row to ensure filtering by company still works.
            db.make_row_from_normalized(
                pulled_at="2026-02-22T12:00:00+00:00",
                company="Alice & Bob",
                source="greenhouse",
                api_url="https://example.test/jobs",
                job_id="ab-1",
            ),
        ]
        db.insert_snapshot_rows(conn, rows)

        all_counts = db.load_canonical_daily_job_counts(conn)
        assert all_counts == [
            {"company": "Alice & Bob", "snapshot_date": "2026-02-22", "job_count": 1},
            {"company": "Quantum Machines", "snapshot_date": "2026-02-22", "job_count": 2},
        ]

        qm_counts = db.load_canonical_daily_job_counts(conn, company="Quantum Machines")
        assert qm_counts == [
            {"company": "Quantum Machines", "snapshot_date": "2026-02-22", "job_count": 2}
        ]
    finally:
        conn.close()
