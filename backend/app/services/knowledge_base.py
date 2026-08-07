from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class KnowledgeBaseHealth:
    """Provider-neutral health information safe to expose from ``/health``."""

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
    """Boundary for per-case knowledge storage.

    Future providers must add document indexing and search to this facade
    rather than letting career services depend on provider-specific types.
    """

    def health(self) -> KnowledgeBaseHealth:
        """Return the provider's current dependency state."""

    def create_collection(self, case_id: str) -> Path:
        """Create and return the isolated collection for one career case."""


class FilesystemKnowledgeBase:
    """Local, dependency-free provider that reserves one directory per case."""

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
    """Safe placeholder for a disabled provider or unavailable dependency."""

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
    """Safe placeholder for an unsupported or malformed provider setting."""

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
    """Build the configured provider without importing optional integrations."""

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
