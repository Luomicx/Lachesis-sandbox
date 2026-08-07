from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import shutil
import sys
import unittest
from uuid import uuid4

from werkzeug.datastructures import MultiDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app


def complete_baseline() -> dict:
    return {
        "school": "Example University",
        "major": "Computer Science",
        "graduation_year": "2027",
        "gpa_or_rank": "3.6/4.0",
        "skills": ["Python", "Data structures"],
        "target_city": "Shanghai",
        "budget": 80000,
        "family_support": "moderate",
        "constraints": "Can study 20 hours per week",
        "long_term_goal": "Backend engineer",
    }


class DocumentIntakeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = BACKEND_DIR / ".test-data" / uuid4().hex
        self.client = self._create_client()

    def tearDown(self) -> None:
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def test_draft_baseline_can_be_completed_and_confirmed(self) -> None:
        null_baseline_case = self.client.post(
            "/api/cases",
            json={"name": "Lin", "baseline": None},
        )
        self.assertEqual(null_baseline_case.status_code, 400)
        self.assertEqual(null_baseline_case.get_json()["error"]["code"], "validation_error")

        created_case = self._create_case()
        case_id = created_case["id"]
        self.assertEqual(created_case["status"], "draft")
        self.assertEqual(created_case["baseline_version"], 0)

        updated_case = self.client.patch(
            f"/api/cases/{case_id}",
            json={"baseline": {"school": "Example University"}},
        )
        self.assertEqual(updated_case.status_code, 200)
        self.assertEqual(updated_case.get_json()["data"]["status"], "intake")
        self.assertEqual(updated_case.get_json()["data"]["baseline_version"], 1)

        unchanged_case = self.client.patch(
            f"/api/cases/{case_id}",
            json={"baseline": {"school": "Example University"}},
        )
        self.assertEqual(unchanged_case.status_code, 200)
        self.assertEqual(unchanged_case.get_json()["data"]["baseline_version"], 1)

        incomplete_confirmation = self.client.post(f"/api/cases/{case_id}/confirm")
        self.assertEqual(incomplete_confirmation.status_code, 400)
        self.assertEqual(incomplete_confirmation.get_json()["error"]["code"], "validation_error")
        self.assertIn("major", incomplete_confirmation.get_json()["error"]["details"]["missing_fields"])

        remaining_baseline = complete_baseline()
        del remaining_baseline["school"]
        completed_case = self.client.patch(
            f"/api/cases/{case_id}",
            json={"baseline": remaining_baseline},
        )
        self.assertEqual(completed_case.status_code, 200)
        self.assertEqual(completed_case.get_json()["data"]["baseline_version"], 2)

        confirmed_case = self.client.post(f"/api/cases/{case_id}/confirm")
        self.assertEqual(confirmed_case.status_code, 200)
        self.assertEqual(confirmed_case.get_json()["data"]["status"], "confirmed")

        repeated_confirmation = self.client.post(f"/api/cases/{case_id}/confirm")
        self.assertEqual(repeated_confirmation.status_code, 200)
        self.assertEqual(repeated_confirmation.get_json()["data"]["status"], "confirmed")

        rejected_update = self.client.patch(
            f"/api/cases/{case_id}",
            json={"baseline": {"target_city": "Beijing"}},
        )
        self.assertEqual(rejected_update.status_code, 409)
        self.assertEqual(rejected_update.get_json()["error"]["code"], "invalid_state")

        rejected_upload = self._upload(
            case_id,
            "resume.pdf",
            "application/pdf",
            b"contents",
        )
        self.assertEqual(rejected_upload.status_code, 409)
        self.assertEqual(rejected_upload.get_json()["error"]["code"], "invalid_state")

    def test_uploads_allowed_documents_with_case_isolation(self) -> None:
        first_case_id = self._create_case()["id"]
        second_case_id = self._create_case()["id"]
        allowed_documents = (
            ("resume.pdf", "application/pdf", b"pdf contents"),
            ("notes.txt", "text/plain", b"plain text contents"),
            (
                "profile.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                b"docx contents",
            ),
            ("portrait.jpg", "image/jpeg", b"jpeg contents"),
            ("portfolio.png", "image/png", b"png contents"),
        )

        uploaded_documents = []
        for filename, content_type, content in allowed_documents:
            with self.subTest(filename=filename):
                response = self._upload(first_case_id, filename, content_type, content)
                self.assertEqual(response.status_code, 201)
                document = response.get_json()["data"]
                uploaded_documents.append(document)
                self.assertEqual(document["case_id"], first_case_id)
                self.assertEqual(document["original_filename"], filename)
                self.assertEqual(document["content_type"], content_type)
                self.assertEqual(document["size_bytes"], len(content))
                self.assertEqual(document["storage_status"], "stored")
                self.assertNotIn("path", document)
                self.assertNotIn("storage_name", document)
                stored_object = (
                    self.data_dir
                    / "knowledge-base"
                    / first_case_id
                    / "documents"
                    / "objects"
                    / f"{document['id']}{Path(filename).suffix.lower()}"
                )
                self.assertEqual(stored_object.read_bytes(), content)

        second_case_document = self._upload(
            second_case_id,
            "resume.pdf",
            "application/pdf",
            b"other case contents",
        ).get_json()["data"]
        self.assertNotEqual(uploaded_documents[0]["id"], second_case_document["id"])
        self.assertFalse(
            (
                self.data_dir
                / "knowledge-base"
                / first_case_id
                / "documents"
                / "objects"
                / f"{second_case_document['id']}.pdf"
            ).exists()
        )

        listed_documents = self.client.get(f"/api/cases/{first_case_id}/documents")
        self.assertEqual(listed_documents.status_code, 200)
        self.assertEqual(len(listed_documents.get_json()["data"]), len(allowed_documents))
        self.assertEqual(self._get_case(first_case_id)["status"], "intake")

    def test_duplicate_names_and_invalid_uploads_leave_no_documents(self) -> None:
        case_id = self._create_case()["id"]

        first_upload = self._upload(case_id, "resume.pdf", "application/pdf", b"first")
        second_upload = self._upload(case_id, "resume.pdf", "application/pdf", b"second")
        self.assertEqual(first_upload.status_code, 201)
        self.assertEqual(second_upload.status_code, 201)
        self.assertNotEqual(first_upload.get_json()["data"]["id"], second_upload.get_json()["data"]["id"])

        invalid_requests = (
            self.client.post(f"/api/cases/{case_id}/documents", json={}),
            self._upload(case_id, "../escape.pdf", "application/pdf", b"invalid"),
            self._upload(case_id, "wrong.pdf", "text/plain", b"invalid"),
            self._upload(case_id, "archive.zip", "application/zip", b"invalid"),
            self._upload(case_id, "empty.txt", "text/plain", b""),
        )
        for response in invalid_requests:
            with self.subTest(status_code=response.status_code):
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], "validation_error")

        listed_documents = self.client.get(f"/api/cases/{case_id}/documents")
        self.assertEqual(len(listed_documents.get_json()["data"]), 2)

        multiple_files = self.client.post(
            f"/api/cases/{case_id}/documents",
            data=MultiDict(
                [
                    ("file", (BytesIO(b"first"), "first.pdf", "application/pdf")),
                    ("file", (BytesIO(b"second"), "second.pdf", "application/pdf")),
                ]
            ),
        )
        self.assertEqual(multiple_files.status_code, 400)
        self.assertEqual(multiple_files.get_json()["error"]["code"], "validation_error")

        unknown_case_upload = self._upload(
            "case_0123456789ab",
            "resume.pdf",
            "application/pdf",
            b"invalid",
        )
        self.assertEqual(unknown_case_upload.status_code, 404)
        self.assertEqual(unknown_case_upload.get_json()["error"]["code"], "not_found")

    def test_rejects_oversized_requests_and_unavailable_storage(self) -> None:
        size_limited_client = self._create_client({"CAREER_DOCUMENT_MAX_BYTES": 4})
        size_limited_case_id = self._create_case(size_limited_client)["id"]
        oversized_document = self._upload(
            size_limited_case_id,
            "resume.pdf",
            "application/pdf",
            b"12345",
            client=size_limited_client,
        )
        self.assertEqual(oversized_document.status_code, 400)
        self.assertEqual(oversized_document.get_json()["error"]["code"], "validation_error")

        request_limited_client = self._create_client({"MAX_CONTENT_LENGTH": 1024})
        request_limited_case_id = self._create_case(request_limited_client)["id"]
        request_too_large = self._upload(
            request_limited_case_id,
            "resume.pdf",
            "application/pdf",
            b"x" * 4096,
            client=request_limited_client,
        )
        self.assertEqual(request_too_large.status_code, 413)
        self.assertEqual(request_too_large.get_json()["error"]["code"], "payload_too_large")

        unavailable_client = self._create_client({"KNOWLEDGE_BASE_ENABLED": False})
        unavailable_case_id = self._create_case(unavailable_client)["id"]
        unavailable_response = self._upload(
            unavailable_case_id,
            "resume.pdf",
            "application/pdf",
            b"contents",
            client=unavailable_client,
        )
        self.assertEqual(unavailable_response.status_code, 503)
        self.assertEqual(unavailable_response.get_json()["error"]["code"], "storage_unavailable")

        invalid_provider_client = self._create_client({"KNOWLEDGE_BASE_PROVIDER": "unsupported"})
        invalid_provider_case_id = self._create_case(invalid_provider_client)["id"]
        invalid_provider_response = self._upload(
            invalid_provider_case_id,
            "resume.pdf",
            "application/pdf",
            b"contents",
            client=invalid_provider_client,
        )
        self.assertEqual(invalid_provider_response.status_code, 503)
        self.assertEqual(invalid_provider_response.get_json()["error"]["code"], "storage_unavailable")

    def test_rejects_symlinked_document_directory(self) -> None:
        case_id = self._create_case()["id"]
        collection_directory = self.client.application.extensions["knowledge_base"].create_collection(case_id)
        external_directory = self.data_dir / "external-documents"
        external_directory.mkdir()
        documents_link = collection_directory / "documents"
        try:
            os.symlink(external_directory, documents_link, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Symbolic links are unavailable in this test environment: {error}")

        response = self._upload(case_id, "resume.pdf", "application/pdf", b"contents")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "storage_error")
        self.assertEqual(list(external_directory.iterdir()), [])

    def _create_client(self, config_overrides: dict[str, object] | None = None):
        configuration = {"TESTING": True, "DATA_DIR": str(self.data_dir)}
        if config_overrides:
            configuration.update(config_overrides)
        return create_app(configuration).test_client()

    def _create_case(self, client=None) -> dict:
        active_client = client or self.client
        response = active_client.post("/api/cases", json={"name": "Lin"})
        self.assertEqual(response.status_code, 201)
        return response.get_json()["data"]

    def _get_case(self, case_id: str) -> dict:
        response = self.client.get(f"/api/cases/{case_id}")
        self.assertEqual(response.status_code, 200)
        return response.get_json()["data"]

    def _upload(
        self,
        case_id: str,
        filename: str,
        content_type: str,
        content: bytes,
        client=None,
    ):
        active_client = client or self.client
        return active_client.post(
            f"/api/cases/{case_id}/documents",
            data={"file": (BytesIO(content), filename, content_type)},
        )


if __name__ == "__main__":
    unittest.main()
