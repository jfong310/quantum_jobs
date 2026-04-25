-- =====================================================
-- 1) Snapshot Integrity
-- =====================================================
-- What this does:
--   Checks for duplicate snapshot keys (pulled_at, company, job_id).
-- Why it matters:
--   Duplicates can skew trends and company-level counts.
SELECT
    pulled_at,
    company,
    job_id,
    COUNT(*) AS row_count
FROM job_snapshots
GROUP BY pulled_at, company, job_id
HAVING COUNT(*) > 1
ORDER BY row_count DESC, pulled_at DESC;


-- =====================================================
-- 2) Latest Snapshot Per Company
-- =====================================================
-- What this does:
--   Finds the most recent snapshot timestamp for each company.
-- Why it matters:
--   Confirms recency and helps detect stale company feeds.
SELECT
    company,
    MAX(pulled_at) AS latest_pulled_at
FROM job_snapshots
GROUP BY company
ORDER BY latest_pulled_at DESC;


-- =====================================================
-- 3) Jobs Over Time
-- =====================================================
-- What this does:
--   Counts jobs per company per day using pulled_date (or fallback from pulled_at).
-- Why it matters:
--   Shows hiring volume trends and directional changes over time.
SELECT
    company,
    COALESCE(pulled_date, substr(pulled_at, 1, 10)) AS snapshot_date,
    COUNT(*) AS job_count
FROM job_snapshots
GROUP BY company, snapshot_date
ORDER BY snapshot_date, company;


-- =====================================================
-- 4) Jobs by Company
-- =====================================================
-- What this does:
--   Aggregates total snapshot rows by company.
-- Why it matters:
--   Provides a quick distribution of volume across companies.
SELECT
    company,
    COUNT(*) AS total_snapshot_rows
FROM job_snapshots
GROUP BY company
ORDER BY total_snapshot_rows DESC, company;
