"""Name extractor."""

from __future__ import annotations

import logging
import re

from app.extractors.models import ExtractionMetadata, ExtractionResult
from app.models import CandidateFragment

logger = logging.getLogger(__name__)


class NameExtractor:
    """Extract candidate names from explicit fields or resume headings."""

    NAME_FIELD_NAMES = ("full_name", "name", "candidate_name")
    LABEL_PATTERN = re.compile(r"(?im)^\s*(?:name|candidate)\s*[:\-]\s*(.+)$")

    def extract(self, fragment: CandidateFragment) -> ExtractionResult:
        """Return likely name values without casing or token normalization."""

        logger.info("Extracting names from %s fragment", fragment.source)
        evidence: list[str] = []

        for field_name in self.NAME_FIELD_NAMES:
            value = fragment.fields.get(field_name)
            if isinstance(value, str) and value.strip():
                evidence.append(f"{field_name}: {value}")
                return self._result(fragment, [value.strip()], "explicit_name_field", evidence, 0.88)

        raw_text = fragment.fields.get("raw_text")
        if isinstance(raw_text, str):
            labeled = self.LABEL_PATTERN.search(raw_text)
            if labeled:
                value = labeled.group(1).strip()
                return self._result(fragment, [value], "labeled_name_line", [labeled.group(0)], 0.72)

            first_line = self._first_resume_heading(raw_text)
            if first_line:
                return self._result(fragment, [first_line], "first_non_empty_text_line", [first_line], 0.55)

        return self._result(fragment, [], "explicit_or_heading_name", [], 0.0)

    @staticmethod
    def _first_resume_heading(raw_text: str) -> str | None:
        for line in raw_text.splitlines():
            candidate = line.strip()
            if candidate and len(candidate.split()) <= 5 and "@" not in candidate:
                return candidate
        return None

    @staticmethod
    def _result(
        fragment: CandidateFragment,
        values: list[str],
        method: str,
        evidence: list[str],
        confidence: float,
    ) -> ExtractionResult:
        return ExtractionResult(
            field_name="full_name",
            values=values,
            metadata=ExtractionMetadata(
                extractor="name",
                source=fragment.source,
                method=method,
                confidence=confidence,
                evidence=evidence,
            ),
        )

