"""API request and response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


PROCESSING_SUMMARY_EXAMPLE: dict[str, Any] = {
    "sources_processed": 2,
    "fields_extracted": 8,
    "fields_normalized": 5,
    "duplicates_removed": 2,
    "conflicts_resolved": 1,
    "overall_confidence": 0.82,
    "processing_time_ms": 18.42,
    "logs": [
        "Pipeline started",
        "Loaded 2 source fragment(s)",
        "Extracted 8 field value(s)",
        "Normalized 5 value(s)",
        "Merged candidate profile",
        "Built provenance records",
        "Calculated confidence report",
        "Applied projection",
        "Output generated",
    ],
}

TRANSFORM_RESPONSE_EXAMPLE: dict[str, Any] = {
    "candidate": {
        "candidate_id": "cand-001",
        "full_name": "Ada Lovelace",
        "emails": ["ada@example.com"],
        "skills": [{"name": "Python", "canonical_name": "python"}],
        "overall_confidence": 0.82,
    },
    "confidence": {
        "overall_score": 0.82,
        "results": [
            {
                "target": "overall",
                "score": 0.82,
                "method": "weighted_average",
                "warnings": [],
                "breakdown": {
                    "factors": [
                        {
                            "name": "source_reliability",
                            "score": 0.85,
                            "weight": 0.4,
                            "reason": "Sources were processed successfully.",
                        }
                    ],
                    "notes": [],
                },
            }
        ],
    },
    "merge_report": {
        "decisions": [
            {
                "field": "full_name",
                "selected_value": "Ada Lovelace",
                "selected_source": "ats_json",
                "strategy": "highest_confidence_then_source_priority_then_timestamp_then_stable_value",
                "confidence": 0.95,
                "discarded_values": [{"value": "A. Lovelace", "source": "recruiter_csv"}],
            }
        ],
        "warnings": [],
    },
    "provenance": [{"pipeline_stage": "merge", "field": "full_name", "source": "ats_json"}],
    "processing_summary": PROCESSING_SUMMARY_EXAMPLE,
}


class ProjectInfo(BaseModel):
    """Project metadata returned by the root endpoint."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "name": "Candidate Flow",
                "description": "Explainable multi-source candidate data transformation engine.",
                "version": "0.1.0",
            }
        },
    )

    name: str = Field(description="Human-readable project name.")
    description: str = Field(description="Short product description.")
    version: str = Field(description="Current API version.")


class HealthResponse(BaseModel):
    """Health endpoint response."""

    model_config = ConfigDict(extra="forbid", frozen=True, json_schema_extra={"example": {"status": "ok"}})

    status: str = Field(default="ok", description="Service health status.")


class VersionResponse(BaseModel):
    """Version endpoint response."""

    model_config = ConfigDict(extra="forbid", frozen=True, json_schema_extra={"example": {"version": "0.1.0"}})

    version: str = Field(description="Current API version.")


class ProcessingSummary(BaseModel):
    """High-level processing summary for UI and CLI output."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                **PROCESSING_SUMMARY_EXAMPLE,
            },
        },
    )

    sources_processed: int = Field(description="Number of source fragments loaded from uploaded files.", ge=0)
    fields_extracted: int = Field(description="Number of field values emitted by extractors.", ge=0)
    fields_normalized: int = Field(description="Number of values normalized before merge.", ge=0)
    duplicates_removed: int = Field(description="Number of discarded duplicate or lower-priority values.", ge=0)
    conflicts_resolved: int = Field(description="Number of fields where at least one value was rejected.", ge=0)
    overall_confidence: float = Field(description="Overall confidence score for the output candidate.", ge=0.0, le=1.0)
    processing_time_ms: float = Field(description="End-to-end processing time in milliseconds.", ge=0.0)
    logs: list[str] = Field(default_factory=list, description="Ordered user-facing pipeline stages.")


class TransformResponse(BaseModel):
    """Full transformation response."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": TRANSFORM_RESPONSE_EXAMPLE
        },
    )

    candidate: dict[str, Any] = Field(description="Projected canonical candidate payload.")
    confidence: dict[str, Any] = Field(description="Confidence report for the transformed candidate.")
    merge_report: dict[str, Any] = Field(description="Merge decisions, discarded values, and warnings.")
    provenance: list[dict[str, Any]] = Field(description="Field-level provenance records.")
    processing_summary: ProcessingSummary = Field(description="High-level processing metrics and timeline.")


class ExplainRequest(BaseModel):
    """Explain request for one candidate field."""

    model_config = ConfigDict(extra="forbid", frozen=True, json_schema_extra={"example": {"field": "full_name"}})

    field: str = Field(description="Candidate field to explain.", examples=["full_name"])


class ExplainResponse(BaseModel):
    """Explanation for one selected field."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "field": "full_name",
                "selected_value": "Ada Lovelace",
                "rejected_values": ["A. Lovelace"],
                "source": "ats_json",
                "rule": "highest_confidence_then_source_priority_then_timestamp_then_stable_value",
                "confidence": 0.95,
                "pipeline_history": [{"pipeline_stage": "merge", "field": "full_name"}],
            }
        },
    )

    field: str = Field(description="Requested field name.")
    selected_value: Any | None = Field(default=None, description="Value selected by the merge report.")
    rejected_values: list[Any] = Field(default_factory=list, description="Values rejected for the selected field.")
    source: str | None = Field(default=None, description="Source that supplied the selected value.")
    rule: str | None = Field(default=None, description="Merge rule used for the decision.")
    confidence: float | None = Field(default=None, description="Confidence attached to the merge decision.", ge=0.0, le=1.0)
    pipeline_history: list[dict[str, Any]] = Field(default_factory=list, description="Provenance records for the decision.")
    support_count: int | None = Field(default=None, description="Number of supporting sources.")
    consensus_score: float | None = Field(default=None, description="Consensus score.")
    supporting_sources: list[str] | None = Field(default=None, description="Supporting sources names.")
    aggregate_confidence: float | None = Field(default=None, description="Aggregated confidence across supporting sources.")
