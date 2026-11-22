from __future__ import annotations
import os
from pathlib import Path

PROJECT_NAME = "热档片间"
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("HOTBAY_DB", str(ROOT / "data" / "hotbay.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
TIERS = ("热档", "温档", "冷档")
TIER_ORDER = {"热档": 0, "温档": 1, "冷档": 2}
