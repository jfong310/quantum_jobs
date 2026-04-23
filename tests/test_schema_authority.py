from __future__ import annotations

import types

from quantum_jobs import collector, db


def test_init_schema_has_no_inline_alter_upgrade_logic() -> None:
    init_consts = [c for c in db.init_schema.__code__.co_consts if isinstance(c, str)]
    ddl = "\n".join(init_consts)

    assert "ALTER TABLE" not in ddl


def test_collector_main_runs_migrations_before_legacy_main(monkeypatch) -> None:
    events: list[str] = []

    class _Conn:
        def close(self) -> None:
            events.append("close")

    def fake_connect_db(path: str) -> _Conn:
        events.append("connect")
        return _Conn()

    def fake_run_all_migrations(conn: _Conn) -> list[str]:
        events.append("migrate")
        return []

    def fake_load_legacy_module(kind: str, alias: str):
        def _legacy_main() -> None:
            events.append("legacy_main")

        return types.SimpleNamespace(main=_legacy_main)

    monkeypatch.setattr(collector, "_LEGACY", None)
    monkeypatch.setattr(collector.migrations, "connect_db", fake_connect_db)
    monkeypatch.setattr(collector.migrations, "run_all_migrations", fake_run_all_migrations)
    monkeypatch.setattr(collector, "load_legacy_module", fake_load_legacy_module)

    collector.main()

    assert events == ["connect", "migrate", "close", "legacy_main"]
