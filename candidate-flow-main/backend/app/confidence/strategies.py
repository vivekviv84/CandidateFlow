"""Confidence scoring strategies.

Strategies consume confidence factors only. They do not know about adapters,
extractors, validators, normalizers, the merge engine, or any pipeline-specific
objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging

from app.confidence.models import ConfidenceBreakdown, ConfidenceFactor, ConfidenceResult

logger = logging.getLogger(__name__)


class ConfidenceStrategy(ABC):
    """Interface for confidence scoring strategies."""

    @abstractmethod
    def score(self, target: str, factors: list[ConfidenceFactor]) -> ConfidenceResult:
        """Return a confidence result for a target from confidence factors only."""


class WeightedConfidenceStrategy(ConfidenceStrategy):
    """Score confidence using the agreed weighted factor formula."""

    REQUIRED_WEIGHTS: dict[str, float] = {
        "source_reliability": 0.4,
        "cross_source_agreement": 0.3,
        "validation": 0.2,
        "extraction_confidence": 0.1,
    }

    def score(self, target: str, factors: list[ConfidenceFactor]) -> ConfidenceResult:
        """Return a weighted confidence result.

        Factors are matched by name. Missing required factors contribute zero and
        are reported as warnings rather than raising.
        """

        logger.info("Scoring confidence for %s with weighted strategy", target)
        factors_by_name = {factor.name: factor for factor in factors}
        warnings: list[str] = []
        score = 0.0

        for factor_name, expected_weight in self.REQUIRED_WEIGHTS.items():
            factor = factors_by_name.get(factor_name)
            if factor is None:
                warnings.append(f"Missing confidence factor: {factor_name}")
                continue
            if factor.weight != expected_weight:
                warnings.append(
                    f"Factor '{factor_name}' provided weight {factor.weight}; expected {expected_weight}."
                )
            score += factor.score * expected_weight

        unused_factors = sorted(set(factors_by_name) - set(self.REQUIRED_WEIGHTS))
        for factor_name in unused_factors:
            warnings.append(f"Unused confidence factor: {factor_name}")

        return ConfidenceResult(
            target=target,
            score=round(score, 4),
            breakdown=ConfidenceBreakdown(
                factors=factors,
                notes=[
                    "Weighted formula: 40% source reliability, 30% cross-source agreement, "
                    "20% validation, 10% extraction confidence."
                ],
            ),
            method="weighted_confidence_v1",
            warnings=warnings,
        )
