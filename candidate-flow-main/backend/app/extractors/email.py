"""Email extractor."""

from __future__ import annotations

import logging
import re

from app.extractors._helpers import fragment_text_values, unique_preserve_order
from app.extractors.models import ExtractionMetadata, ExtractionResult
from app.models import CandidateFragment

logger = logging.getLogger(__name__)


class EmailExtractor:
    """Extract email address strings from a candidate fragment."""

    EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w+-])")

    def extract(self, fragment: CandidateFragment) -> ExtractionResult:
        """Return email values exactly as found, without case normalization."""

        logger.info("Extracting emails from %s fragment", fragment.source)
        matches: list[str] = []
        evidence: list[str] = []

        for text in fragment_text_values(fragment.fields):
            for match in self.EMAIL_PATTERN.finditer(text):
                matches.append(match.group(0))
                evidence.append(text)

        values = unique_preserve_order(matches)
        confidence = 0.9 if values else 0.0
        return ExtractionResult(
            field_name="emails",
            values=values,
            metadata=ExtractionMetadata(
                extractor="email",
                source=fragment.source,
                method="regex_email_pattern",
                confidence=confidence,
                evidence=unique_preserve_order(evidence),
            ),
        )
