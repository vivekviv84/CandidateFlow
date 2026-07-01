"""Confidence aggregation from field-level results to overall confidence."""

from __future__ import annotations

import logging
from typing import Protocol

from app.confidence.models import ConfidenceBreakdown, ConfidenceFactor, ConfidenceReport, ConfidenceResult

logger = logging.getLogger(__name__)


class AggregationStrategy(Protocol):
    """Protocol for future pluggable aggregation strategies."""

    def aggregate(self, results: list[ConfidenceResult]) -> float:
        """Aggregate field confidence results into one score."""


class WeightedAverageAggregationStrategy:
    """Aggregate field confidence using field weights from result metadata."""

    DEFAULT_WEIGHT = 1.0

    def aggregate(self, results: list[ConfidenceResult]) -> float:
        """Return weighted average of field confidence results."""

        if not results:
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0
        for result in results:
            weight = self._weight_for(result)
            weighted_sum += result.score * weight
            total_weight += weight

        if total_weight == 0.0:
            return 0.0
        return round(weighted_sum / total_weight, 4)

    def _weight_for(self, result: ConfidenceResult) -> float:
        for factor in result.breakdown.factors:
            if factor.name == "field_weight":
                return factor.weight
        return self.DEFAULT_WEIGHT


class ConfidenceAggregator:
    """Aggregate field confidence results into an explainable confidence report."""

    def __init__(self, strategy: AggregationStrategy | None = None) -> None:
        """Create an aggregator with a replaceable aggregation strategy."""

        self.strategy = strategy or WeightedAverageAggregationStrategy()

    def aggregate(self, results: list[ConfidenceResult]) -> ConfidenceReport:
        """Return an explainable report from field confidence results."""

        logger.info("Aggregating %s confidence result(s)", len(results))
        overall_score = self.strategy.aggregate(results)
        return ConfidenceReport(
            results=results,
            overall_score=overall_score,
            metadata={
                "aggregation_method": self.strategy.__class__.__name__,
                "field_count": len(results),
            },
        )

    def aggregate_field(
        self,
        target: str,
        factors: list[ConfidenceFactor],
        method: str = "precomputed_field_confidence",
    ) -> ConfidenceResult:
        """Create an explainable field confidence result from precomputed factors."""

        logger.info("Aggregating field confidence for %s", target)
        if not factors:
            return ConfidenceResult(
                target=target,
                score=0.0,
                breakdown=ConfidenceBreakdown(factors=[], notes=["No confidence factors were provided."]),
                method=method,
                warnings=["No confidence factors were provided."],
            )

        total_weight = sum(factor.weight for factor in factors)
        if total_weight == 0.0:
            return ConfidenceResult(
                target=target,
                score=0.0,
                breakdown=ConfidenceBreakdown(factors=factors, notes=["All factor weights were zero."]),
                method=method,
                warnings=["All factor weights were zero."],
            )

        score = sum(factor.score * factor.weight for factor in factors) / total_weight
        return ConfidenceResult(
            target=target,
            score=round(score, 4),
            breakdown=ConfidenceBreakdown(factors=factors),
            method=method,
        )
