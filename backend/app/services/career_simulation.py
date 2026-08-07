"""
services/ 目录：业务服务层。
本文件实现确定性的本地仿真运行器，在引入 Mesa/SimPy 适配器前使用，
负责批量运行与聚合结果。
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from statistics import median
from typing import Any
from uuid import uuid4

from ..errors import APIError
from ..models.career import HORIZON_YEARS, RUN_MODES
from .career_repository import CareerRepository


METRIC_BASELINES = {
    "graduate_school": {
        "career_capital": 58,
        "skill_growth": 64,
        "financial_resilience": 42,
        "employment_stability": 53,
        "life_quality": 51,
        "goal_proximity": 60,
    },
    "offer": {
        "career_capital": 54,
        "skill_growth": 57,
        "financial_resilience": 64,
        "employment_stability": 56,
        "life_quality": 54,
        "goal_proximity": 55,
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


class CareerSimulationService:
    """在引入 Mesa/SimPy 适配器之前使用的确定性本地运行器。"""

    def __init__(self, repository: CareerRepository):
        self.repository = repository

    def run_batch(self, scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        scenario = self.repository.get_scenario(scenario_id)
        run_mode = payload.get("run_mode", "quick")
        horizon_years = payload.get("horizon_years", 1)
        if run_mode not in RUN_MODES:
            raise APIError("validation_error", "run_mode must be quick, standard, or deep.", 400)
        if horizon_years not in HORIZON_YEARS:
            raise APIError("validation_error", "horizon_years must be 1, 3, or 5.", 400)

        batch_id = f"batch_{uuid4().hex[:12]}"
        world_count = RUN_MODES[run_mode]
        worlds: list[dict[str, Any]] = []
        for path in scenario["paths"]:
            for seed in range(1, world_count + 1):
                world = self._run_world(scenario, path, seed, horizon_years, batch_id)
                self.repository.save_world(scenario_id, batch_id, world)
                worlds.append(world)

        aggregate = self._aggregate(scenario, worlds)
        batch = {
            "id": batch_id,
            "scenario_id": scenario_id,
            "status": "completed",
            "run_mode": run_mode,
            "horizon_years": horizon_years,
            "completed_worlds": len(worlds),
            "total_worlds": len(worlds),
            "failed_seeds": [],
            "rules_version": scenario["rules_version"],
            "data_version": "local-v1",
            "created_at": _now(),
            "aggregate": aggregate,
        }
        self.repository.save_batch(scenario_id, batch)
        return batch

    def _run_world(
        self,
        scenario: dict[str, Any],
        path: dict[str, Any],
        seed: int,
        horizon_years: int,
        batch_id: str,
    ) -> dict[str, Any]:
        rng = random.Random(f"{scenario['input_fingerprint']}:{path['title']}:{seed}:{horizon_years}")
        baseline = METRIC_BASELINES[path["type"]]
        horizon_adjustment = (horizon_years - 1) * 2
        metrics = {
            name: {
                "value": max(0, min(100, round(value + horizon_adjustment + rng.randint(-12, 12), 2))),
                "source_label": "simulation_result",
            }
            for name, value in baseline.items()
        }
        world_id = f"world_{uuid4().hex[:12]}"
        months = horizon_years * 12
        events = [
            {
                "id": f"event_{world_id}_start",
                "time_month": 1,
                "kind": "path_started",
                "message": f"Simulated {path['type']} path started.",
                "source_label": "simulation_result",
                "rules_version": scenario["rules_version"],
            },
            {
                "id": f"event_{world_id}_checkpoint",
                "time_month": months,
                "kind": "horizon_checkpoint",
                "message": "Simulated horizon reached.",
                "source_label": "simulation_result",
                "rules_version": scenario["rules_version"],
            },
        ]
        return {
            "id": world_id,
            "batch_id": batch_id,
            "scenario_id": scenario["id"],
            "path_id": path["id"],
            "seed": seed,
            "horizon_years": horizon_years,
            "status": "completed",
            "metrics": metrics,
            "events": events,
            "snapshots": [
                {"time_month": 0, "state": "initialized"},
                {"time_month": months, "state": "completed", "metrics": metrics},
            ],
            "created_at": _now(),
        }

    @staticmethod
    def _aggregate(scenario: dict[str, Any], worlds: list[dict[str, Any]]) -> dict[str, Any]:
        result_paths = []
        for path in scenario["paths"]:
            path_worlds = [world for world in worlds if world["path_id"] == path["id"]]
            dimensions = {}
            for dimension in METRIC_BASELINES[path["type"]]:
                values = [world["metrics"][dimension]["value"] for world in path_worlds]
                dimensions[dimension] = {
                    "median": median(values),
                    "p10": _percentile(values, 0.10),
                    "p90": _percentile(values, 0.90),
                    "source_label": "simulation_result",
                }
            result_paths.append(
                {
                    "path_id": path["id"],
                    "title": path["title"],
                    "type": path["type"],
                    "confidence": path["confidence"],
                    "world_count": len(path_worlds),
                    "dimensions": dimensions,
                }
            )
        return {
            "source_label": "simulation_result",
            "disclaimer": "Simulated distributions are not admissions or career outcome promises.",
            "paths": result_paths,
        }
