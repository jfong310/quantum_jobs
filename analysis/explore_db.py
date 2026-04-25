"""Quick script for lightweight database exploration."""

from __future__ import annotations

import sqlite3

import pandas as pd


try:
    from quantum_jobs.db.paths import DB_PATH
except Exception:
    DB_PATH = "quantum_jobs.db"


conn = sqlite3.connect(str(DB_PATH))

query = """
SELECT
    company,
    COALESCE(pulled_date, substr(pulled_at, 1, 10)) AS snapshot_date,
    COUNT(*) AS job_count
FROM job_snapshots
GROUP BY company, snapshot_date
ORDER BY snapshot_date DESC, company
LIMIT 20;
"""

df = pd.read_sql(query, conn)
print(df.head())

conn.close()
