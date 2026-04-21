"""Backward-compatible shim for the legacy migration utilities path."""

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from legacy.migration_utils_legacy import *  # noqa: F401,F403
