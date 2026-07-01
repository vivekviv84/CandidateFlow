"""Skill normalization."""

from __future__ import annotations

import logging
from typing import Any

from app.normalizers.base import BaseNormalizer
from app.normalizers.models import NormalizationMetadata, NormalizationResult, NormalizedValue

logger = logging.getLogger(__name__)


DEFAULT_SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "py": "Python",
    "python": "Python",
    "ml ops": "MLOps",
    "mlops": "MLOps",
    "sql": "SQL",
    "ts": "TypeScript",
    "typescript": "TypeScript",
}


class SkillsNormalizer(BaseNormalizer):
    """Normalize skill aliases into canonical skill names."""

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        """Create a skill normalizer with optional alias overrides."""

        self.aliases = aliases or DEFAULT_SKILL_ALIASES

    def normalize(self, values: list[Any], field_name: str = "skills") -> NormalizationResult:
        """Normalize skill names without deduplicating or merging them."""

        logger.info("Normalizing %s skill value(s)", len(values))
        normalized_values = [self._normalize_one(value) for value in values]
        return NormalizationResult(field_name=field_name, values=normalized_values)

    def _normalize_one(self, value: Any) -> NormalizedValue:
        steps: list[str] = []
        warnings: list[str] = []

        if not isinstance(value, str):
            warnings.append("Skill value is not a string; preserved original value.")
            return self._result(value, value, False, steps, warnings)

        candidate = value
        trimmed = candidate.strip()
        if trimmed != candidate:
            steps.append("trimmed whitespace")
            candidate = trimmed

        lookup_key = " ".join(candidate.casefold().replace("_", " ").split())
        canonical = self.aliases.get(lookup_key)
        if canonical:
            if canonical != candidate:
                steps.append(f"mapped alias '{candidate}' to canonical skill '{canonical}'")
            normalized = canonical
        else:
            normalized = candidate
            warnings.append("No canonical alias mapping found; preserved trimmed skill value.")

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
                normalizer="skills",
                method="alias_map",
                steps=steps,
                warnings=warnings,
            ),
        )

