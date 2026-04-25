from __future__ import annotations

from quantum_jobs import collector, db


def test_init_schema_has_no_inline_alter_upgrade_logic() -> None:
    init_consts = [c for c in db.init_schema.__code__.co_consts if isinstance(c, str)]
    ddl = "\n".join(init_consts)

    assert "ALTER TABLE" not in ddl


def test_collector_main_runs_migrations_before_source_fetch(monkeypatch) -> None:
    events: list[str] = []

    class _Conn:
        def executescript(self, *_args, **_kwargs):
            return None

        def commit(self):
            return None

        def execute(self, *_args, **_kwargs):
            class _Row:
                def fetchone(self):
                    return [0]

            return _Row()

        def close(self) -> None:
            events.append("close")

    def fake_connect_db(path: str) -> _Conn:
        events.append(f"connect:{path}")
        return _Conn()

    def fake_run_all_migrations(conn: _Conn) -> list[str]:
        events.append("migrate")
        return []

    class _FakeSource:
        def fetch_rows(self, pulled_at: str):
            events.append(f"fetch:{pulled_at}")
            return []

    monkeypatch.setattr(collector.migrations, "connect_db", fake_connect_db)
    monkeypatch.setattr(collector.migrations, "run_all_migrations", fake_run_all_migrations)
    monkeypatch.setattr(collector, "connect_db", fake_connect_db)
    monkeypatch.setattr(collector, "build_sources", lambda: [_FakeSource()])

    collector.main()

    assert events[0].startswith("connect:")
    assert events[1] == "migrate"
    assert events[2] == "close"
    assert events[3].startswith("connect:")
    assert events[4].startswith("fetch:")
    assert events[5] == "close"
