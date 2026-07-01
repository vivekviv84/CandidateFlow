"""Reusable interfaces for validators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.validators.models import ValidationResult


class BaseValidator(ABC):
    """Interface implemented by all validation-only components."""

    @abstractmethod
    def validate(self, value: Any, field: str) -> list[ValidationResult]:
        """Validate a value and return all discovered validation results."""

