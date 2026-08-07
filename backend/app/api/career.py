from __future__ import annotations

from typing import Any

from flask import current_app, jsonify, request

from ..errors import APIError
from ..services.career_repository import CareerRepository
from ..services.career_simulation import CareerSimulationService
from ..services.document_intake import DocumentIntakeService
from . import career_bp


def _repository() -> CareerRepository:
    return current_app.extensions["career_repository"]


def _document_intake() -> DocumentIntakeService:
    return current_app.extensions["document_intake"]


def _json_body() -> dict[str, Any]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise APIError("validation_error", "Request body must be a JSON object.", 400)
    return body


@career_bp.post("/cases")
def create_case():
    body = _json_body()
    case = _repository().create_case(
        body.get("name"),
        body.get("baseline"),
        baseline_provided="baseline" in body,
    )
    return jsonify({"data": case}), 201


@career_bp.get("/cases/<case_id>")
def get_case(case_id: str):
    return jsonify({"data": _repository().get_case(case_id)})


@career_bp.patch("/cases/<case_id>")
def update_case_baseline(case_id: str):
    body = _json_body()
    return jsonify({"data": _repository().update_baseline(case_id, body.get("baseline"))})


@career_bp.post("/cases/<case_id>/documents")
def upload_document(case_id: str):
    if not request.mimetype or not request.mimetype.startswith("multipart/form-data"):
        raise APIError("validation_error", "Documents must use multipart/form-data.", 400)
    if set(request.files) != {"file"} or len(request.files.getlist("file")) != 1:
        raise APIError("validation_error", "Request must contain exactly one file field.", 400)
    return jsonify({"data": _document_intake().store_document(case_id, request.files["file"])}), 201


@career_bp.get("/cases/<case_id>/documents")
def list_documents(case_id: str):
    return jsonify({"data": _document_intake().list_documents(case_id)})


@career_bp.post("/cases/<case_id>/confirm")
def confirm_case(case_id: str):
    return jsonify({"data": _repository().confirm_case(case_id)})


@career_bp.post("/cases/<case_id>/paths")
def create_path(case_id: str):
    return jsonify({"data": _repository().create_path(case_id, _json_body())}), 201


@career_bp.get("/cases/<case_id>/paths")
def list_paths(case_id: str):
    return jsonify({"data": _repository().list_paths(case_id)})


@career_bp.post("/scenarios")
def create_scenario():
    body = _json_body()
    scenario = _repository().create_scenario(body.get("case_id"), body.get("path_ids"))
    return jsonify({"data": scenario}), 201


@career_bp.post("/scenarios/<scenario_id>/runs")
def run_scenario(scenario_id: str):
    batch = CareerSimulationService(_repository()).run_batch(scenario_id, _json_body())
    return jsonify({"data": batch}), 201


@career_bp.get("/scenarios/<scenario_id>/comparison")
def get_comparison(scenario_id: str):
    batch_id = request.args.get("batch_id")
    if not batch_id:
        raise APIError("validation_error", "batch_id query parameter is required.", 400)
    batch = _repository().get_batch(scenario_id, batch_id)
    return jsonify({"data": batch["aggregate"], "meta": {
        "batch_id": batch["id"],
        "completed_worlds": batch["completed_worlds"],
        "total_worlds": batch["total_worlds"],
        "failed_seeds": batch["failed_seeds"],
        "rules_version": batch["rules_version"],
        "data_version": batch["data_version"],
    }})


@career_bp.get("/world-runs/<world_id>/timeline")
def get_timeline(world_id: str):
    world = _repository().get_world(world_id)
    return jsonify({"data": {
        "world_id": world["id"],
        "scenario_id": world["scenario_id"],
        "seed": world["seed"],
        "events": world["events"],
        "snapshots": world["snapshots"],
    }})
