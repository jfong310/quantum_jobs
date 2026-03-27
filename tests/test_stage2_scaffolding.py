from __future__ import annotations

import sys
import types


def _install_requests_stub() -> None:
    if "requests" in sys.modules:
        return

    class _DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {}

    class Session:
        def get(self, *args, **kwargs):
            return _DummyResponse()

    def get(*args, **kwargs):
        return _DummyResponse()

    mod = types.ModuleType("requests")
    mod.RequestException = Exception
    mod.Session = Session
    mod.get = get
    sys.modules["requests"] = mod


def test_stage2_migrations_wrapper_exposes_legacy_api() -> None:
    from quantum_jobs import migrations

    assert callable(migrations.connect_db)
    assert callable(migrations.run_all_migrations)


def test_stage2_collector_wrapper_exposes_legacy_api() -> None:
    _install_requests_stub()
    from quantum_jobs import collector

    assert collector.normalize_str("  hello   world  ") == "hello world"
