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
--   Builds canonical daily counts per company by selecting the latest snapshot
--   timestamp per (company, date), then counting distinct job_id values.
-- Why it matters:
--   Multiple collector runs on the same day can inflate counts if rows are
--   aggregated naively across all snapshots for that day.
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
ORDER BY d.snapshot_date, s.company;


-- =====================================================
-- 3b) Collector Runs Per Company-Day
-- =====================================================
-- What this does:
--   Shows how many distinct collection runs happened per (company, date).
-- Why it matters:
--   Quickly surfaces dates where multi-run inflation risk exists.
SELECT
    company,
    COALESCE(pulled_date, substr(pulled_at, 1, 10)) AS snapshot_date,
    COUNT(DISTINCT pulled_at) AS collector_runs,
    COUNT(*) AS raw_rows
FROM job_snapshots
GROUP BY company, snapshot_date
HAVING COUNT(DISTINCT pulled_at) > 1
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
