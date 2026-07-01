"""Shared normalization result contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NormalizationMetadata(BaseModel):
    """Explain how one source value was normalized."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    normalizer: str
    method: str
    steps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class NormalizedValue(BaseModel):
    """One normalized value and its source-preserving metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    original_value: Any
    normalized_value: Any
    is_normalized: bool
    metadata: NormalizationMetadata


class NormalizationResult(BaseModel):
    """Structured output for normalized extracted values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: str
    values: list[NormalizedValue] = Field(default_factory=list)

