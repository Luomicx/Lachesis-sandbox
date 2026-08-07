"""
app/ 目录：应用核心包。
本文件为 Flask 应用工厂，负责装配各扩展、注册蓝图与统一错误处理。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from .config import Config
from .errors import APIError
from .services.career_repository import CareerRepository
from .services.document_intake import DocumentIntakeService
from .services.knowledge_base import create_knowledge_base


def create_app(config_overrides: dict[str, Any] | None = None) -> Flask:
    """创建独立的 Lachesis 后端应用。"""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    app.json.ensure_ascii = False

    Path(app.config["DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    app.extensions["career_repository"] = CareerRepository(app.config["DATA_DIR"])
    app.extensions["knowledge_base"] = create_knowledge_base(app.config)
    app.extensions["document_intake"] = DocumentIntakeService(
        app.extensions["career_repository"],
        app.extensions["knowledge_base"],
        app.config["CAREER_DOCUMENT_MAX_BYTES"],
    )

    from .api import career_bp

    app.register_blueprint(career_bp, url_prefix="/api")

    @app.get("/health")
    def health() -> tuple[dict[str, object], int]:
        knowledge_base = app.extensions["knowledge_base"]
        return {
            "status": "ok",
            "service": "lachesis-backend",
            "version": "0.1.0",
            "knowledge_base": knowledge_base.health().to_dict(),
        }, 200

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        return jsonify({"error": error.to_dict()}), error.status_code

    @app.errorhandler(404)
    def handle_not_found(_: object):
        return jsonify({"error": {"code": "not_found", "message": "Resource not found."}}), 404

    @app.errorhandler(RequestEntityTooLarge)
    def handle_payload_too_large(_: RequestEntityTooLarge):
        return jsonify({"error": {"code": "payload_too_large", "message": "Request is too large."}}), 413

    return app
