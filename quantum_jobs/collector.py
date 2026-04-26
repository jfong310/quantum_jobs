from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Protocol

from . import db, migrations
from .db.paths import DB_PATH
from .sources.greenhouse_companies import ionq_source, psiquantum_source
from .sources.lever_companies import (
    atomcomputing_source,
    qctrl_source,
    quantinuum_source,
    rigetti_source,
)


TIMEOUT_S = 30

# Re-export core helpers for compatibility with existing call sites/tests.
connect_db = db.connect_db
init_schema = db.init_schema
normalize_str = db.normalize_str
make_row_from_normalized = db.make_row_from_normalized
insert_snapshot_rows = db.insert_snapshot_rows
upsert_current = db.upsert_current
get_previous_snapshot_time = db.get_previous_snapshot_time
load_snapshot_map = db.load_snapshot_map
log_changes = db.log_changes


class JobSource(Protocol):
    def name(self) -> str: ...

    def fetch_rows(self, pulled_at: str) -> List[Dict[str, Any]]: ...


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TeamMeSource:
    def __init__(self, *, company: str, source: str, api_url: str, timeout_s: int = 30) -> None:
        self.company = company
        self.source = source
        self.api_url = api_url
        self.timeout_s = timeout_s

    def name(self) -> str:
        return f"{self.company} ({self.source})"

    def fetch_rows(self, pulled_at: str) -> List[Dict[str, Any]]:
        import requests

        res = requests.get(self.api_url, timeout=self.timeout_s)
        res.raise_for_status()
        payload = res.json()

        jobs = payload.get("data", [])
        if not isinstance(jobs, list):
            raise ValueError(f"Unexpected payload format for {self.name()}: 'data' is {type(jobs)}")

        rows: List[Dict[str, Any]] = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            rows.append(
                make_row_from_normalized(
                    pulled_at=pulled_at,
                    company=self.company,
                    source=self.source,
                    api_url=self.api_url,
                    job_id=job.get("id"),
                    title=job.get("title"),
                    department=job.get("department"),
                    location=job.get("location"),
                    modality=job.get("workplaceType"),
                    apply_url=job.get("applyUrl"),
                    last_modified=job.get("lastModified"),
                    requisition_id=job.get("requisitionId"),
                    raw_json_obj=job,
                )
            )
        return rows


class GreenhouseSourceAdapter:
    def __init__(self, gh_source_obj: Any) -> None:
        self.gh = gh_source_obj

    def name(self) -> str:
        return f"{getattr(self.gh, 'company', 'Greenhouse')} (greenhouse)"

    def fetch_rows(self, pulled_at: str) -> List[Dict[str, Any]]:
        jobs = self.gh.fetch_as_dicts()
        rows: List[Dict[str, Any]] = []

        for j in jobs:
            if not isinstance(j, dict):
                continue
            rows.append(
                make_row_from_normalized(
                    pulled_at=pulled_at,
                    company=j.get("company"),
                    source=j.get("source"),
                    api_url=j.get("api_url"),
                    job_id=j.get("job_id"),
                    title=j.get("title"),
                    department=j.get("department"),
                    location=j.get("location"),
                    modality=j.get("modality"),
                    apply_url=j.get("apply_url"),
                    last_modified=j.get("last_modified"),
                    requisition_id=j.get("requisition_id"),
                    raw_json_obj=j.get("raw_json"),
                )
            )

        return rows


class LeverSourceAdapter:
    def __init__(self, lever_source_obj: Any) -> None:
        self.lv = lever_source_obj

    def name(self) -> str:
        return f"{getattr(self.lv, 'company', 'Lever')} (lever)"

    def fetch_rows(self, pulled_at: str) -> List[Dict[str, Any]]:
        jobs = self.lv.fetch_as_dicts()
        rows: List[Dict[str, Any]] = []

        for j in jobs:
            if not isinstance(j, dict):
                continue
            rows.append(
                make_row_from_normalized(
                    pulled_at=pulled_at,
                    company=j.get("company"),
                    source=j.get("source"),
                    api_url=j.get("api_url"),
                    job_id=j.get("job_id"),
                    title=j.get("title"),
                    department=j.get("department"),
                    location=j.get("location"),
                    modality=j.get("modality"),
                    apply_url=j.get("apply_url"),
                    last_modified=j.get("last_modified"),
                    requisition_id=j.get("requisition_id"),
                    raw_json_obj=j.get("raw_json"),
                )
            )

        return rows


def build_sources() -> List[JobSource]:
    return [
        TeamMeSource(
            company="Quantum Machines",
            source="teamme.link",
            api_url="https://teamme.link/api/projects/e1b1ebc1-c84e-4c70-a322-fd628476b5b2/positions",
            timeout_s=TIMEOUT_S,
        ),
        GreenhouseSourceAdapter(ionq_source()),
        GreenhouseSourceAdapter(psiquantum_source()),
        LeverSourceAdapter(rigetti_source()),
        LeverSourceAdapter(atomcomputing_source()),
        LeverSourceAdapter(quantinuum_source()),
        LeverSourceAdapter(qctrl_source()),
    ]


def main() -> None:
    pulled_at = utc_now_iso()
    conn = migrations.connect_db(str(DB_PATH))
    try:
        init_schema(conn)
        migrations.run_all_migrations(conn)
    finally:
        conn.close()

    conn = connect_db(str(DB_PATH))
    try:
        init_schema(conn)

        for src in build_sources():
            rows = src.fetch_rows(pulled_at)
            rows = [r for r in rows if r.get("company") and r.get("job_id")]
            if not rows:
                continue

            company = rows[0]["company"]

            insert_snapshot_rows(conn, rows)
            prev_time = get_previous_snapshot_time(conn, company, pulled_at)
            new_map = {r["job_id"]: r for r in rows}
            prev_map = load_snapshot_map(conn, company, prev_time) if prev_time else {}
            log_changes(conn, pulled_at=pulled_at, company=company, prev_map=prev_map, new_map=new_map)
            upsert_current(conn, rows)

            cur_count = conn.execute(
                "SELECT COUNT(*) FROM job_current WHERE company = ?",
                (company,),
            ).fetchone()[0]

            print(f"[{company}] Jobs this run: {len(rows)} | Current tracked: {cur_count}")
            if prev_time:
                print(f"[{company}] Compared against previous snapshot: {prev_time}")
            else:
                print(f"[{company}] No previous snapshot found (first run).")

        print(f"\nDB: {DB_PATH.resolve()}")
        print(f"Pulled at (UTC): {pulled_at}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
