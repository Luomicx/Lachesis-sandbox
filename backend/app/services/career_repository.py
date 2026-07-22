from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..errors import APIError
from ..models.career import validate_baseline, validate_path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CareerRepository:
    """Filesystem repository with case-scoped, versioned JSON artifacts."""

    def __init__(self, data_dir: str | Path):
        self.root = Path(data_dir)
        self.cases_dir = self.root / "cases"
        self.scenarios_dir = self.root / "scenarios"
        self.cases_dir.mkdir(parents=True, exist_ok=True)
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
        ) as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            temp_name = handle.name
        os.replace(temp_name, path)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise APIError("not_found", "Resource not found.", 404) from error
        except json.JSONDecodeError as error:
            raise APIError("storage_error", "Stored resource is invalid.", 500) from error

    def _case_path(self, case_id: str) -> Path:
        return self.cases_dir / case_id / "case.json"

    def create_case(self, name: Any, baseline: Any) -> dict[str, Any]:
        if not isinstance(name, str) or not name.strip():
            raise APIError("validation_error", "name is required.", 400)
        case_id = f"case_{uuid4().hex[:12]}"
        now = utc_now()
        case = {
            "id": case_id,
            "name": name.strip(),
            "status": "intake",
            "baseline": validate_baseline(baseline),
            "baseline_version": 1,
            "created_at": now,
            "updated_at": now,
        }
        self._write_json(self._case_path(case_id), case)
        return case

    def get_case(self, case_id: str) -> dict[str, Any]:
        return self._read_json(self._case_path(case_id))

    def confirm_case(self, case_id: str) -> dict[str, Any]:
        case = self.get_case(case_id)
        if case["status"] == "confirmed":
            return case
        if case["status"] != "intake":
            raise APIError("invalid_state", "Only an intake case can be confirmed.", 409)
        case["status"] = "confirmed"
        case["updated_at"] = utc_now()
        self._write_json(self._case_path(case_id), case)
        return case

    def _path_path(self, case_id: str, path_id: str) -> Path:
        return self.cases_dir / case_id / "paths" / f"{path_id}.json"

    def list_paths(self, case_id: str) -> list[dict[str, Any]]:
        self.get_case(case_id)
        directory = self.cases_dir / case_id / "paths"
        if not directory.exists():
            return []
        return [self._read_json(path) for path in sorted(directory.glob("*.json"))]

    def create_path(self, case_id: str, payload: Any) -> dict[str, Any]:
        case = self.get_case(case_id)
        if case["status"] != "confirmed":
            raise APIError("invalid_state", "Confirm the case before creating paths.", 409)
        existing = self.list_paths(case_id)
        if len(existing) >= 4:
            raise APIError("validation_error", "A case can contain at most four paths.", 400)
        path = validate_path(payload)
        path_id = f"path_{uuid4().hex[:12]}"
        source_label = "model_assumption"
        if path["type"] == "offer" and path["confidence"] == "real":
            source_label = "user_fact"
        path.update(
            {
                "id": path_id,
                "case_id": case_id,
                "created_at": utc_now(),
                "source_label": source_label,
            }
        )
        self._write_json(self._path_path(case_id, path_id), path)
        return path

    def _scenario_path(self, scenario_id: str) -> Path:
        return self.scenarios_dir / scenario_id / "scenario.json"

    def create_scenario(self, case_id: Any, path_ids: Any) -> dict[str, Any]:
        if not isinstance(case_id, str):
            raise APIError("validation_error", "case_id is required.", 400)
        case = self.get_case(case_id)
        if case["status"] != "confirmed":
            raise APIError("invalid_state", "Confirm the case before creating a scenario.", 409)
        if not isinstance(path_ids, list) or not path_ids or len(path_ids) > 4:
            raise APIError("validation_error", "path_ids must contain one to four path IDs.", 400)
        paths_by_id = {path["id"]: path for path in self.list_paths(case_id)}
        if len(set(path_ids)) != len(path_ids) or any(path_id not in paths_by_id for path_id in path_ids):
            raise APIError("validation_error", "path_ids must reference distinct paths in the case.", 400)

        selected_paths = [paths_by_id[path_id] for path_id in path_ids]
        canonical_paths = [
            {
                "type": path["type"],
                "title": path["title"],
                "details": path["details"],
                "confidence": path["confidence"],
                "source_label": path["source_label"],
            }
            for path in selected_paths
        ]
        canonical_input = {
            "baseline": case["baseline"],
            "paths": canonical_paths,
            "rules_version": "career-rules-v0.1",
        }
        fingerprint = sha256(
            json.dumps(canonical_input, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        scenario_id = f"scenario_{uuid4().hex[:12]}"
        scenario = {
            "id": scenario_id,
            "case_id": case_id,
            "case_baseline_version": case["baseline_version"],
            "paths": selected_paths,
            "rules_version": "career-rules-v0.1",
            "input_fingerprint": fingerprint,
            "created_at": utc_now(),
        }
        self._write_json(self._scenario_path(scenario_id), scenario)
        self._write_json(self.scenarios_dir / scenario_id / "input_snapshot.json", scenario)
        return scenario

    def get_scenario(self, scenario_id: str) -> dict[str, Any]:
        return self._read_json(self._scenario_path(scenario_id))

    def save_batch(self, scenario_id: str, batch: dict[str, Any]) -> None:
        self._write_json(self.scenarios_dir / scenario_id / "batches" / batch["id"] / "batch.json", batch)

    def save_world(self, scenario_id: str, batch_id: str, world: dict[str, Any]) -> None:
        world_dir = self.scenarios_dir / scenario_id / "batches" / batch_id / "worlds" / world["id"]
        self._write_json(world_dir / "world.json", world)
        self._write_json(world_dir / "metrics.json", world["metrics"])
        self._write_json(world_dir / "snapshots.json", {"snapshots": world["snapshots"]})
        events_path = world_dir / "events.jsonl"
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text(
            "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in world["events"]),
            encoding="utf-8",
        )
        self._write_json(world_dir / "role_contexts.json", {"role_contexts": []})

    def get_batch(self, scenario_id: str, batch_id: str) -> dict[str, Any]:
        return self._read_json(self.scenarios_dir / scenario_id / "batches" / batch_id / "batch.json")

    def get_world(self, world_id: str) -> dict[str, Any]:
        for world_path in self.scenarios_dir.glob(f"*/batches/*/worlds/{world_id}/world.json"):
            return self._read_json(world_path)
        raise APIError("not_found", "World run not found.", 404)
