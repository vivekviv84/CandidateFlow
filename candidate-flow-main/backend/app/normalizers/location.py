"""Location normalization."""

from __future__ import annotations

import logging
from typing import Any

from app.normalizers.base import BaseNormalizer
from app.normalizers.models import NormalizationMetadata, NormalizationResult, NormalizedValue

logger = logging.getLogger(__name__)


COUNTRY_ALIASES: dict[str, str] = {
    "india": "IN",
    "in": "IN",
    "usa": "US",
    "us": "US",
    "united states": "US",
    "united states of america": "US",
    "uk": "GB",
    "united kingdom": "GB",
}

REGION_ALIASES: dict[str, str] = {
    "ca": "CA",
    "california": "CA",
    "ka": "KA",
    "karnataka": "KA",
    "maharashtra": "MH",
    "mh": "MH",
}


class LocationNormalizer(BaseNormalizer):
    """Normalize simple locations into city, region, and country parts."""

    def normalize(self, values: list[Any], field_name: str = "location") -> NormalizationResult:
        """Normalize location strings or dictionaries without geocoding."""

        logger.info("Normalizing %s location value(s)", len(values))
        normalized_values = [self._normalize_one(value) for value in values]
        return NormalizationResult(field_name=field_name, values=normalized_values)

    def _normalize_one(self, value: Any) -> NormalizedValue:
        steps: list[str] = []
        warnings: list[str] = []

        if isinstance(value, dict):
            normalized = self._from_dict(value, steps, warnings)
            return self._result(value, normalized, normalized != value, steps, warnings)
        if not isinstance(value, str):
            warnings.append("Location value is not a string or object; preserved original value.")
            return self._result(value, value, False, steps, warnings)

        candidate = value
        trimmed = candidate.strip()
        if trimmed != candidate:
            steps.append("trimmed whitespace")
            candidate = trimmed

        parts = [part.strip() for part in candidate.split(",") if part.strip()]
        if not parts:
            warnings.append("Location value is blank after trimming.")
            return self._result(value, candidate, candidate != value, steps, warnings)

        normalized = {"city": None, "region": None, "country": None}
        if len(parts) == 1:
            normalized["city"] = parts[0]
            warnings.append("Only one location part found; treated as city.")
        elif len(parts) == 2:
            normalized["city"] = parts[0]
            normalized["country"] = self._country_code(parts[1], steps, warnings)
        else:
            normalized["city"] = parts[0]
            normalized["region"] = self._region_code(parts[1], steps)
            normalized["country"] = self._country_code(parts[2], steps, warnings)

        return self._result(value, normalized, normalized != value, steps, warnings)

    def _from_dict(
        self,
        value: dict[Any, Any],
        steps: list[str],
        warnings: list[str],
    ) -> dict[str, Any]:
        normalized = {
            "city": value.get("city"),
            "region": value.get("region"),
            "country": value.get("country"),
        }
        if isinstance(normalized["city"], str):
            city = normalized["city"].strip()
            if city != normalized["city"]:
                steps.append("trimmed city whitespace")
            normalized["city"] = city
        if isinstance(normalized["region"], str):
            normalized["region"] = self._region_code(normalized["region"], steps)
        if isinstance(normalized["country"], str):
            normalized["country"] = self._country_code(normalized["country"], steps, warnings)
        return normalized

    @staticmethod
    def _country_code(value: str, steps: list[str], warnings: list[str]) -> str:
        trimmed = value.strip()
        if trimmed != value:
            steps.append("trimmed country whitespace")
        code = COUNTRY_ALIASES.get(trimmed.casefold())
        if code:
            if code != trimmed:
                steps.append(f"mapped country '{trimmed}' to ISO code '{code}'")
            return code
        warnings.append(f"No country mapping found for '{trimmed}'; preserved source country.")
        return trimmed

    @staticmethod
    def _region_code(value: str, steps: list[str]) -> str:
        trimmed = value.strip()
        if trimmed != value:
            steps.append("trimmed region whitespace")
        code = REGION_ALIASES.get(trimmed.casefold())
        if code and code != trimmed:
            steps.append(f"mapped region '{trimmed}' to code '{code}'")
            return code
        return trimmed

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
                normalizer="location",
                method="comma_separated_structuring",
                steps=steps,
                warnings=warnings,
            ),
        )

