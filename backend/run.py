"""
backend/ 目录：后端应用根目录。
本文件为本地开发入口，负责创建 Flask 应用并按环境变量启动服务。
"""
from __future__ import annotations

import os

from app import create_app


def main() -> None:
    app = create_app()
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", "5001")),
        debug=app.config["DEBUG"],
    )


if __name__ == "__main__":
    main()
