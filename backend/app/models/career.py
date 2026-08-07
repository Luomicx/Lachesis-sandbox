"""
models/ 目录：领域模型层。
本文件定义职业案例的 baseline、路径等验证规则与共享常量，
供 API 与 service 层复用。
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..errors import APIError


REQUIRED_BASELINE_FIELDS = (
    "school",
    "major",
    "graduation_year",
    "gpa_or_rank",
    "skills",
    "target_city",
    "budget",
    "family_support",
    "constraints",
    "long_term_goal",
)
PATH_TYPES = {"graduate_school", "offer"}
OFFER_CONFIDENCE = {"real", "hypothetical"}
RUN_MODES = {"quick": 10, "standard": 20, "deep": 50}
HORIZON_YEARS = {1, 3, 5}


def require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise APIError("validation_error", f"{field_name} must be an object.", 400)
    return dict(value)


def validate_baseline(value: Any) -> dict[str, Any]:
    baseline = require_object(value, "baseline")
    missing = [field for field in REQUIRED_BASELINE_FIELDS if field not in baseline]
    if missing:
        raise APIError(
            "validation_error",
            "baseline is missing required fields.",
            400,
            {"missing_fields": missing},
        )

    for field in REQUIRED_BASELINE_FIELDS:
        if field == "budget":
            continue
        if field == "skills":
            if not isinstance(baseline[field], list) or not baseline[field]:
                raise APIError("validation_error", "baseline.skills must be a non-empty list.", 400)
            continue
        if not str(baseline[field]).strip():
            raise APIError("validation_error", f"baseline.{field} must not be empty.", 400)

    if not isinstance(baseline["budget"], (int, float)) or baseline["budget"] < 0:
        raise APIError("validation_error", "baseline.budget must be a non-negative number.", 400)
    return baseline


def validate_baseline_update(value: Any) -> dict[str, Any]:
    baseline_update = require_object(value, "baseline")
    unsupported_fields = sorted(set(baseline_update) - set(REQUIRED_BASELINE_FIELDS))
    if unsupported_fields:
        raise APIError(
            "validation_error",
            "baseline contains unsupported fields.",
            400,
            {"unsupported_fields": unsupported_fields},
        )
    return baseline_update


def validate_path(value: Any) -> dict[str, Any]:
    payload = require_object(value, "path")
    path_type = payload.get("type")
    if path_type not in PATH_TYPES:
        raise APIError(
            "validation_error",
            "path.type must be graduate_school or offer.",
            400,
        )
    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        raise APIError("validation_error", "path.title is required.", 400)

    details = payload.get("details", {})
    if not isinstance(details, Mapping):
        raise APIError("validation_error", "path.details must be an object.", 400)

    normalized = {"type": path_type, "title": title.strip(), "details": dict(details)}
    if path_type == "offer":
        confidence = payload.get("confidence", "hypothetical")
        if confidence not in OFFER_CONFIDENCE:
            raise APIError("validation_error", "offer confidence must be real or hypothetical.", 400)
        normalized["confidence"] = confidence
    else:
        normalized["confidence"] = "model_assumption"
    return normalized
