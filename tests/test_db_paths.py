from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quantum_jobs.db.paths import DB_PATH


def test_db_path_points_to_repo_root_file() -> None:
    assert DB_PATH.name == "quantum_jobs.db"
    assert DB_PATH == REPO_ROOT / "quantum_jobs.db"
