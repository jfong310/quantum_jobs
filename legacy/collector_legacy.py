import requests
import sqlite3
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Protocol
from pathlib import Path
import logging

from quantum_jobs.db.paths import DB_PATH

# ---- PATH CONFIGURATION ----
SCRIPT_DIR = Path(__file__).resolve().parent

# ---- LOGGING SETUP ----
logging.basicConfig(
    filename=str(SCRIPT_DIR / "collector.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

logging.info("Collector starting")
logging.info(f"SCRIPT_DIR = {SCRIPT_DIR}")
logging.info(f"DB_PATH = {DB_PATH}")

TIMEOUT_S = 30


# ----------------------------
# Time helpers
# ----------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------
# DB helpers
# ----------------------------

def connect_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Create the collector base tables and indexes if they do not exist.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS job_snapshots (
            snapshot_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            pulled_at       TEXT NOT NULL,
            pulled_date     TEXT, -- YYYY-MM-DD for grouping
            company         TEXT NOT NULL,
            source          TEXT NOT NULL,
            api_url         TEXT NOT NULL,

            job_id          TEXT NOT NULL,
            title           TEXT,
            department      TEXT,
            location        TEXT,
            modality        TEXT,
            apply_url       TEXT,
            last_modified   TEXT,
            requisition_id  TEXT,

            raw_json        TEXT,

            UNIQUE(pulled_at, company, job_id)
        );

        CREATE TABLE IF NOT EXISTS job_current (
            company         TEXT NOT NULL,
            job_id          TEXT NOT NULL,

            pulled_at       TEXT NOT NULL,
            pulled_date     TEXT,
            source          TEXT NOT NULL,
            api_url         TEXT NOT NULL,

            title           TEXT,
            department      TEXT,
            location        TEXT,
            modality        TEXT,
            apply_url       TEXT,
            last_modified   TEXT,
            requisition_id  TEXT,

            raw_json        TEXT,

            PRIMARY KEY(company, job_id)
        );

        CREATE TABLE IF NOT EXISTS job_changes (
            change_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            pulled_at       TEXT NOT NULL,
            company         TEXT NOT NULL,
            job_id          TEXT,
            change_type     TEXT NOT NULL,  -- added|removed|changed|no_change

            title           TEXT,
            location        TEXT,
            modality        TEXT,
            apply_url       TEXT,
            last_modified   TEXT,

            details_json    TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_snapshots_company_time
            ON job_snapshots(company, pulled_at);

        CREATE INDEX IF NOT EXISTS idx_changes_company_time
            ON job_changes(company, pulled_at);

        CREATE INDEX IF NOT EXISTS idx_current_company
            ON job_current(company);
        """
    )

    conn.commit()


# ----------------------------
# Normalization helpers
# ----------------------------

def normalize_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    s = " ".join(s.split())
    return s if s else None


def make_row_from_normalized(
    *,
    pulled_at: str,
    company: str,
    source: str,
    api_url: str,
    job_id: Any,
    title: Any = None,
    department: Any = None,
    location: Any = None,
    modality: Any = None,
    apply_url: Any = None,
    last_modified: Any = None,
    requisition_id: Any = None,
    raw_json_obj: Any = None,
) -> Dict[str, Any]:
    pulled_date = pulled_at[:10]
    raw_json_str = (
        json.dumps(raw_json_obj, ensure_ascii=False, separators=(",", ":"))
        if raw_json_obj is not None
        else None
    )

    return {
        "pulled_at": pulled_at,
        "pulled_date": pulled_date,
        "company": normalize_str(company),
        "source": normalize_str(source),
        "api_url": normalize_str(api_url),

        "job_id": normalize_str(job_id),
        "title": normalize_str(title),
        "department": normalize_str(department),
        "location": normalize_str(location),
        "modality": normalize_str(modality),
        "apply_url": normalize_str(apply_url),
        "last_modified": normalize_str(last_modified),
        "requisition_id": normalize_str(requisition_id),

        "raw_json": raw_json_str,
    }


# ----------------------------
# Insert / upsert
# ----------------------------

def insert_snapshot_rows(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> None:
    sql = """
        INSERT OR IGNORE INTO job_snapshots (
            pulled_at, pulled_date, company, source, api_url,
            job_id, title, department, location, modality,
            apply_url, last_modified, requisition_id, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    data = [
        (
            r["pulled_at"], r["pulled_date"], r["company"], r["source"], r["api_url"],
            r["job_id"], r["title"], r["department"], r["location"], r["modality"],
            r["apply_url"], r["last_modified"], r["requisition_id"], r["raw_json"]
        )
        for r in rows
    ]
    conn.executemany(sql, data)
    conn.commit()


def upsert_current(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> None:
    sql = """
        INSERT INTO job_current (
            company, job_id,
            pulled_at, pulled_date, source, api_url,
            title, department, location, modality,
            apply_url, last_modified, requisition_id, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company, job_id) DO UPDATE SET
            pulled_at=excluded.pulled_at,
            pulled_date=excluded.pulled_date,
            source=excluded.source,
            api_url=excluded.api_url,
            title=excluded.title,
            department=excluded.department,
            location=excluded.location,
            modality=excluded.modality,
            apply_url=excluded.apply_url,
            last_modified=excluded.last_modified,
            requisition_id=excluded.requisition_id,
            raw_json=excluded.raw_json
    """
    data = [
        (
            r["company"], r["job_id"],
            r["pulled_at"], r["pulled_date"], r["source"], r["api_url"],
            r["title"], r["department"], r["location"], r["modality"],
            r["apply_url"], r["last_modified"], r["requisition_id"], r["raw_json"]
        )
        for r in rows
    ]
    conn.executemany(sql, data)
    conn.commit()


# ----------------------------
# Diffing helpers
# ----------------------------

def get_previous_snapshot_time(conn: sqlite3.Connection, company: str, before_time: str) -> Optional[str]:
    row = conn.execute(
        """
        SELECT MAX(pulled_at)
        FROM job_snapshots
        WHERE company = ? AND pulled_at < ?
        """,
        (company, before_time),
    ).fetchone()
    return row[0] if row and row[0] else None


def load_snapshot_map(conn: sqlite3.Connection, company: str, pulled_at: str) -> Dict[str, Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT job_id, title, department, location, modality, apply_url, last_modified, raw_json
        FROM job_snapshots
        WHERE company = ? AND pulled_at = ?
        """,
        (company, pulled_at),
    ).fetchall()

    out: Dict[str, Dict[str, Any]] = {}
    for (job_id, title, department, location, modality, apply_url, last_modified, raw_json) in rows:
        out[job_id] = {
            "job_id": job_id,
            "title": title,
            "department": department,
            "location": location,
            "modality": modality,
            "apply_url": apply_url,
            "last_modified": last_modified,
            "raw_json": raw_json,
        }
    return out


def _diff_fields(j: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": j.get("title"),
        "department": j.get("department"),
        "location": j.get("location"),
        "modality": j.get("modality"),
        "apply_url": j.get("apply_url"),
        "last_modified": j.get("last_modified"),
    }


def log_changes(
    conn: sqlite3.Connection,
    *,
    pulled_at: str,
    company: str,
    prev_map: Dict[str, Dict[str, Any]],
    new_map: Dict[str, Dict[str, Any]],
) -> None:
    prev_ids = set(prev_map.keys())
    new_ids = set(new_map.keys())

    added = new_ids - prev_ids
    removed = prev_ids - new_ids
    kept = prev_ids & new_ids

    change_rows = []

    for jid in added:
        j = new_map[jid]
        change_rows.append((
            pulled_at, company, jid, "added",
            j.get("title"), j.get("location"), j.get("modality"),
            j.get("apply_url"), j.get("last_modified"),
            json.dumps({"new": _diff_fields(j)}, ensure_ascii=False)
        ))

    for jid in removed:
        j = prev_map[jid]
        change_rows.append((
            pulled_at, company, jid, "removed",
            j.get("title"), j.get("location"), j.get("modality"),
            j.get("apply_url"), j.get("last_modified"),
            json.dumps({"old": _diff_fields(j)}, ensure_ascii=False)
        ))

    fields = ["title", "department", "location", "modality", "apply_url", "last_modified"]
    for jid in kept:
        old = prev_map[jid]
        new = new_map[jid]
        diffs = {}
        for f in fields:
            if str(old.get(f)) != str(new.get(f)):
                diffs[f] = {"old": old.get(f), "new": new.get(f)}
        if diffs:
            change_rows.append((
                pulled_at, company, jid, "changed",
                new.get("title"), new.get("location"), new.get("modality"),
                new.get("apply_url"), new.get("last_modified"),
                json.dumps(diffs, ensure_ascii=False)
            ))

    if not change_rows:
        change_rows.append((
            pulled_at, company, None, "no_change",
            None, None, None, None, None,
            json.dumps({}, ensure_ascii=False)
        ))

    conn.executemany(
        """
        INSERT INTO job_changes (
            pulled_at, company, job_id, change_type,
            title, location, modality, apply_url, last_modified,
            details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        change_rows
    )
    conn.commit()


# ----------------------------
# Source interface + implementations
# ----------------------------

class JobSource(Protocol):
    def name(self) -> str: ...
    def fetch_rows(self, pulled_at: str) -> List[Dict[str, Any]]: ...


class TeamMeSource:
    """
    Your existing TeamMe-like endpoint (Quantum Machines).
    """
    def __init__(self, *, company: str, source: str, api_url: str, timeout_s: int = 30) -> None:
        self.company = company
        self.source = source
        self.api_url = api_url
        self.timeout_s = timeout_s

    def name(self) -> str:
        return f"{self.company} ({self.source})"

    def fetch_rows(self, pulled_at: str) -> List[Dict[str, Any]]:
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
            rows.append(make_row_from_normalized(
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
            ))
        return rows


class GreenhouseSourceAdapter:
    """
    Wraps GreenhouseBoardSource to produce DB-ready rows.
    """
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
            rows.append(make_row_from_normalized(
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
            ))

        return rows


class LeverSourceAdapter:
    """
    Wraps LeverPostingsSource to produce DB-ready rows.
    """
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
            rows.append(make_row_from_normalized(
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
            ))

        return rows


# ----------------------------
# Main runner
# ----------------------------

def main() -> None:
    # Import here so the script still runs even if a source module is temporarily missing.
    from quantum_jobs.sources.greenhouse_companies import ionq_source, psiquantum_source
    from quantum_jobs.sources.lever_companies import rigetti_source, atomcomputing_source, quantinuum_source, qctrl_source

    SOURCES: List[JobSource] = [
        # Existing single-source (TeamMe) company
        TeamMeSource(
            company="Quantum Machines",
            source="teamme.link",
            api_url="https://teamme.link/api/projects/e1b1ebc1-c84e-4c70-a322-fd628476b5b2/positions",
            timeout_s=TIMEOUT_S
        ),

        # Greenhouse-based companies
        GreenhouseSourceAdapter(ionq_source()),
        GreenhouseSourceAdapter(psiquantum_source()),

        # Lever-based companies
        LeverSourceAdapter(rigetti_source()),
        LeverSourceAdapter(atomcomputing_source()),
        LeverSourceAdapter(quantinuum_source()),
        LeverSourceAdapter(qctrl_source()),
    ]

    pulled_at = utc_now_iso()

    conn = connect_db(DB_PATH)
    try:
        init_schema(conn)

        for src in SOURCES:
            logging.info(f"Fetching source: {src.name()}")
            rows = src.fetch_rows(pulled_at)

            rows = [r for r in rows if r.get("company") and r.get("job_id")]
            if not rows:
                logging.warning(f"No jobs returned (or missing IDs) for {src.name()}")
                continue

            # Derive company from the rows (safe because adapters stamp company per row)
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
    try:
        main()
        logging.info("Collector finished successfully")
    except Exception:
        logging.exception("Collector failed")
        raise
