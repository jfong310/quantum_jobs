from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]


def _ensure_requests_stub() -> None:
    """Provide a lightweight requests stub when dependency isn't installed."""
    if "requests" in sys.modules:
        return

    class RequestException(Exception):
        pass

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
    mod.RequestException = RequestException
    mod.Session = Session
    mod.get = get
    sys.modules["requests"] = mod


def load_module_from_repo(rel_path: str, module_name: str) -> ModuleType:
    """Load a Python module directly from a repository-relative path."""
    _ensure_requests_stub()

    module_path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
