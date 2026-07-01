"""Projection layer for canonical candidates."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from app.models import Candidate
from app.projection.config import MissingFieldStrategy, ProjectionConfig, ProjectionError
from app.projection.field_mapper import MISSING, FieldMapper

logger = logging.getLogger(__name__)


class Projector:
    """Project a canonical candidate into configured JSON-compatible output."""

    def __init__(self, field_mapper: FieldMapper | None = None) -> None:
        """Create a projector with an injectable field mapper."""

        self.field_mapper = field_mapper or FieldMapper()

    def project(self, candidate: Candidate, config: ProjectionConfig | None = None) -> dict[str, Any]:
        """Project a canonical candidate using runtime projection config."""

        projection_config = config or ProjectionConfig()
        logger.info("Projecting candidate %s", candidate.candidate_id)
        source = self._candidate_data(candidate)
        source = self._apply_visibility(source, projection_config)

        if projection_config.field_mappings:
            return self._project_mapped_fields(source, projection_config)
        return self._project_selected_fields(source, projection_config)

    def _project_mapped_fields(self, source: dict[str, Any], config: ProjectionConfig) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for output_path, source_path in config.field_mappings.items():
            self._copy_path(source, output, source_path, output_path, config.on_missing)
        return output

    def _project_selected_fields(self, source: dict[str, Any], config: ProjectionConfig) -> dict[str, Any]:
        output: dict[str, Any] = {}
        selected_fields = config.selected_fields or list(source.keys())
        for source_path in selected_fields:
            output_path = config.rename_fields.get(source_path, source_path)
            self._copy_path(source, output, source_path, output_path, config.on_missing)
        return output

    def _copy_path(
        self,
        source: dict[str, Any],
        output: dict[str, Any],
        source_path: str,
        output_path: str,
        on_missing: MissingFieldStrategy,
    ) -> None:
        value = self.field_mapper.get_path(source, source_path)
        if value is MISSING:
            if on_missing == MissingFieldStrategy.ERROR:
                raise ProjectionError(f"Missing projection field: {source_path}")
            if on_missing == MissingFieldStrategy.OMIT:
                return
            self.field_mapper.set_path(output, output_path, None)
            return
        self.field_mapper.set_path(output, output_path, value)

    def _candidate_data(self, candidate: Candidate) -> dict[str, Any]:
        data = candidate.model_dump(mode="json")
        return self._json_ready(data)

    def _apply_visibility(self, data: dict[str, Any], config: ProjectionConfig) -> dict[str, Any]:
        output = data
        if not config.include_provenance:
            output.pop("provenance", None)
        if not config.include_confidence:
            output = self._remove_confidence(output)
        return output

    def _remove_confidence(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self._remove_confidence(item)
                for key, item in value.items()
                if key not in {"confidence", "overall_confidence"}
            }
        if isinstance(value, list):
            return [self._remove_confidence(item) for item in value]
        return value

    def _json_ready(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return self._json_ready(value.model_dump(mode="json"))
        if isinstance(value, dict):
            return {str(key): self._json_ready(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_ready(item) for item in value]
        return value
