import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\warfm\PycharmProjects\PythonProject\AI Code\Quantum Jobs\quantum_jobs.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys=ON;")

def q(sql, params=()):
    return conn.execute(sql, params).fetchall()

###

rows = q("""
    SELECT pulled_at, pulled_date
    FROM job_snapshots
    ORDER BY snapshot_id DESC
    LIMIT 10
""")

for row in rows:
    print(row)

###

conn.close()