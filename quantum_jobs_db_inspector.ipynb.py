import sqlite3
from quantum_jobs.db.paths import DB_PATH

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
