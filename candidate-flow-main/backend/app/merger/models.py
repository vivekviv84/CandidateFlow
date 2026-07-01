"""Merge engine models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import Candidate, SourceType


class MergeCandidateValue(BaseModel):
    """One value offered by one source fragment for merge consideration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str
    value: Any
    source: SourceType
    source_priority: int
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class MergeDecision(BaseModel):
    """Explain one deterministic merge choice."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str
    selected_value: Any
    selected_source: SourceType
    candidate_values: list[MergeCandidateValue]
    discarded_values: list[MergeCandidateValue] = Field(default_factory=list)
    resolver: str
    strategy: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    support_count: int | None = None
    consensus_score: float | None = None
    supporting_sources: list[str] | None = None
    aggregate_confidence: float | None = None


class FieldResolution(BaseModel):
    """Resolved value and decisions for a canonical candidate field."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: str
    value: Any
    decisions: list[MergeDecision] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MergeReport(BaseModel):
    """Detailed report for a complete merge run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decisions: list[MergeDecision] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fragments_seen: int = 0
    fields_resolved: list[str] = Field(default_factory=list)


class MergeResult(BaseModel):
    """Top-level merge output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: Candidate
    report: MergeReport

