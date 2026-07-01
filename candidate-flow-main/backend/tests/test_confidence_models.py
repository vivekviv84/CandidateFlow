"""Unit tests for confidence engine foundation models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.confidence import (
    ConfidenceBreakdown,
    ConfidenceFactor,
    ConfidenceReport,
    ConfidenceResult,
)


def test_confidence_factor_captures_weighted_explanation() -> None:
    factor = ConfidenceFactor(
        name="source_reliability",
        score=0.95,
        weight=0.4,
        reason="ATS JSON is the highest-priority source.",
        metadata={"source": "ats_json"},
    )

    assert factor.name == "source_reliability"
    assert factor.score == 0.95
    assert factor.weight == 0.4
    assert factor.metadata == {"source": "ats_json"}


def test_confidence_models_are_frozen() -> None:
    factor = ConfidenceFactor(
        name="validation_success",
        score=1.0,
        weight=0.3,
        reason="No validation issues were reported.",
    )

    with pytest.raises(ValidationError):
        factor.score = 0.5  # type: ignore[misc]


def test_confidence_factor_bounds_score_and_weight() -> None:
    with pytest.raises(ValidationError):
        ConfidenceFactor(name="bad_score", score=1.1, weight=0.5, reason="Out of range.")

    with pytest.raises(ValidationError):
        ConfidenceFactor(name="bad_weight", score=0.5, weight=-0.1, reason="Out of range.")


def test_confidence_breakdown_contains_factors_and_notes() -> None:
    factor = ConfidenceFactor(
        name="cross_source_agreement",
        score=0.8,
        weight=0.2,
        reason="Two sources agreed on the selected value.",
    )

    breakdown = ConfidenceBreakdown(factors=[factor], notes=["Module 7A stores data only."])

    assert breakdown.factors == [factor]
    assert breakdown.notes == ["Module 7A stores data only."]


def test_confidence_result_describes_one_target() -> None:
    breakdown = ConfidenceBreakdown(
        factors=[
            ConfidenceFactor(
                name="extraction_confidence",
                score=0.75,
                weight=0.1,
                reason="Extractor reported medium confidence.",
            )
        ]
    )

    result = ConfidenceResult(
        target="full_name",
        score=0.75,
        breakdown=breakdown,
        method="not_scored_yet",
        warnings=["Scoring algorithms are not implemented in Module 7A."],
    )

    assert result.target == "full_name"
    assert result.score == 0.75
    assert result.breakdown == breakdown
    assert result.warnings == ["Scoring algorithms are not implemented in Module 7A."]


def test_confidence_result_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ConfidenceResult.model_validate(
            {
                "target": "emails",
                "score": 0.9,
                "breakdown": {"factors": []},
                "method": "not_scored_yet",
                "unexpected": "value",
            }
        )


def test_confidence_report_collects_results() -> None:
    generated_at = datetime(2026, 7, 1, tzinfo=timezone.utc)
    result = ConfidenceResult(
        target="overall",
        score=0.88,
        breakdown=ConfidenceBreakdown(factors=[]),
        method="not_scored_yet",
    )

    report = ConfidenceReport(
        results=[result],
        overall_score=0.88,
        generated_at=generated_at,
        metadata={"candidate_id": "cand-001"},
    )

    assert report.results == [result]
    assert report.overall_score == 0.88
    assert report.generated_at == generated_at
    assert report.metadata == {"candidate_id": "cand-001"}


def test_confidence_report_bounds_overall_score() -> None:
    with pytest.raises(ValidationError):
        ConfidenceReport(overall_score=1.5)

