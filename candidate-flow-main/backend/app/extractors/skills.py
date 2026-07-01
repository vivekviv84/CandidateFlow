"""Skills extractor."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.extractors._helpers import flatten_field_values, unique_preserve_order
from app.extractors.models import ExtractionMetadata, ExtractionResult
from app.models import CandidateFragment

logger = logging.getLogger(__name__)


class SkillsExtractor:
    """Extract explicit skills from structured fields or skills sections."""

    SKILL_FIELD_NAMES = {"skill", "skills", "technical_skills", "technologies"}
    SKILLS_LINE_PATTERN = re.compile(r"(?im)^\s*(?:skills|technical skills)\s*[:\-]\s*(.+)$")

    def extract(self, fragment: CandidateFragment) -> ExtractionResult:
        """Return skill strings without canonicalization or synonym mapping."""

        logger.info("Extracting skills from %s fragment", fragment.source)
        skills: list[str] = []
        evidence: list[str] = []

        for key, value in fragment.fields.items():
            if key.lower() in self.SKILL_FIELD_NAMES:
                values = list(flatten_field_values(value))
                for item in values:
                    skills.extend(self._split_skill_text(item))
                    evidence.append(item)

        raw_text = fragment.fields.get("raw_text")
        if isinstance(raw_text, str):
            for match in self.SKILLS_LINE_PATTERN.finditer(raw_text):
                section_text = match.group(1)
                skills.extend(self._split_skill_text(section_text))
                evidence.append(match.group(0))

        values = unique_preserve_order(skill for skill in skills if skill)
        confidence = 0.78 if values else 0.0
        return ExtractionResult(
            field_name="skills",
            values=values,
            metadata=ExtractionMetadata(
                extractor="skills",
                source=fragment.source,
                method="explicit_skill_fields_and_sections",
                confidence=confidence,
                evidence=unique_preserve_order(evidence),
            ),
        )

    @staticmethod
    def _split_skill_text(value: Any) -> list[str]:
        text = str(value)
        return [part.strip() for part in re.split(r"[,;|/]", text) if part.strip()]

