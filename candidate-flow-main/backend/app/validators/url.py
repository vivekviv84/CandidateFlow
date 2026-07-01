"""URL validation."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from app.validators.base import BaseValidator
from app.validators.models import Severity, ValidationResult

logger = logging.getLogger(__name__)


class UrlValidator(BaseValidator):
    """Validate URL strings without adding schemes or changing casing."""

    ALLOWED_SCHEMES = {"http", "https"}

    def validate(self, value: Any, field: str = "links") -> list[ValidationResult]:
        """Validate one URL, a list of URLs, or a platform-to-URL mapping."""

        logger.info("Validating URL field %s", field)
        if isinstance(value, dict):
            return [self._validate_one(url, f"{field}.{platform}") for platform, url in value.items()]
        values = value if isinstance(value, list) else [value]
        return [
            self._validate_one(item, f"{field}[{index}]" if isinstance(value, list) else field)
            for index, item in enumerate(values)
        ]

    def _validate_one(self, value: Any, field: str) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                severity=Severity.ERROR,
                message="URL value must be a string.",
                field=field,
                suggested_action="Discard the value or convert it before validation.",
            )
        parsed = urlparse(value)
        if parsed.scheme not in self.ALLOWED_SCHEMES:
            return ValidationResult(
                is_valid=False,
                severity=Severity.ERROR,
                message="URL scheme must be http or https.",
                field=field,
                suggested_action="Send the value to URL normalization or manual review.",
            )
        if not parsed.netloc or "." not in parsed.netloc:
            return ValidationResult(
                is_valid=False,
                severity=Severity.ERROR,
                message="URL must include a host with a domain.",
                field=field,
                suggested_action="Keep the original value for review and exclude it from trusted links.",
            )
        return ValidationResult(
            is_valid=True,
            severity=Severity.INFO,
            message="URL structure is valid.",
            field=field,
            suggested_action="No action required.",
        )

