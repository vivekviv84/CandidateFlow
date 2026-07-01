"""Email validation."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.validators.base import BaseValidator
from app.validators.models import Severity, ValidationResult

logger = logging.getLogger(__name__)


class EmailValidator(BaseValidator):
    """Validate email address strings without normalizing them."""

    EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

    def validate(self, value: Any, field: str = "emails") -> list[ValidationResult]:
        """Validate one email or a list of emails."""

        logger.info("Validating email field %s", field)
        values = value if isinstance(value, list) else [value]
        results: list[ValidationResult] = []
        for index, item in enumerate(values):
            item_field = f"{field}[{index}]" if isinstance(value, list) else field
            results.append(self._validate_one(item, item_field))
        return results

    def _validate_one(self, value: Any, field: str) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                severity=Severity.ERROR,
                message="Email value must be a string.",
                field=field,
                suggested_action="Discard the value or convert it before validation.",
            )
        if value != value.strip():
            return ValidationResult(
                is_valid=False,
                severity=Severity.WARNING,
                message="Email contains leading or trailing whitespace.",
                field=field,
                suggested_action="Send the value to the email normalizer.",
            )
        if not self.EMAIL_PATTERN.fullmatch(value):
            return ValidationResult(
                is_valid=False,
                severity=Severity.ERROR,
                message="Email does not match the expected address format.",
                field=field,
                suggested_action="Keep the original value for review and exclude it from trusted email output.",
            )
        return ValidationResult(
            is_valid=True,
            severity=Severity.INFO,
            message="Email format is valid.",
            field=field,
            suggested_action="No action required.",
        )

