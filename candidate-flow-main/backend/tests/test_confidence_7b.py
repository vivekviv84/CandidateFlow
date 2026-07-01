"""Unit tests for Module 7B confidence strategies and aggregation."""

from __future__ import annotations

from app.confidence import (
    ConfidenceAggregator,
    ConfidenceFactor,
    ConfidenceResult,
    WeightedAverageAggregationStrategy,
    WeightedConfidenceStrategy,
)
from app.confidence.models import ConfidenceBreakdown


def _agreed_factors() -> list[ConfidenceFactor]:
    return [
        ConfidenceFactor(
            name="source_reliability",
            score=1.0,
            weight=0.4,
            reason="ATS source is highly reliable.",
        ),
        ConfidenceFactor(
            name="cross_source_agreement",
            score=0.5,
            weight=0.3,
            reason="Two sources agree.",
        ),
        ConfidenceFactor(
            name="validation",
            score=0.8,
            weight=0.2,
            reason="Validation mostly passed.",
        ),
        ConfidenceFactor(
            name="extraction_confidence",
            score=0.6,
            weight=0.1,
            reason="Extractor confidence was moderate.",
        ),
    ]


def test_weighted_confidence_strategy_uses_agreed_formula() -> None:
    result = WeightedConfidenceStrategy().score("full_name", _agreed_factors())

    assert result.target == "full_name"
    assert result.score == 0.77
    assert result.method == "weighted_confidence_v1"
    assert result.warnings == []
    assert result.breakdown.factors == _agreed_factors()
    assert result.breakdown.notes == [
        "Weighted formula: 40% source reliability, 30% cross-source agreement, "
        "20% validation, 10% extraction confidence."
    ]


def test_weighted_confidence_strategy_reports_missing_and_unused_factors() -> None:
    factors = [
        ConfidenceFactor(name="source_reliability", score=1.0, weight=0.4, reason="Available."),
        ConfidenceFactor(name="extra_signal", score=1.0, weight=0.9, reason="Future signal."),
    ]

    result = WeightedConfidenceStrategy().score("emails", factors)

    assert result.score == 0.4
    assert result.warnings == [
        "Missing confidence factor: cross_source_agreement",
        "Missing confidence factor: validation",
        "Missing confidence factor: extraction_confidence",
        "Unused confidence factor: extra_signal",
    ]


def test_weighted_confidence_strategy_reports_weight_mismatch_but_uses_agreed_weight() -> None:
    factors = _agreed_factors()
    factors[0] = ConfidenceFactor(
        name="source_reliability",
        score=1.0,
        weight=0.9,
        reason="Caller supplied a wrong weight.",
    )

    result = WeightedConfidenceStrategy().score("phones", factors)

    assert result.score == 0.77
    assert result.warnings == ["Factor 'source_reliability' provided weight 0.9; expected 0.4."]


def test_confidence_aggregator_creates_field_result_from_factors() -> None:
    factors = [
        ConfidenceFactor(name="signal_a", score=1.0, weight=1.0, reason="Strong signal."),
        ConfidenceFactor(name="signal_b", score=0.5, weight=0.5, reason="Medium signal."),
    ]

    result = ConfidenceAggregator().aggregate_field("full_name", factors)

    assert result.target == "full_name"
    assert result.score == 0.8333
    assert result.breakdown.factors == factors
    assert result.method == "precomputed_field_confidence"


def test_confidence_aggregator_handles_empty_field_factors() -> None:
    result = ConfidenceAggregator().aggregate_field("headline", [])

    assert result.score == 0.0
    assert result.warnings == ["No confidence factors were provided."]
    assert result.breakdown.notes == ["No confidence factors were provided."]


def test_confidence_aggregator_handles_zero_weight_field_factors() -> None:
    result = ConfidenceAggregator().aggregate_field(
        "headline",
        [ConfidenceFactor(name="zero", score=1.0, weight=0.0, reason="No contribution.")],
    )

    assert result.score == 0.0
    assert result.warnings == ["All factor weights were zero."]


def test_confidence_aggregator_builds_explainable_report() -> None:
    results = [
        ConfidenceResult(
            target="full_name",
            score=0.9,
            breakdown=ConfidenceBreakdown(
                factors=[
                    ConfidenceFactor(
                        name="field_weight",
                        score=1.0,
                        weight=1.0,
                        reason="Name is important.",
                    )
                ]
            ),
            method="fixture",
        ),
        ConfidenceResult(
            target="emails",
            score=0.6,
            breakdown=ConfidenceBreakdown(
                factors=[
                    ConfidenceFactor(
                        name="field_weight",
                        score=1.0,
                        weight=0.5,
                        reason="Email is moderately important.",
                    )
                ]
            ),
            method="fixture",
        ),
    ]

    report = ConfidenceAggregator().aggregate(results)

    assert report.results == results
    assert report.overall_score == 0.8
    assert report.metadata == {
        "aggregation_method": "WeightedAverageAggregationStrategy",
        "field_count": 2,
    }


def test_confidence_aggregator_supports_future_strategy_replacement() -> None:
    class ConstantAggregationStrategy:
        def aggregate(self, results: list[ConfidenceResult]) -> float:
            return 0.42

    report = ConfidenceAggregator(strategy=ConstantAggregationStrategy()).aggregate([])

    assert report.overall_score == 0.42
    assert report.metadata["aggregation_method"] == "ConstantAggregationStrategy"


def test_weighted_average_aggregation_returns_zero_for_empty_results() -> None:
    assert WeightedAverageAggregationStrategy().aggregate([]) == 0.0

