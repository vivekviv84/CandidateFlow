"""Provenance models for explaining pipeline decisions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import SourceType


class ProvenanceEntry(BaseModel):
    """Explain one selected value from a pipeline stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str
    selected_value: Any
    discarded_values: list[Any] = Field(default_factory=list)
    source: SourceType
    merge_rule: str
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: str
    pipeline_stage: str = "merge"
