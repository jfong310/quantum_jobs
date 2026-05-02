from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantum_jobs.visualizer import generate_run_history_heatmap
from quantum_jobs.db.paths import DB_PATH


def main() -> None:
    output_file = "run_history.png"
    generate_run_history_heatmap(str(DB_PATH), output_file)


if __name__ == "__main__":
    main()
