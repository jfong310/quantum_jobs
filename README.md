# Quantum Jobs Tracker

A data-driven tool for collecting and analyzing hiring trends across quantum computing companies.

## Canonical runtime entry points (Phase 1–4 state)

Use these package-aligned scripts as the primary operational entry points:

- Collector: `python scripts/run_collector.py`
- Migrations: `python scripts/run_migrations.py`

Legacy compatibility entry points are still present for backward compatibility during the refactor window:

- `Quantum Jobs Collector.py`
- `run_migrations.py`
- `migration_utils.py`
- `collectors/sources/*` shims

## Project structure (current)

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
├── legacy/
│   ├── collector_legacy.py
│   └── migration_utils_legacy.py
└── tests/
```

## Database path behavior

The canonical runtime DB path is centralized at:

- `quantum_jobs.db.paths.DB_PATH`

It intentionally resolves to the repository root file:

- `<repo-root>/quantum_jobs.db`

This behavior is preserved for compatibility.

## Windows Task Scheduler guidance

For reliability, run scripts through Python and quote full paths (especially filenames with spaces):

```powershell
python "C:\path\to\quantum_jobs\scripts\run_migrations.py"
python "C:\path\to\quantum_jobs\scripts\run_collector.py"
```

Legacy file with spaces should also be quoted if used:

```powershell
python "C:\path\to\quantum_jobs\Quantum Jobs Collector.py"
```

## Notes

- Notebook and analysis artifacts may contain historical/local path examples.
- Phase 5 is intended to remove compatibility shims after the compatibility window.
