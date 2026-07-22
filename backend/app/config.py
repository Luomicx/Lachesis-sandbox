from __future__ import annotations

import os
from pathlib import Path


class Config:
    """Runtime settings for the standalone local-first backend."""

    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    SECRET_KEY = os.environ.get("SECRET_KEY", "lachesis-development-only")
    JSON_SORT_KEYS = False
    DATA_DIR = os.environ.get(
        "LACHESIS_DATA_DIR",
        str(Path(__file__).resolve().parents[1] / "data"),
    )
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
