"""Email normalization."""

from __future__ import annotations

import logging
from typing import Any

from app.normalizers.base import BaseNormalizer
from app.normalizers.models import NormalizationMetadata, NormalizationResult, NormalizedValue

logger = logging.getLogger(__name__)


class EmailNormalizer(BaseNormalizer):
    """Normalize email strings by trimming whitespace and lowercasing."""

    def normalize(self, values: list[Any], field_name: str = "emails") -> NormalizationResult:
        """Normalize extracted email values without dropping invalid-looking input."""

        logger.info("Normalizing %s email value(s)", len(values))
        normalized_values = [self._normalize_one(value) for value in values]
        return NormalizationResult(field_name=field_name, values=normalized_values)

    @staticmethod
    def _normalize_one(value: Any) -> NormalizedValue:
        steps: list[str] = []
        warnings: list[str] = []

        if not isinstance(value, str):
            warnings.append("Email value is not a string; preserved original value.")
            return NormalizedValue(
                original_value=value,
                normalized_value=value,
                is_normalized=False,
                metadata=NormalizationMetadata(
                    normalizer="email",
                    method="trim_and_lowercase",
                    steps=steps,
                    warnings=warnings,
                ),
            )

        normalized = value
        trimmed = normalized.strip()
        if trimmed != normalized:
            steps.append("trimmed whitespace")
            normalized = trimmed

        lowercased = normalized.lower()
        if lowercased != normalized:
            steps.append("lowercased")
            normalized = lowercased

        return NormalizedValue(
            original_value=value,
            normalized_value=normalized,
            is_normalized=normalized != value,
            metadata=NormalizationMetadata(
                normalizer="email",
                method="trim_and_lowercase",
                steps=steps,
                warnings=warnings,
            ),
        )

