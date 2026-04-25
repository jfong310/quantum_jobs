df = run_query("""
SELECT pulled_at, substr(pulled_at, 1, 10) AS derived_date, pulled_date
FROM job_snapshots
LIMIT 5;
""")
df

