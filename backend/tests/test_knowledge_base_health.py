"""
tests/ 目录：后端集成测试。
本文件覆盖知识库健康状态与按 case 隔离行为。
"""
from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app


class KnowledgeBaseHealthTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = BACKEND_DIR / ".test-data" / uuid4().hex

    def tearDown(self) -> None:
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def test_default_filesystem_provider_is_ready_and_case_isolated(self) -> None:
        client = self._create_client()

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        health_payload = response.get_json()
        self.assertEqual(health_payload["status"], "ok")
        self.assertEqual(
            health_payload["knowledge_base"],
            {
                "provider": "filesystem",
                "status": "ready",
                "case_isolation": True,
            },
        )
        knowledge_base = client.application.extensions["knowledge_base"]
        first_collection = knowledge_base.create_collection("case_0123456789ab")
        second_collection = knowledge_base.create_collection("case_fedcba987654")

        expected_root_directory = self.data_dir / "knowledge-base"
        self.assertTrue(expected_root_directory.is_dir())
        self.assertTrue(first_collection.is_dir())
        self.assertTrue(second_collection.is_dir())
        self.assertNotEqual(first_collection, second_collection)
        self.assertEqual(first_collection.parent, expected_root_directory)
        self.assertEqual(second_collection.parent, expected_root_directory)

        for invalid_case_id in ("../case_0123456789ab", r"case_0123456789ab\outside"):
            with self.subTest(case_id=invalid_case_id):
                with self.assertRaises(ValueError):
                    knowledge_base.create_collection(invalid_case_id)

    def test_disabled_provider_reports_unavailable_without_startup_failure(self) -> None:
        client = self._create_client({"KNOWLEDGE_BASE_ENABLED": False})

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        knowledge_base_health = response.get_json()["knowledge_base"]
        self.assertEqual(knowledge_base_health["provider"], "filesystem")
        self.assertEqual(knowledge_base_health["status"], "unavailable")
        self.assertFalse(knowledge_base_health["case_isolation"])
        self.assertEqual(knowledge_base_health["message"], "The knowledge base is disabled.")

    def test_file_as_filesystem_root_reports_invalid(self) -> None:
        self.data_dir.mkdir(parents=True)
        filesystem_root_file = self.data_dir / "not-a-directory"
        filesystem_root_file.write_text(
            "This file cannot be used as a collection root.",
            encoding="utf-8",
        )
        client = self._create_client({"KNOWLEDGE_BASE_DIR": str(filesystem_root_file)})

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        knowledge_base_health = response.get_json()["knowledge_base"]
        self.assertEqual(knowledge_base_health["provider"], "filesystem")
        self.assertEqual(knowledge_base_health["status"], "invalid")
        self.assertFalse(knowledge_base_health["case_isolation"])

    def test_unknown_provider_reports_invalid_without_startup_failure(self) -> None:
        client = self._create_client({"KNOWLEDGE_BASE_PROVIDER": "unsupported"})

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        knowledge_base_health = response.get_json()["knowledge_base"]
        self.assertEqual(knowledge_base_health["provider"], "unsupported")
        self.assertEqual(knowledge_base_health["status"], "invalid")
        self.assertFalse(knowledge_base_health["case_isolation"])
        self.assertEqual(
            knowledge_base_health["message"],
            "The configured knowledge-base provider is unsupported.",
        )

    def _create_client(self, config_overrides: dict[str, object] | None = None):
        application_config = {
            "TESTING": True,
            "DATA_DIR": str(self.data_dir),
        }
        if config_overrides:
            application_config.update(config_overrides)
        return create_app(application_config).test_client()


if __name__ == "__main__":
    unittest.main()
