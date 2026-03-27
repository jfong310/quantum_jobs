from __future__ import annotations

from types import ModuleType
from typing import Any

from ._legacy_loader import load_legacy_module


_LEGACY: ModuleType | None = None


def _legacy() -> ModuleType:
    global _LEGACY
    if _LEGACY is None:
        _LEGACY = load_legacy_module("migrations", "quantum_jobs_legacy_migrations")
    return _LEGACY


def __getattr__(name: str) -> Any:
    return getattr(_legacy(), name)
