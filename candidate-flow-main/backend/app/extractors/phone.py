"""Phone extractor."""

from __future__ import annotations

import logging
import re

from app.extractors._helpers import fragment_text_values, unique_preserve_order
from app.extractors.models import ExtractionMetadata, ExtractionResult
from app.models import CandidateFragment

logger = logging.getLogger(__name__)


class PhoneExtractor:
    """Extract phone-like strings without converting them to E.164."""

    PHONE_PATTERN = re.compile(
        r"(?<!\w)(?:\+?\d[\d().\-\s]{6,}\d)(?:\s*(?:x|ext\.?)\s*\d+)?(?!\w)",
        re.IGNORECASE,
    )

    def extract(self, fragment: CandidateFragment) -> ExtractionResult:
        """Return phone values as source substrings, with no phone normalization."""

        logger.info("Extracting phones from %s fragment", fragment.source)
        matches: list[str] = []
        evidence: list[str] = []

        for text in fragment_text_values(fragment.fields):
            for match in self.PHONE_PATTERN.finditer(text):
                candidate = match.group(0)
                digit_count = sum(character.isdigit() for character in candidate)
                if 7 <= digit_count <= 18:
                    matches.append(candidate)
                    evidence.append(text)

        values = unique_preserve_order(matches)
        confidence = 0.82 if values else 0.0
        return ExtractionResult(
            field_name="phones",
            values=values,
            metadata=ExtractionMetadata(
                extractor="phone",
                source=fragment.source,
                method="regex_phone_pattern",
                confidence=confidence,
                evidence=unique_preserve_order(evidence),
            ),
        )

