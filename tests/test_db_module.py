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
