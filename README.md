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

### Direct Execution (No Redirection)
If you do not need to capture output to a file:
- **Program/script:** `C:\path\to\venv\Scripts\python.exe`
- **Add arguments:** `"C:\path\to\repo\scripts\run_collector.py"`

### Execution with Logging (Redirection)
If you use shell features like `/c` or redirection (`>>`), you **must** use `cmd.exe` as the entry point. Using `python.exe` with `/c` will result in a **(0x2)** error.

- **Program/script:** `cmd.exe`
- **Add arguments:** `/c ""C:\path\to\venv\Scripts\python.exe" "C:\path\to\repo\scripts\run_collector.py" >> "C:\path\to\repo\scheduler_run.log" 2>&1"`
- **Start in:** `C:\path\to\repo`

*Note: Use double-quotes around the entire command string after `/c` if paths contain spaces.*

## Notes

- Legacy top-level shim entry points were removed in Phase 5 cleanup.
- Historical/analysis notebook artifacts remain in-repo; runtime collection/migration flows should use canonical entry points above.
