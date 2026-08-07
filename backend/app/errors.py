"""
app/ 目录：应用核心包。
本文件定义统一的 API 错误封装，用于跨层安全传递错误码与详情。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class APIError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        error = {"code": self.code, "message": self.message}
        if self.details:
            error["details"] = self.details
        return error
