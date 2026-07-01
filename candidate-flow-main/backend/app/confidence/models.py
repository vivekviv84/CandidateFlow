"""Shared confidence engine data models.

This module intentionally contains data contracts only. Scoring algorithms,
aggregation logic, and pipeline integration belong to later modules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceFactor(BaseModel):
    """One explainable contribution to a confidence score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfidenceBreakdown(BaseModel):
    """Detailed factors used to explain a confidence result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    factors: list[ConfidenceFactor] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ConfidenceResult(BaseModel):
    """Confidence score for one field or object."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target: str
    score: float = Field(ge=0.0, le=1.0)
    breakdown: ConfidenceBreakdown
    method: str
    warnings: list[str] = Field(default_factory=list)


class ConfidenceReport(BaseModel):
    """Collection of confidence results for a scoring run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    results: list[ConfidenceResult] = Field(default_factory=list)
    overall_score: float | None = Field(default=None, ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

