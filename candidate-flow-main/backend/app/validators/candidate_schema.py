"""Candidate schema validation."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from pydantic import BaseModel

from app.validators.models import Severity, ValidationResult

logger = logging.getLogger(__name__)


class CandidateSchemaValidator:
    """Validate candidate-like dictionaries without constructing or mutating them."""

    REQUIRED_FIELDS = {"candidate_id"}
    FIELD_TYPES: dict[str, tuple[type[Any], ...]] = {
        "candidate_id": (str,),
        "full_name": (str, type(None)),
        "emails": (list,),
        "phones": (list,),
        "location": (str, type(None)),
        "links": (dict,),
        "headline": (str, type(None)),
        "years_experience": (int, float, type(None)),
        "skills": (list,),
        "experience": (list,),
        "education": (list,),
        "provenance": (list,),
        "overall_confidence": (int, float),
        "validation_errors": (list,),
    }

    def validate(self, candidate: Mapping[str, Any] | BaseModel, field: str = "candidate") -> list[ValidationResult]:
        """Validate schema shape and collect all discovered issues."""

        logger.info("Validating candidate schema")
        data = candidate.model_dump(mode="python") if isinstance(candidate, BaseModel) else candidate
        if not isinstance(data, Mapping):
            return [
                ValidationResult(
                    is_valid=False,
                    severity=Severity.ERROR,
                    message="Candidate must be a mapping or Pydantic model.",
                    field=field,
                    suggested_action="Discard this candidate object or convert it to a dictionary.",
                )
            ]

        results: list[ValidationResult] = []
        results.extend(self._required_field_results(data, field))
        results.extend(self._type_results(data, field))
        results.extend(self._collection_item_results(data, field))
        results.extend(self._confidence_results(data, field))

        if not results:
            return [
                ValidationResult(
                    is_valid=True,
                    severity=Severity.INFO,
                    message="Candidate schema is valid.",
                    field=field,
                    suggested_action="No action required.",
                )
            ]
        return results

    def _required_field_results(self, data: Mapping[str, Any], field: str) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for required_field in sorted(self.REQUIRED_FIELDS):
            if required_field not in data or data.get(required_field) in ("", None):
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=Severity.ERROR,
                        message=f"Required field '{required_field}' is missing or blank.",
                        field=f"{field}.{required_field}",
                        suggested_action="Keep partial output but flag the candidate for identity review.",
                    )
                )
        return results

    def _type_results(self, data: Mapping[str, Any], field: str) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for key, expected_types in self.FIELD_TYPES.items():
            if key not in data:
                continue
            if not isinstance(data[key], expected_types):
                expected = ", ".join(type_.__name__ for type_ in expected_types)
                results.append(
                    ValidationResult(
                        is_valid=False,
                        severity=Severity.ERROR,
                        message=f"Field '{key}' has invalid type; expected {expected}.",
                        field=f"{field}.{key}",
                        suggested_action="Send this candidate through projection or schema repair before output.",
                    )
                )
        return results

    def _collection_item_results(self, data: Mapping[str, Any], field: str) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for list_field in ("emails", "phones", "skills", "experience", "education", "provenance", "validation_errors"):
            value = data.get(list_field)
            if not isinstance(value, list):
                continue
            for index, item in enumerate(value):
                if list_field in {"emails", "phones", "validation_errors"} and not isinstance(item, str):
                    results.append(self._item_type_result(field, list_field, index, "string"))
                if list_field in {"skills", "experience", "education", "provenance"} and not isinstance(item, dict):
                    results.append(self._item_type_result(field, list_field, index, "object"))

        links = data.get("links")
        if isinstance(links, dict):
            for platform, url in links.items():
                if not isinstance(platform, str):
                    results.append(self._map_type_result(field, "links", "keys", "string"))
                if not isinstance(url, str):
                    results.append(self._map_type_result(field, "links", str(platform), "string URL value"))
        return results

    @staticmethod
    def _confidence_results(data: Mapping[str, Any], field: str) -> list[ValidationResult]:
        confidence = data.get("overall_confidence")
        if confidence is None:
            return []
        if isinstance(confidence, bool):
            return [
                ValidationResult(
                    is_valid=False,
                    severity=Severity.ERROR,
                    message="overall_confidence must be a numeric value, not a boolean.",
                    field=f"{field}.overall_confidence",
                    suggested_action="Recalculate confidence before projection.",
                )
            ]
        if isinstance(confidence, int | float) and 0.0 <= float(confidence) <= 1.0:
            return []
        return [
            ValidationResult(
                is_valid=False,
                severity=Severity.ERROR,
                message="overall_confidence must be between 0.0 and 1.0.",
                field=f"{field}.overall_confidence",
                suggested_action="Recalculate confidence before projection.",
            )
        ]

    @staticmethod
    def _item_type_result(field: str, list_field: str, index: int, expected: str) -> ValidationResult:
        return ValidationResult(
            is_valid=False,
            severity=Severity.ERROR,
            message=f"{list_field} item must be a {expected}.",
            field=f"{field}.{list_field}[{index}]",
            suggested_action="Drop or repair the item before output.",
        )

    @staticmethod
    def _map_type_result(field: str, map_field: str, key: str, expected: str) -> ValidationResult:
        return ValidationResult(
            is_valid=False,
            severity=Severity.ERROR,
            message=f"{map_field} {key} must be a {expected}.",
            field=f"{field}.{map_field}.{key}",
            suggested_action="Drop or repair the map entry before output.",
        )
