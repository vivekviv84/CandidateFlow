"""Phone validation."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.validators.base import BaseValidator
from app.validators.models import Severity, ValidationResult

logger = logging.getLogger(__name__)


class PhoneValidator(BaseValidator):
    """Validate phone-like strings without formatting or E.164 conversion."""

    ALLOWED_PATTERN = re.compile(r"^[+\d().\-\s]*(?:\s*(?:x|ext\.?)\s*\d+)?$", re.IGNORECASE)

    def validate(self, value: Any, field: str = "phones") -> list[ValidationResult]:
        """Validate one phone value or a list of phone values."""

        logger.info("Validating phone field %s", field)
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
                message="Phone value must be a string.",
                field=field,
                suggested_action="Discard the value or convert it before validation.",
            )
        digit_count = sum(character.isdigit() for character in value)
        if digit_count < 7:
            return ValidationResult(
                is_valid=False,
                severity=Severity.ERROR,
                message="Phone value has fewer than 7 digits.",
                field=field,
                suggested_action="Keep the value for review; do not include it as a trusted phone number.",
            )
        if digit_count > 18:
            return ValidationResult(
                is_valid=False,
                severity=Severity.ERROR,
                message="Phone value has more than 18 digits.",
                field=field,
                suggested_action="Keep the value for review; do not include it as a trusted phone number.",
            )
        if not self.ALLOWED_PATTERN.fullmatch(value):
            return ValidationResult(
                is_valid=False,
                severity=Severity.WARNING,
                message="Phone value contains unexpected characters.",
                field=field,
                suggested_action="Route the value to manual review or a stricter phone parser.",
            )
        return ValidationResult(
            is_valid=True,
            severity=Severity.INFO,
            message="Phone value has a plausible structure.",
            field=field,
            suggested_action="No action required.",
        )

