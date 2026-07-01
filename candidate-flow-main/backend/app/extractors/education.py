"""Education extractor."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.extractors._helpers import unique_preserve_order
from app.extractors.models import ExtractionMetadata, ExtractionResult
from app.models import CandidateFragment

logger = logging.getLogger(__name__)


class EducationExtractor:
    """Extract education entries from explicit fields or labeled text lines."""

    EDUCATION_FIELD_NAMES = ("education", "educations", "academic_background")
    EDUCATION_LINE_PATTERN = re.compile(
        r"(?im)^\s*(?:education|degree)\s*[:\-]\s*"
        r"(?P<degree>.+?)\s+(?:at|from)\s+(?P<institution>.+?)"
        r"(?:\s*\((?P<year>\d{4})\))?\s*$"
    )

    def extract(self, fragment: CandidateFragment) -> ExtractionResult:
        """Return education dictionaries without validation or deduplication logic."""

        logger.info("Extracting education from %s fragment", fragment.source)
        values: list[dict[str, Any]] = []
        evidence: list[str] = []

        for field_name in self.EDUCATION_FIELD_NAMES:
            if field_name in fragment.fields:
                values.extend(self._from_structured_value(fragment.fields[field_name]))
                evidence.append(field_name)

        raw_text = fragment.fields.get("raw_text")
        if isinstance(raw_text, str):
            for match in self.EDUCATION_LINE_PATTERN.finditer(raw_text):
                values.append(
                    {
                        "institution": match.group("institution").strip(),
                        "degree": match.group("degree").strip(),
                        "end_year": match.group("year"),
                    }
                )
                evidence.append(match.group(0))

        unique_values = unique_preserve_order(values)
        confidence = 0.74 if unique_values else 0.0
        return ExtractionResult(
            field_name="education",
            values=unique_values,
            metadata=ExtractionMetadata(
                extractor="education",
                source=fragment.source,
                method="explicit_education_fields_and_labeled_lines",
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
            "institution",
            "degree",
            "field",
            "end_year",
            "start_date",
            "end_date",
        }
        return {key: value.get(key) for key in allowed_keys if key in value and value.get(key) is not None}

