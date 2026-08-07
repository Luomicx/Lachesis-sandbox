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
    KNOWLEDGE_BASE_ENABLED = (
        os.environ.get("LACHESIS_KNOWLEDGE_BASE_ENABLED", "true").lower() == "true"
    )
    KNOWLEDGE_BASE_PROVIDER = os.environ.get("LACHESIS_KNOWLEDGE_BASE_PROVIDER", "filesystem")
    KNOWLEDGE_BASE_DIR = os.environ.get("LACHESIS_KNOWLEDGE_BASE_DIR")
    CAREER_DOCUMENT_MAX_BYTES = 10 * 1024 * 1024
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
