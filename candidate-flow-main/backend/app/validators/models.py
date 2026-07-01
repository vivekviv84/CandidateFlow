"""Shared validation result models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Severity(StrEnum):
    """Validation issue severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationResult(BaseModel):
    """Structured result emitted by every validator.

    Validators never change input values. They only report whether the inspected
    value is acceptable and what downstream processing should do next.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_valid: bool
    severity: Severity
    message: str
    field: str
    suggested_action: str

