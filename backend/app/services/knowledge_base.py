"""
services/ 目录：业务服务层。
本文件实现按 case 隔离的知识库边界与文件系统提供者，
定义健康状态并拒绝不安全的 case ID，不引入可选外部依赖。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class KnowledgeBaseHealth:
    """可安全暴露到 ``/health`` 的提供者无关健康信息。"""

    provider: str
    status: str
    case_isolation: bool = True
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        health_payload: dict[str, Any] = {
            "provider": self.provider,
            "status": self.status,
            "case_isolation": self.case_isolation,
        }
        if self.message:
            health_payload["message"] = self.message
        return health_payload


class KnowledgeBase(Protocol):
    """按 case 隔离的知识存储边界。

    未来的提供者必须通过此外观增加文档索引与搜索，
    而非让 career 服务依赖提供者特有的类型。
    """

    def health(self) -> KnowledgeBaseHealth:
        """返回提供者当前的依赖状态。"""

    def create_collection(self, case_id: str) -> Path:
        """创建并返回某个 career case 的隔离集合。"""


class FilesystemKnowledgeBase:
    """本地、无依赖的提供者，为每个 case 预留一个目录。"""

    provider_name = "filesystem"
    case_id_pattern = re.compile(r"case_[0-9a-f]{12}\Z")

    def __init__(self, root_directory: str | Path) -> None:
        self.root_directory = Path(root_directory)

    def health(self) -> KnowledgeBaseHealth:
        if self.root_directory.exists() and not self.root_directory.is_dir():
            return KnowledgeBaseHealth(
                provider=self.provider_name,
                status="invalid",
                case_isolation=False,
                message="The local knowledge-base path is not a directory.",
            )

        try:
            self.root_directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            return KnowledgeBaseHealth(
                provider=self.provider_name,
                status="unavailable",
                case_isolation=False,
                message="The local knowledge-base directory is unavailable.",
            )

        return KnowledgeBaseHealth(provider=self.provider_name, status="ready")

    def create_collection(self, case_id: str) -> Path:
        validated_case_id = self._validate_case_id(case_id)
        current_health = self.health()
        if current_health.status != "ready":
            raise RuntimeError(current_health.message or "Knowledge base is unavailable.")

        resolved_root_directory = self.root_directory.resolve()
        collection_directory = resolved_root_directory / validated_case_id
        if collection_directory.is_symlink():
            raise ValueError("Knowledge-base collections cannot be symbolic links.")
        collection_directory.mkdir(exist_ok=True)

        resolved_collection_directory = collection_directory.resolve()
        if collection_directory.is_symlink() or (
            resolved_collection_directory.parent != resolved_root_directory
        ):
            raise ValueError("Knowledge-base collections must remain inside their root directory.")
        return collection_directory

    @classmethod
    def _validate_case_id(cls, case_id: str) -> str:
        if not cls.case_id_pattern.fullmatch(case_id):
            raise ValueError(
                "Case identifiers must use the generated case_<12 hex characters> format."
            )
        return case_id


class UnavailableKnowledgeBase:
    """针对禁用提供者或不可用依赖的安全占位实现。"""

    def __init__(self, provider_name: str, message: str) -> None:
        self.provider_name = provider_name
        self.message = message

    def health(self) -> KnowledgeBaseHealth:
        return KnowledgeBaseHealth(
            provider=self.provider_name,
            status="unavailable",
            case_isolation=False,
            message=self.message,
        )

    def create_collection(self, case_id: str) -> Path:
        raise RuntimeError(self.message)


class InvalidKnowledgeBase:
    """针对不支持或配置错误的提供者的安全占位实现。"""

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def health(self) -> KnowledgeBaseHealth:
        return KnowledgeBaseHealth(
            provider=self.provider_name,
            status="invalid",
            case_isolation=False,
            message="The configured knowledge-base provider is unsupported.",
        )

    def create_collection(self, case_id: str) -> Path:
        raise RuntimeError("The configured knowledge-base provider is unsupported.")


def create_knowledge_base(configuration: Mapping[str, Any]) -> KnowledgeBase:
    """在不导入可选集成的前提下构建所配置的提供者。"""

    configured_provider = str(configuration.get("KNOWLEDGE_BASE_PROVIDER", "filesystem"))
    provider_name = configured_provider.strip().lower()
    if not configuration.get("KNOWLEDGE_BASE_ENABLED", True):
        return UnavailableKnowledgeBase(provider_name, "The knowledge base is disabled.")

    if provider_name != FilesystemKnowledgeBase.provider_name:
        return InvalidKnowledgeBase(provider_name)

    configured_directory = configuration.get("KNOWLEDGE_BASE_DIR")
    if configured_directory:
        root_directory = Path(configured_directory)
    else:
        root_directory = Path(configuration["DATA_DIR"]) / "knowledge-base"
    return FilesystemKnowledgeBase(root_directory)
