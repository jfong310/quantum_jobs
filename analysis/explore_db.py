"""Quick script for lightweight database exploration."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


cwd = Path.cwd().resolve()
repo_root = next((p for p in [cwd, *cwd.parents] if (p / "quantum_jobs").is_dir()), cwd)

try:
    from quantum_jobs.db.paths import DB_PATH as PROJECT_DB_PATH

    db_path = Path(PROJECT_DB_PATH).resolve()
except Exception:
    db_path = (repo_root / "quantum_jobs.db").resolve()

print(f"Using database: {db_path}")

if not db_path.exists():
    raise FileNotFoundError(
        f"Database not found at {db_path}. "
        "Expected the project database at repo root; refusing to create a blank SQLite file."
    )

conn = sqlite3.connect(f"file:{db_path}?mode=rw", uri=True)

query = """
WITH daily_latest AS (
    SELECT
        company,
        COALESCE(pulled_date, substr(pulled_at, 1, 10)) AS snapshot_date,
        MAX(pulled_at) AS latest_pulled_at
    FROM job_snapshots
    GROUP BY company, snapshot_date
)
SELECT
    s.company,
    d.snapshot_date,
    COUNT(DISTINCT s.job_id) AS job_count
FROM job_snapshots s
JOIN daily_latest d
  ON s.company = d.company
 AND COALESCE(s.pulled_date, substr(s.pulled_at, 1, 10)) = d.snapshot_date
 AND s.pulled_at = d.latest_pulled_at
GROUP BY s.company, d.snapshot_date
ORDER BY d.snapshot_date DESC, s.company
LIMIT 20;
"""

df = pd.read_sql(query, conn)
print(df.head())

conn.close()
