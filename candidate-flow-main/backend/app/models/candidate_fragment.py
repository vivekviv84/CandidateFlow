"""Source-neutral candidate fragment model.

Adapters are the only layer that should know about CSV, JSON, PDF, or TXT.
Every adapter emits this model so downstream pipeline stages can stay source
agnostic and deterministic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceType(StrEnum):
    """Supported candidate information sources ordered by business priority."""

    ATS_JSON = "ats_json"
    RECRUITER_CSV = "recruiter_csv"
    RESUME = "resume"
    GITHUB = "github"
    RECRUITER_NOTES = "recruiter_notes"


DEFAULT_SOURCE_PRIORITIES: dict[SourceType, int] = {
    SourceType.ATS_JSON: 100,
    SourceType.RECRUITER_CSV: 80,
    SourceType.RESUME: 60,
    SourceType.GITHUB: 50,
    SourceType.RECRUITER_NOTES: 40,
}


class CandidateFragment(BaseModel):
    """Normalized boundary object emitted by each source adapter.

    Attributes:
        source: Source adapter that produced the fragment.
        source_priority: Higher values win priority ties in merge decisions.
        metadata: Source-level details such as file name, row number, or parser.
        fields: Extracted raw or semi-normalized candidate fields.
        parsing_errors: Non-fatal issues collected while reading the source.
        confidence: Adapter-level confidence in this fragment, from 0.0 to 1.0.
        extracted_at: Timestamp used only as a final deterministic merge signal.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: SourceType
    source_priority: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    fields: dict[str, Any] = Field(default_factory=dict)
    parsing_errors: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_post_init(self, __context: Any) -> None:
        """Apply the configured default priority when an adapter omits it."""

        if self.source_priority is None:
            object.__setattr__(
                self,
                "source_priority",
                DEFAULT_SOURCE_PRIORITIES[self.source],
            )

    @field_validator("parsing_errors")
    @classmethod
    def remove_blank_errors(cls, value: list[str]) -> list[str]:
        """Drop empty error entries while preserving original error order."""

        return [error.strip() for error in value if error and error.strip()]

    @property
    def has_errors(self) -> bool:
        """Return whether the adapter reported non-fatal parsing issues."""

        return bool(self.parsing_errors)

