# Quantum Jobs Tracker

A data-driven tool for collecting and analyzing hiring trends across quantum computing companies.

## Canonical runtime entry points

Use these package-first entry points:

- Collector: `python -m quantum_jobs.collector`
- Collector (script): `python scripts/run_collector.py`
- Migrations (script): `python scripts/run_migrations.py`

## Project structure (Phase 5)

```text
quantum_jobs/
├── quantum_jobs/
│   ├── cli/
│   │   ├── collect.py
│   │   └── migrate.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── paths.py
│   ├── sources/
│   ├── collector.py
│   └── migrations.py
├── scripts/
│   ├── run_collector.py
│   └── run_migrations.py
├── legacy/                  # archived historical modules (non-canonical)
└── tests/
```

## Database path behavior

The canonical runtime DB path is centralized at `quantum_jobs.db.paths.DB_PATH` and intentionally resolves to `<repo-root>/quantum_jobs.db` for compatibility.

## Windows Task Scheduler guidance

Run through Python with quoted full paths:

```powershell
python "C:\path\to\quantum_jobs\scripts\run_migrations.py"
python "C:\path\to\quantum_jobs\scripts\run_collector.py"
```

## Notes

- Legacy top-level shim entry points were removed in Phase 5 cleanup.
- Historical/analysis notebook artifacts remain in-repo; runtime collection/migration flows should use canonical entry points above.
