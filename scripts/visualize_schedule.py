from __future__ import annotations

import sys
import argparse
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantum_jobs.visualizer import generate_run_history_heatmap, print_console_heatmap
from quantum_jobs.db.paths import DB_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize the collector run schedule.")
    parser.add_argument("--png", action="store_true", help="Generate a PNG image (run_history.png)")
    parser.add_argument("--weeks", type=int, default=4, help="Number of weeks for console view (default: 4)")
    args = parser.parse_args()

    if args.png:
        output_file = "run_history.png"
        generate_run_history_heatmap(str(DB_PATH), output_file)
    else:
        print_console_heatmap(str(DB_PATH), weeks=args.weeks)


if __name__ == "__main__":
    main()
