from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]


# Stable aliases for legacy files while we migrate to package-based modules.
LEGACY_FILES = {
    "collector": REPO_ROOT / "legacy" / "collector_legacy.py",
    "migrations": REPO_ROOT / "legacy" / "migration_utils_legacy.py",
}


def load_legacy_module(kind: str, alias: str) -> ModuleType:
    """Load a legacy module from a file path with a stable alias."""
    if kind not in LEGACY_FILES:
        raise KeyError(f"Unsupported legacy module kind: {kind}")

    module_path = LEGACY_FILES[kind]
    spec = importlib.util.spec_from_file_location(alias, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module
