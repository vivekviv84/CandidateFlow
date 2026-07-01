"""Runtime configuration models for output projection behavior."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MissingFieldStrategy(StrEnum):
    """Supported strategies for fields missing from a projected candidate."""

    NULL = "null"
    OMIT = "omit"
    ERROR = "error"


class RuntimeConfig(BaseModel):
    """User-editable runtime config consumed by later pipeline stages.

    The model intentionally stores mappings and field selections as data, so
    future projection and normalization changes can be made without code edits.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    output_fields: list[str] | None = None
    rename_fields: dict[str, str] = Field(default_factory=dict)
    field_mappings: dict[str, str] = Field(default_factory=dict)
    include_confidence: bool = True
    include_provenance: bool = True
    missing_field_strategy: MissingFieldStrategy = MissingFieldStrategy.NULL

    @field_validator("output_fields")
    @classmethod
    def reject_empty_field_names(cls, value: list[str] | None) -> list[str] | None:
        """Ensure configured output fields are meaningful and deterministic."""

        if value is None:
            return value

        cleaned = [field.strip() for field in value if field and field.strip()]
        if len(cleaned) != len(value):
            raise ValueError("output_fields cannot contain blank field names")
        return cleaned

