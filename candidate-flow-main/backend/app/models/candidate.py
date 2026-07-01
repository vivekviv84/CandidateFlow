"""Canonical candidate profile models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.candidate_fragment import SourceType


class ProvenanceRecord(BaseModel):
    """Explainable decision record for a selected canonical value."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str
    selected_value: Any
    source: SourceType
    method: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    pipeline_stage: str = "merge"
    merge_rule: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    discarded_values: list[Any] = Field(default_factory=list)
    normalized_from: Any | None = None


class Skill(BaseModel):
    """Canonical skill with source and confidence context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    canonical_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[SourceType] = Field(default_factory=list)

    @field_validator("name", "canonical_name")
    @classmethod
    def normalize_skill_text(cls, value: str) -> str:
        """Trim skill text before later normalizers perform canonical mapping."""

        return value.strip()


class Experience(BaseModel):
    """Canonical professional experience entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source: SourceType


class Education(BaseModel):
    """Canonical education entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    institution: str
    degree: str | None = None
    field: str | None = None
    end_year: int | None = Field(default=None, ge=1900, le=2200)
    confidence: float = Field(ge=0.0, le=1.0)
    source: SourceType


class Candidate(BaseModel):
    """Single canonical candidate profile emitted by the pipeline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    full_name: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    location: str | None = None
    links: dict[str, str] = Field(default_factory=dict)
    headline: str | None = None
    years_experience: float | None = Field(default=None, ge=0.0)
    skills: list[Skill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    provenance: list[ProvenanceRecord] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    validation_errors: list[str] = Field(default_factory=list)

    @field_validator("emails")
    @classmethod
    def normalize_emails(cls, value: list[str]) -> list[str]:
        """Lowercase, trim, and deduplicate email addresses deterministically."""

        seen: set[str] = set()
        emails: list[str] = []
        for email in value:
            normalized = email.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                emails.append(normalized)
        return emails

    @field_validator("phones")
    @classmethod
    def remove_duplicate_phones(cls, value: list[str]) -> list[str]:
        """Trim and deduplicate phone strings without changing order."""

        seen: set[str] = set()
        phones: list[str] = []
        for phone in value:
            normalized = phone.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                phones.append(normalized)
        return phones




