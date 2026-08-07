from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from werkzeug.datastructures import FileStorage

from ..errors import APIError
from .career_repository import CareerRepository, utc_now
from .knowledge_base import KnowledgeBase


ALLOWED_DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}
COPY_CHUNK_SIZE = 64 * 1024


class DocumentIntakeService:
    """Store raw, case-private documents without inspecting their content."""

    def __init__(
        self,
        repository: CareerRepository,
        knowledge_base: KnowledgeBase,
        maximum_document_bytes: int,
    ) -> None:
        self.repository = repository
        self.knowledge_base = knowledge_base
        self.maximum_document_bytes = maximum_document_bytes

    def store_document(self, case_id: str, uploaded_file: FileStorage) -> dict[str, Any]:
        case = self.repository.get_case(case_id)
        if case["status"] not in {"draft", "intake"}:
            raise APIError("invalid_state", "Documents can only be added during intake.", 409)

        knowledge_base_health = self.knowledge_base.health()
        if knowledge_base_health.status != "ready":
            raise APIError("storage_unavailable", "Document storage is unavailable.", 503)

        filename, extension, content_type = self._validate_upload(uploaded_file)
        collection_directory = self.knowledge_base.create_collection(case_id)
        documents_directory = self._get_private_directory(
            collection_directory,
            "documents",
            create=True,
        )
        objects_directory = self._get_private_directory(documents_directory, "objects", create=True)
        metadata_directory = self._get_private_directory(documents_directory, "metadata", create=True)

        document_id = f"document_{uuid4().hex[:12]}"
        object_path = objects_directory / f"{document_id}{extension}"
        metadata_path = metadata_directory / f"{document_id}.json"
        bytes_written = self._write_file(uploaded_file, object_path)
        metadata = {
            "id": document_id,
            "case_id": case_id,
            "original_filename": filename,
            "content_type": content_type,
            "size_bytes": bytes_written,
            "storage_status": "stored",
            "created_at": utc_now(),
        }
        try:
            self.repository._write_json(metadata_path, metadata)
            self.repository.begin_intake(case_id)
        except OSError as error:
            object_path.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)
            raise APIError("storage_error", "Document metadata could not be saved.", 500) from error
        return metadata

    def list_documents(self, case_id: str) -> list[dict[str, Any]]:
        self.repository.get_case(case_id)
        knowledge_base_health = self.knowledge_base.health()
        if knowledge_base_health.status != "ready":
            raise APIError("storage_unavailable", "Document storage is unavailable.", 503)
        collection_directory = self.knowledge_base.create_collection(case_id)
        documents_directory = self._get_private_directory(
            collection_directory,
            "documents",
            create=False,
        )
        if documents_directory is None:
            return []
        metadata_directory = self._get_private_directory(
            documents_directory,
            "metadata",
            create=False,
        )
        if metadata_directory is None:
            return []

        document_metadata = []
        for metadata_path in sorted(metadata_directory.glob("*.json")):
            self._validate_private_file(metadata_path, metadata_directory)
            document_metadata.append(self.repository._read_json(metadata_path))
        return document_metadata

    @staticmethod
    def _get_private_directory(
        parent_directory: Path,
        directory_name: str,
        *,
        create: bool,
    ) -> Path | None:
        resolved_parent_directory = parent_directory.resolve()
        if parent_directory.is_symlink() or not resolved_parent_directory.is_dir():
            raise APIError("storage_error", "Document storage is invalid.", 500)

        child_directory = parent_directory / directory_name
        if child_directory.exists():
            if child_directory.is_symlink() or not child_directory.is_dir():
                raise APIError("storage_error", "Document storage is invalid.", 500)
        elif not create:
            return None
        else:
            try:
                child_directory.mkdir()
            except OSError as error:
                raise APIError("storage_error", "Document storage is unavailable.", 500) from error

        resolved_child_directory = child_directory.resolve()
        if resolved_child_directory.parent != resolved_parent_directory:
            raise APIError("storage_error", "Document storage is invalid.", 500)
        return child_directory

    @staticmethod
    def _validate_private_file(file_path: Path, parent_directory: Path) -> None:
        if file_path.is_symlink() or file_path.resolve().parent != parent_directory.resolve():
            raise APIError("storage_error", "Document metadata is invalid.", 500)

    def _validate_upload(self, uploaded_file: FileStorage) -> tuple[str, str, str]:
        filename = uploaded_file.filename or ""
        if not filename or any(character in filename for character in ("/", "\\", "\x00", "\r", "\n")):
            raise APIError("validation_error", "Document filename is invalid.", 400)
        if len(filename.encode("utf-8")) > 255:
            raise APIError("validation_error", "Document filename is too long.", 400)

        extension = Path(filename).suffix.lower()
        content_type = ALLOWED_DOCUMENT_TYPES.get(extension)
        if not content_type or uploaded_file.mimetype != content_type:
            raise APIError("validation_error", "Document type is not supported.", 400)
        return filename, extension, content_type

    def _write_file(self, uploaded_file: FileStorage, object_path: Path) -> int:
        temporary_path: Path | None = None
        bytes_written = 0
        try:
            with tempfile.NamedTemporaryFile("wb", dir=object_path.parent, delete=False) as temporary_file:
                temporary_path = Path(temporary_file.name)
                while chunk := uploaded_file.stream.read(COPY_CHUNK_SIZE):
                    bytes_written += len(chunk)
                    if bytes_written > self.maximum_document_bytes:
                        raise APIError("validation_error", "Document exceeds the size limit.", 400)
                    temporary_file.write(chunk)
            if not bytes_written:
                raise APIError("validation_error", "Document must not be empty.", 400)
            os.replace(temporary_path, object_path)
            return bytes_written
        except OSError as error:
            raise APIError("storage_error", "Document could not be stored.", 500) from error
        finally:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)
