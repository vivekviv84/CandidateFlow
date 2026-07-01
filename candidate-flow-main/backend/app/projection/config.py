"""Projection layer configuration models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.config import RuntimeConfig


class MissingFieldStrategy(StrEnum):
    """Strategies for handling missing fields during projection."""

    NULL = "null"
    OMIT = "omit"
    ERROR = "error"


class ProjectionConfig(BaseModel):
    """Runtime projection configuration.

    Attributes:
        selected_fields: Source paths to include when no explicit field mappings are provided.
        rename_fields: Mapping of source paths to output paths.
        field_mappings: Explicit mapping of output paths to source paths.
        include_confidence: Whether confidence fields should be emitted.
        include_provenance: Whether provenance records should be emitted.
        on_missing: Strategy for missing source paths.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    selected_fields: list[str] | None = None
    rename_fields: dict[str, str] = Field(default_factory=dict)
    field_mappings: dict[str, str] = Field(default_factory=dict)
    include_confidence: bool = True
    include_provenance: bool = True
    on_missing: MissingFieldStrategy = MissingFieldStrategy.NULL

    @field_validator("selected_fields")
    @classmethod
    def reject_blank_selected_fields(cls, value: list[str] | None) -> list[str] | None:
        """Reject blank selected field paths."""

        if value is None:
            return value
        cleaned = [field.strip() for field in value if field and field.strip()]
        if len(cleaned) != len(value):
            raise ValueError("selected_fields cannot contain blank paths")
        return cleaned

    @classmethod
    def from_runtime_config(cls, config: RuntimeConfig) -> "ProjectionConfig":
        """Build a projection config from the earlier runtime config model."""

        return cls(
            selected_fields=config.output_fields,
            rename_fields=config.rename_fields,
            field_mappings=config.field_mappings,
            include_confidence=config.include_confidence,
            include_provenance=config.include_provenance,
            on_missing=MissingFieldStrategy(config.missing_field_strategy.value),
        )


class ProjectionError(ValueError):
    """Raised when projection cannot satisfy an error-on-missing request."""
