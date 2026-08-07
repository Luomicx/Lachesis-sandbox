"""
tests/ 目录：后端集成测试。
本文件覆盖职业案例、路径、场景与仿真的 API 集成行为。
"""
from __future__ import annotations

import sys
import shutil
import unittest
from uuid import uuid4
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app


def baseline() -> dict:
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


class CareerApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = BACKEND_DIR / ".test-data" / uuid4().hex
        app = create_app({"TESTING": True, "DATA_DIR": str(self.data_dir)})
        self.client = app.test_client()

    def tearDown(self) -> None:
        shutil.rmtree(self.data_dir, ignore_errors=True)

    def create_confirmed_case(self) -> str:
        created = self.client.post("/api/cases", json={"name": "Lin", "baseline": baseline()})
        self.assertEqual(created.status_code, 201)
        case_id = created.get_json()["data"]["id"]
        confirmed = self.client.post(f"/api/cases/{case_id}/confirm")
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.get_json()["data"]["status"], "confirmed")
        return case_id

    def create_scenario(self) -> str:
        case_id = self.create_confirmed_case()
        graduate = self.client.post(
            f"/api/cases/{case_id}/paths",
            json={
                "type": "graduate_school",
                "title": "Match graduate programme",
                "details": {"target": "Example University CS"},
            },
        )
        offer = self.client.post(
            f"/api/cases/{case_id}/paths",
            json={
                "type": "offer",
                "title": "Hypothetical backend offer",
                "confidence": "hypothetical",
                "details": {"city": "Shanghai"},
            },
        )
        self.assertEqual(graduate.status_code, 201)
        self.assertEqual(offer.status_code, 201)
        self.assertEqual(offer.get_json()["data"]["confidence"], "hypothetical")
        scenario = self.client.post(
            "/api/scenarios",
            json={
                "case_id": case_id,
                "path_ids": [graduate.get_json()["data"]["id"], offer.get_json()["data"]["id"]],
            },
        )
        self.assertEqual(scenario.status_code, 201)
        return scenario.get_json()["data"]["id"]

    def test_runs_two_paths_and_returns_comparison_and_timeline(self) -> None:
        scenario_id = self.create_scenario()
        run = self.client.post(
            f"/api/scenarios/{scenario_id}/runs",
            json={"run_mode": "quick", "horizon_years": 1},
        )
        self.assertEqual(run.status_code, 201)
        batch = run.get_json()["data"]
        self.assertEqual(batch["completed_worlds"], 20)
        self.assertEqual(batch["failed_seeds"], [])
        self.assertEqual(len(batch["aggregate"]["paths"]), 2)
        self.assertEqual(batch["aggregate"]["source_label"], "simulation_result")

        comparison = self.client.get(
            f"/api/scenarios/{scenario_id}/comparison?batch_id={batch['id']}"
        )
        self.assertEqual(comparison.status_code, 200)
        comparison_data = comparison.get_json()
        self.assertEqual(comparison_data["meta"]["rules_version"], "career-rules-v0.1")
        self.assertIn("career_capital", comparison_data["data"]["paths"][0]["dimensions"])

        world_id = self._first_world_id(scenario_id, batch["id"])
        timeline = self.client.get(f"/api/world-runs/{world_id}/timeline")
        self.assertEqual(timeline.status_code, 200)
        self.assertEqual(len(timeline.get_json()["data"]["events"]), 2)

    def test_repeated_run_has_reproducible_aggregate(self) -> None:
        scenario_id = self.create_scenario()
        first = self.client.post(f"/api/scenarios/{scenario_id}/runs", json={}).get_json()["data"]
        second = self.client.post(f"/api/scenarios/{scenario_id}/runs", json={}).get_json()["data"]
        self.assertEqual(first["aggregate"], second["aggregate"])

    def test_equivalent_scenarios_have_the_same_distributions(self) -> None:
        first_scenario = self.create_scenario()
        second_scenario = self.create_scenario()
        first = self.client.post(f"/api/scenarios/{first_scenario}/runs", json={}).get_json()["data"]
        second = self.client.post(f"/api/scenarios/{second_scenario}/runs", json={}).get_json()["data"]
        first_dimensions = [path["dimensions"] for path in first["aggregate"]["paths"]]
        second_dimensions = [path["dimensions"] for path in second["aggregate"]["paths"]]
        self.assertEqual(first_dimensions, second_dimensions)

    def test_real_offer_uses_user_fact_provenance(self) -> None:
        case_id = self.create_confirmed_case()
        offer = self.client.post(
            f"/api/cases/{case_id}/paths",
            json={
                "type": "offer",
                "title": "Signed backend offer",
                "confidence": "real",
                "details": {"city": "Shanghai"},
            },
        )
        self.assertEqual(offer.status_code, 201)
        self.assertEqual(offer.get_json()["data"]["source_label"], "user_fact")

    def test_rejects_invalid_or_unconfirmed_input(self) -> None:
        invalid = self.client.post("/api/cases", json={"name": "Lin", "baseline": {}})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json()["error"]["code"], "validation_error")

        created = self.client.post("/api/cases", json={"name": "Lin", "baseline": baseline()})
        case_id = created.get_json()["data"]["id"]
        path = self.client.post(
            f"/api/cases/{case_id}/paths",
            json={"type": "offer", "title": "Offer"},
        )
        self.assertEqual(path.status_code, 409)
        self.assertEqual(path.get_json()["error"]["code"], "invalid_state")

    def _first_world_id(self, scenario_id: str, batch_id: str) -> str:
        repository = self.client.application.extensions["career_repository"]
        world_files = list(
            repository.scenarios_dir.glob(f"{scenario_id}/batches/{batch_id}/worlds/*/world.json")
        )
        self.assertTrue(world_files)
        return world_files[0].parent.name


if __name__ == "__main__":
    unittest.main()
