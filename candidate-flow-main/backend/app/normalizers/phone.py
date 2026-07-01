"""Phone normalization."""

from __future__ import annotations

import logging
from typing import Any

import phonenumbers

from app.normalizers.base import BaseNormalizer
from app.normalizers.models import NormalizationMetadata, NormalizationResult, NormalizedValue

logger = logging.getLogger(__name__)


class PhoneNormalizer(BaseNormalizer):
    """Normalize phone numbers to E.164 using phonenumbers."""

    def __init__(self, default_region: str = "US") -> None:
        """Create a phone normalizer with a fallback parsing region."""

        self.default_region = default_region

    def normalize(self, values: list[Any], field_name: str = "phones") -> NormalizationResult:
        """Normalize phone values to E.164 where possible."""

        logger.info("Normalizing %s phone value(s)", len(values))
        normalized_values = [self._normalize_one(value) for value in values]
        return NormalizationResult(field_name=field_name, values=normalized_values)

    def _normalize_one(self, value: Any) -> NormalizedValue:
        steps: list[str] = []
        warnings: list[str] = []

        if not isinstance(value, str):
            warnings.append("Phone value is not a string; preserved original value.")
            return self._result(value, value, False, steps, warnings)

        candidate = value
        trimmed = candidate.strip()
        if trimmed != candidate:
            steps.append("trimmed whitespace")
            candidate = trimmed

        try:
            parsed = phonenumbers.parse(candidate, self.default_region)
        except phonenumbers.NumberParseException as exc:
            warnings.append(f"Phone parse failed: {exc}")
            return self._result(value, candidate, candidate != value, steps, warnings)

        if not phonenumbers.is_possible_number(parsed):
            warnings.append("Phone number is not possible for the parsed region.")
            return self._result(value, candidate, candidate != value, steps, warnings)

        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        if formatted != candidate:
            steps.append("converted to E.164")
        return self._result(value, formatted, formatted != value, steps, warnings)

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
                normalizer="phone",
                method="phonenumbers_e164",
                steps=steps,
                warnings=warnings,
            ),
        )

