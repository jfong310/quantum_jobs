from __future__ import annotations

import json

from quantum_jobs import collector


def test_make_row_from_normalized_derives_expected_fields() -> None:
    row = collector.make_row_from_normalized(
        pulled_at="2026-03-24T12:00:00+00:00",
        company="  IonQ  ",
        source=" greenhouse ",
        api_url=" https://example.test/jobs ",
        job_id=123,
        title=" Quantum Engineer ",
        department=" R&D ",
        location=" College Park, MD ",
        modality=" Hybrid ",
        apply_url="https://example.test/apply",
        last_modified="2026-03-24T10:00:00Z",
        requisition_id="REQ-1",
        raw_json_obj={"id": 123},
    )

    assert row["pulled_date"] == "2026-03-24"
    assert row["company"] == "IonQ"
    assert row["source"] == "greenhouse"
    assert row["job_id"] == "123"
    assert row["raw_json"] == json.dumps({"id": 123}, ensure_ascii=False, separators=(",", ":"))


def test_log_changes_records_added_removed_changed_and_no_change() -> None:
    conn = collector.connect_db(":memory:")
    try:
        collector.init_schema(conn)

        prev_map = {
            "same": {
                "job_id": "same",
                "title": "Engineer I",
                "department": "Engineering",
                "location": "NYC",
                "modality": "Onsite",
                "apply_url": "https://example.test/same",
                "last_modified": "2026-03-20T00:00:00Z",
            },
            "removed": {
                "job_id": "removed",
                "title": "Scientist",
                "department": "Research",
                "location": "LA",
                "modality": "Remote",
                "apply_url": "https://example.test/removed",
                "last_modified": "2026-03-19T00:00:00Z",
            },
        }

        new_map = {
            "same": {
                "job_id": "same",
                "title": "Engineer II",  # changed
                "department": "Engineering",
                "location": "NYC",
                "modality": "Onsite",
                "apply_url": "https://example.test/same",
                "last_modified": "2026-03-20T00:00:00Z",
            },
            "added": {
                "job_id": "added",
                "title": "Technician",
                "department": "Operations",
                "location": "Austin",
                "modality": "Hybrid",
                "apply_url": "https://example.test/added",
                "last_modified": "2026-03-21T00:00:00Z",
            },
        }

        collector.log_changes(
            conn,
            pulled_at="2026-03-24T12:00:00+00:00",
            company="TestCo",
            prev_map=prev_map,
            new_map=new_map,
        )

        change_types = {
            row[0]
            for row in conn.execute(
                "SELECT change_type FROM job_changes WHERE company='TestCo'"
            ).fetchall()
        }
        assert change_types == {"added", "removed", "changed"}

        collector.log_changes(
            conn,
            pulled_at="2026-03-24T13:00:00+00:00",
            company="NoChangeCo",
            prev_map={"a": {"job_id": "a", "title": "T", "department": None, "location": None, "modality": None, "apply_url": None, "last_modified": None}},
            new_map={"a": {"job_id": "a", "title": "T", "department": None, "location": None, "modality": None, "apply_url": None, "last_modified": None}},
        )

        rows = conn.execute(
            "SELECT change_type, details_json FROM job_changes WHERE company='NoChangeCo'"
        ).fetchall()
        assert rows == [("no_change", "{}")]
    finally:
        conn.close()
