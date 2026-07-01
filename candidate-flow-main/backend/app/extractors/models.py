"""Shared result contracts for deterministic extractors."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import SourceType


class ExtractionMetadata(BaseModel):
    """Explain how an extractor found its values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    extractor: str
    source: SourceType
    method: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Structured output for one extracted canonical field."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: str
    values: list[Any] = Field(default_factory=list)
    metadata: ExtractionMetadata

