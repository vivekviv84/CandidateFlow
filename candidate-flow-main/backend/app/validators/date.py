"""Date validation."""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any

from app.validators.base import BaseValidator
from app.validators.models import Severity, ValidationResult

logger = logging.getLogger(__name__)


class DateValidator(BaseValidator):
    """Validate common source date strings without rewriting them."""

    PRESENT_VALUES = {"present", "current", "now"}
    DATE_FORMATS = (
        "%Y",
        "%Y-%m",
        "%Y-%m-%d",
        "%b %Y",
        "%B %Y",
        "%b %d %Y",
        "%B %d %Y",
    )
    NUMERIC_PATTERN = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")

    def validate(self, value: Any, field: str = "date") -> list[ValidationResult]:
        """Validate one date value or a list of date values."""

        logger.info("Validating date field %s", field)
        values = value if isinstance(value, list) else [value]
        results: list[ValidationResult] = []
        for index, item in enumerate(values):
            item_field = f"{field}[{index}]" if isinstance(value, list) else field
            results.append(self._validate_one(item, item_field))
        return results

    def _validate_one(self, value: Any, field: str) -> ValidationResult:
        if value is None:
            return ValidationResult(
                is_valid=True,
                severity=Severity.INFO,
                message="Date is absent.",
                field=field,
                suggested_action="No action required.",
            )
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                severity=Severity.ERROR,
                message="Date value must be a string or null.",
                field=field,
                suggested_action="Discard the value or convert it before validation.",
            )

        candidate = value.strip()
        if not candidate:
            return ValidationResult(
                is_valid=False,
                severity=Severity.WARNING,
                message="Date value is blank.",
                field=field,
                suggested_action="Treat the date as missing.",
            )
        if candidate.lower() in self.PRESENT_VALUES:
            return ValidationResult(
                is_valid=True,
                severity=Severity.INFO,
                message="Date value is an accepted open-ended marker.",
                field=field,
                suggested_action="No action required.",
            )
        if self._matches_supported_date(candidate):
            return ValidationResult(
                is_valid=True,
                severity=Severity.INFO,
                message="Date value matches a supported source date format.",
                field=field,
                suggested_action="No action required.",
            )
        return ValidationResult(
            is_valid=False,
            severity=Severity.ERROR,
            message="Date value does not match a supported source date format.",
            field=field,
            suggested_action="Keep the original value for review and exclude it from trusted date output.",
        )

    def _matches_supported_date(self, value: str) -> bool:
        for date_format in self.DATE_FORMATS:
            try:
                parsed = datetime.strptime(value, date_format)
            except ValueError:
                continue
            if self.NUMERIC_PATTERN.fullmatch(value) and not self._numeric_parts_match(value, parsed):
                return False
            return True
        return False

    @staticmethod
    def _numeric_parts_match(value: str, parsed: datetime) -> bool:
        parts = value.split("-")
        if len(parts) >= 2 and int(parts[1]) != parsed.month:
            return False
        if len(parts) == 3 and int(parts[2]) != parsed.day:
            return False
        return True

