from __future__ import annotations


def test_migrations_module_exposes_expected_api() -> None:
    from quantum_jobs import migrations

    assert callable(migrations.connect_db)
    assert callable(migrations.run_all_migrations)


def test_collector_module_exposes_expected_helpers() -> None:
    from quantum_jobs import collector

    assert collector.normalize_str("  hello   world  ") == "hello world"
