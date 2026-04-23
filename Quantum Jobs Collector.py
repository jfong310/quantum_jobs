"""Backward-compatible shim for the legacy collector script path."""

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from legacy.collector_legacy import *  # noqa: F401,F403


if __name__ == "__main__":
    from quantum_jobs.collector import main as collect_main

    collect_main()
