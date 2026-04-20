from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional


def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Create/upgrade the collector tables.

    `pulled_date` is a derived convenience field from `pulled_at` for grouping.
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

    # Best-effort migration for existing DBs missing pulled_date columns.
    try:
        conn.execute("ALTER TABLE job_snapshots ADD COLUMN pulled_date TEXT;")
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE job_current ADD COLUMN pulled_date TEXT;")
    except sqlite3.OperationalError:
        pass

    conn.commit()


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
