"""Date normalization."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from dateutil import parser

from app.normalizers.base import BaseNormalizer
from app.normalizers.models import NormalizationMetadata, NormalizationResult, NormalizedValue

logger = logging.getLogger(__name__)


class DateNormalizer(BaseNormalizer):
    """Normalize source date strings to YYYY-MM where possible."""

    OPEN_ENDED_VALUES = {"present", "current", "now"}

    def normalize(self, values: list[Any], field_name: str = "dates") -> NormalizationResult:
        """Normalize date values without validating or dropping unparseable values."""

        logger.info("Normalizing %s date value(s)", len(values))
        normalized_values = [self._normalize_one(value) for value in values]
        return NormalizationResult(field_name=field_name, values=normalized_values)

    def _normalize_one(self, value: Any) -> NormalizedValue:
        steps: list[str] = []
        warnings: list[str] = []

        if value is None:
            warnings.append("Date value is null; preserved original value.")
            return self._result(value, value, False, steps, warnings)
        if not isinstance(value, str):
            warnings.append("Date value is not a string; preserved original value.")
            return self._result(value, value, False, steps, warnings)

        candidate = value
        trimmed = candidate.strip()
        if trimmed != candidate:
            steps.append("trimmed whitespace")
            candidate = trimmed

        if candidate.lower() in self.OPEN_ENDED_VALUES:
            warnings.append("Open-ended date marker preserved for later business logic.")
            return self._result(value, candidate, candidate != value, steps, warnings)

        try:
            parsed = parser.parse(candidate, default=datetime(1900, 1, 1), fuzzy=False)
        except (ValueError, OverflowError) as exc:
            warnings.append(f"Date parse failed: {exc}")
            return self._result(value, candidate, candidate != value, steps, warnings)

        normalized = f"{parsed.year:04d}-{parsed.month:02d}"
        if normalized != candidate:
            steps.append("converted to YYYY-MM")
        return self._result(value, normalized, normalized != value, steps, warnings)

    @staticmethod
    def _result(
        original_value: Any,
        normalized_value: Any,
        is_normalized: bool,
        steps: list[str],
        warnings: list[str],
    ) -> NormalizedValue:
        return NormalizedValue(
            original_value=original_value,
            normalized_value=normalized_value,
            is_normalized=is_normalized,
            metadata=NormalizationMetadata(
                normalizer="date",
                method="dateutil_to_year_month",
                steps=steps,
                warnings=warnings,
            ),
        )

