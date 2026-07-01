"""Unit tests for the shared model layer."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import (
    Candidate,
    CandidateFragment,
    MissingFieldStrategy,
    ProvenanceRecord,
    RuntimeConfig,
    Skill,
    SourceType,
)


def test_candidate_fragment_assigns_default_priority_and_keeps_errors_clean() -> None:
    fragment = CandidateFragment(
        source=SourceType.ATS_JSON,
        fields={"full_name": "Ada Lovelace"},
        parsing_errors=["", " invalid date ", "   "],
        confidence=0.92,
    )

    assert fragment.source_priority == 100
    assert fragment.parsing_errors == ["invalid date"]
    assert fragment.has_errors is True


def test_candidate_normalizes_emails_and_deduplicates_phones() -> None:
    candidate = Candidate(
        candidate_id="cand-001",
        emails=[" ADA@EXAMPLE.COM ", "ada@example.com", "work@example.com"],
        phones=[" +14155552671 ", "+14155552671"],
    )

    assert candidate.emails == ["ada@example.com", "work@example.com"]
    assert candidate.phones == ["+14155552671"]


def test_confidence_fields_are_bounded() -> None:
    with pytest.raises(ValidationError):
        Skill(
            name="Python",
            canonical_name="python",
            confidence=1.2,
            sources=[SourceType.RESUME],
        )


def test_runtime_config_rejects_unknown_keys_and_blank_output_fields() -> None:
    with pytest.raises(ValidationError):
        RuntimeConfig(output_fields=["full_name", " "])

    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate({"include_confidence": True, "unknown": "value"})


def test_provenance_record_captures_explainability_context() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)

    record = ProvenanceRecord(
        field="full_name",
        selected_value="Ada Lovelace",
        source=SourceType.RECRUITER_CSV,
        method="scalar_conflict_resolution",
        reason="Higher confidence than resume value",
        confidence=0.88,
        timestamp=timestamp,
        discarded_values=["A. Lovelace"],
        normalized_from=" Ada Lovelace ",
    )

    assert record.timestamp == timestamp
    assert record.discarded_values == ["A. Lovelace"]
    assert record.normalized_from == " Ada Lovelace "


def test_runtime_config_defaults_are_projection_friendly() -> None:
    config = RuntimeConfig()

    assert config.include_confidence is True
    assert config.include_provenance is True
    assert config.missing_field_strategy == MissingFieldStrategy.NULL

