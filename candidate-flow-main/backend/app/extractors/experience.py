"""Experience extractor."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.extractors._helpers import unique_preserve_order
from app.extractors.models import ExtractionMetadata, ExtractionResult
from app.models import CandidateFragment

logger = logging.getLogger(__name__)


class ExperienceExtractor:
    """Extract experience entries from explicit fields or deterministic lines."""

    EXPERIENCE_FIELD_NAMES = ("experience", "work_experience", "employment")
    EXPERIENCE_LINE_PATTERN = re.compile(
        r"(?im)^\s*(?:experience|work)\s*[:\-]\s*"
        r"(?P<title>.+?)\s+at\s+(?P<company>.+?)"
        r"(?:\s*\((?P<dates>[^)]+)\))?\s*$"
    )

    def extract(self, fragment: CandidateFragment) -> ExtractionResult:
        """Return experience dictionaries without date normalization or merging."""

        logger.info("Extracting experience from %s fragment", fragment.source)
        values: list[dict[str, Any]] = []
        evidence: list[str] = []

        for field_name in self.EXPERIENCE_FIELD_NAMES:
            if field_name in fragment.fields:
                extracted = self._from_structured_value(fragment.fields[field_name])
                values.extend(extracted)
                evidence.append(field_name)

        raw_text = fragment.fields.get("raw_text")
        if isinstance(raw_text, str):
            for match in self.EXPERIENCE_LINE_PATTERN.finditer(raw_text):
                values.append(
                    {
                        "company": match.group("company").strip(),
                        "title": match.group("title").strip(),
                        "dates": match.group("dates").strip() if match.group("dates") else None,
                        "summary": None,
                    }
                )
                evidence.append(match.group(0))

        unique_values = unique_preserve_order(values)
        confidence = 0.76 if unique_values else 0.0
        return ExtractionResult(
            field_name="experience",
            values=unique_values,
            metadata=ExtractionMetadata(
                extractor="experience",
                source=fragment.source,
                method="explicit_experience_fields_and_labeled_lines",
                confidence=confidence,
                evidence=unique_preserve_order(evidence),
            ),
        )

    def _from_structured_value(self, value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            entries: list[dict[str, Any]] = []
            for item in value:
                entries.extend(self._from_structured_value(item))
            return entries
        if isinstance(value, dict):
            return [self._entry_from_dict(value)]
        if isinstance(value, str) and value.strip():
            return [{"raw": value.strip()}]
        return []

    @staticmethod
    def _entry_from_dict(value: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = {
            "company",
            "title",
            "start_date",
            "end_date",
            "dates",
            "summary",
            "description",
        }
        return {key: value.get(key) for key in allowed_keys if key in value and value.get(key) is not None}

