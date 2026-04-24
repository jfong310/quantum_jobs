# Phase 5 Readiness Audit (Phases 0–4)

Date: 2026-04-24 (UTC)

## Judgment

**Ready for Phase 5: Yes**

The readiness-hardening pass is complete. Pre-cleanup blockers from this audit were addressed with minimal, compatibility-safe updates, while intentionally deferring actual shim removals and structural cleanup to Phase 5.

## Phase-by-phase status

### Phase 0 — Safety baseline
- **Partial / not evidenced in-repo (non-blocking for Phase 5 code cleanup)**.
- I did not find committed baseline artifacts (row counts, per-company current counts, latest change_type stats, saved stdout/log pair) tracked in repo. If needed, regenerate before making behavior-changing cleanup edits.

### Phase 1 — Package scaffolding only
- **Complete**.
- Package scaffolding exists (`quantum_jobs/`, `quantum_jobs/db/`, `quantum_jobs/cli/`, `quantum_jobs/sources/`).
- Wrapper scripts and compatibility entry points exist.

### Phase 2 — Pure moves with compatibility shims
- **Complete (with expected shims still present)**.
- Legacy forwarding shims are still present at old paths and forwarding to package modules.
- Migration IDs remain stable (`0001...`, `0002...`) in migration registry.

### Phase 3 — Path unification
- **Complete for runtime paths**.
- Central DB path authority exists at `quantum_jobs/db/paths.py` and is used by collector/migration entry points.
- Notebook helper files were updated to use centralized path import where feasible.

### Phase 4 — Schema authority consolidation
- **Functionally complete**.
- Collector orchestrator runs migrations before invoking legacy collector main.
- `init_schema` in package DB module contains base DDL and no inline `ALTER TABLE` upgrade logic.
- Migration `ALTER TABLE` logic remains in migration system (as intended).

## Key findings requested in audit brief

### Forwarding stubs still present
- `migration_utils.py` forwards to `legacy.migration_utils_legacy`.
- `Quantum Jobs Collector.py` forwards to `legacy.collector_legacy` (and runs new collector main when executed directly).
- `collectors/sources/*` modules forward to `quantum_jobs.sources.*`.
- `quantum_jobs/migrations.py` and `quantum_jobs/collector.py` are wrappers over legacy implementations via loader.

### Duplicate DB path definitions
- Canonical path is centralized in `quantum_jobs/db/paths.py`.
- Previously non-canonical notebook path literals were updated:
  - `quantum_jobs_db_inspector.ipynb.py` now imports `DB_PATH` from `quantum_jobs.db.paths`.
  - `Quantum_Job_Visualization_Quantum Machines.ipynb` now imports `DB_PATH` from `quantum_jobs.db.paths`.

### Inline schema ALTER logic outside migrations
- In runtime core package path, no inline `ALTER TABLE` detected in `quantum_jobs/db/__init__.py`.
- `ALTER TABLE` appears in legacy migration utility (expected authority location for migrations).

### Migration IDs accidentally renamed
- No evidence of accidental rename; IDs are:
  - `0001_add_pulled_date_job_snapshots`
  - `0002_add_pulled_date_current_and_changes`

### Scripts/tests still importing legacy paths
- Tests intentionally import legacy paths to validate shims and backward compatibility.
- Legacy collector still imports from `collectors.sources.*` shim paths by design.

### Notebooks/scripts/docs referencing old paths
- README now describes package-first canonical runtime structure and clearly labels legacy entry points as compatibility-only.
- Notebook helper DB path examples were aligned to centralized DB path guidance.

### Windows Task Scheduler entry-point risks
- `scripts/run_collector.py` includes `sys.path` insertion for direct script execution and should work when launched via Python from repo context.
- `Quantum Jobs Collector.py` filename contains spaces; scheduler invocations must quote path correctly.
- README now documents Windows Task Scheduler-safe invocation examples with quoted full paths and package-first script preference.

### Optional dependency import fragility (`requests`)
- Source adapters were hardened to use lazy default session creation so importing source modules/shims does not immediately fail when `requests` is unavailable in minimal test/smoke environments.
- Actual network fetch behavior remains unchanged when dependencies are installed.

## Checks executed

1. Test suite
   - `pytest -q`
   - Result: **15 passed**.

2. Migration smoke (isolated temp DB, no repo DB mutation)
   - Initialized schema on temp DB and ran migrations twice.
   - First run applied `0001`, `0002`; second run applied none.

3. Collector orchestration smoke (isolated monkeypatched run)
   - Validated call order: connect temp DB path -> run migrations -> close -> call legacy main.

4. Legacy shim import smoke
   - Legacy/source shim imports now succeed without eager `requests` import at module import-time.
   - Explicit stub-based compatibility test still passes.

## What changed in this readiness-hardening pass

1. Updated README to package-first canonical structure and clarified compatibility-only legacy entry points.
2. Added explicit Windows Task Scheduler guidance using quoted Python script paths.
3. Updated notebook helper DB path usage to centralized `quantum_jobs.db.paths.DB_PATH`.
4. Hardened source adapter imports against eager optional dependency failures by using lazy default session creation.

## Intentionally deferred to Phase 5

1. Remove/retire forwarding stubs in planned order after compatibility window ends.
2. Continue documentation cleanup beyond core readiness notes (historical references may still exist in ancillary artifacts).
3. Decide whether and how to retire legacy top-level scripts after compatibility window ends.
4. Decide whether `query_db.py` should be repaired, archived, or replaced with a maintained CLI/query helper.
5. Preserve migration IDs and migration ledger continuity during cleanup.
