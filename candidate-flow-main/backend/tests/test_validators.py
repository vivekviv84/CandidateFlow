"""Unit tests for validation-only modules."""

from __future__ import annotations

from app.validators import (
    CandidateSchemaValidator,
    DateValidator,
    EmailValidator,
    PhoneValidator,
    Severity,
    UrlValidator,
)


def test_email_validator_accepts_valid_email_without_modifying_value() -> None:
    value = "ADA@EXAMPLE.COM"

    results = EmailValidator().validate(value, "emails[0]")

    assert results[0].is_valid is True
    assert results[0].severity == Severity.INFO
    assert value == "ADA@EXAMPLE.COM"


def test_email_validator_flags_whitespace_without_normalizing() -> None:
    value = " ada@example.com "

    results = EmailValidator().validate(value, "emails[0]")

    assert results[0].is_valid is False
    assert results[0].severity == Severity.WARNING
    assert results[0].field == "emails[0]"
    assert "normalizer" in results[0].suggested_action
    assert value == " ada@example.com "


def test_email_validator_collects_list_results() -> None:
    results = EmailValidator().validate(["ada@example.com", "not-email"], "emails")

    assert [result.is_valid for result in results] == [True, False]
    assert results[1].field == "emails[1]"


def test_phone_validator_accepts_plausible_source_format() -> None:
    value = "+1 (415) 555-2671 ext. 9"

    results = PhoneValidator().validate(value, "phones[0]")

    assert results[0].is_valid is True
    assert value == "+1 (415) 555-2671 ext. 9"


def test_phone_validator_flags_short_and_unexpected_values() -> None:
    results = PhoneValidator().validate(["123", "555-0100 CALL"], "phones")

    assert [result.is_valid for result in results] == [False, False]
    assert results[0].message == "Phone value has fewer than 7 digits."
    assert results[1].severity == Severity.WARNING


def test_date_validator_accepts_supported_dates_and_present_marker() -> None:
    results = DateValidator().validate(["2024", "2024-06", "Jan 2024", "Present"], "experience_dates")

    assert all(result.is_valid for result in results)


def test_date_validator_rejects_impossible_or_unknown_formats() -> None:
    results = DateValidator().validate(["2024-13", "next summer"], "experience_dates")

    assert [result.is_valid for result in results] == [False, False]
    assert all(result.severity == Severity.ERROR for result in results)


def test_url_validator_accepts_http_and_https_urls() -> None:
    results = UrlValidator().validate(
        {"linkedin": "https://linkedin.com/in/ada", "github": "http://github.com/ada"},
        "links",
    )

    assert all(result.is_valid for result in results)
    assert results[0].field == "links.linkedin"


def test_url_validator_rejects_missing_scheme_and_bad_host() -> None:
    results = UrlValidator().validate(["linkedin.com/in/ada", "https://localhost"], "links")

    assert [result.is_valid for result in results] == [False, False]
    assert results[0].message == "URL scheme must be http or https."
    assert results[1].message == "URL must include a host with a domain."


def test_candidate_schema_validator_accepts_valid_candidate_mapping() -> None:
    candidate = {
        "candidate_id": "cand-001",
        "full_name": "Ada Lovelace",
        "emails": ["ada@example.com"],
        "phones": ["555 0100"],
        "links": {"linkedin": "https://linkedin.com/in/ada"},
        "skills": [{"name": "Python"}],
        "experience": [],
        "education": [],
        "provenance": [],
        "overall_confidence": 0.8,
        "validation_errors": [],
    }

    results = CandidateSchemaValidator().validate(candidate)

    assert len(results) == 1
    assert results[0].is_valid is True
    assert results[0].field == "candidate"


def test_candidate_schema_validator_collects_all_schema_issues() -> None:
    candidate = {
        "candidate_id": "",
        "emails": ["ada@example.com", 42],
        "phones": "555 0100",
        "links": {"github": 123},
        "skills": ["Python"],
        "overall_confidence": 1.4,
    }

    results = CandidateSchemaValidator().validate(candidate)

    assert all(result.is_valid is False for result in results)
    assert {result.field for result in results} == {
        "candidate.candidate_id",
        "candidate.phones",
        "candidate.emails[1]",
        "candidate.skills[0]",
        "candidate.links.github",
        "candidate.overall_confidence",
    }


def test_candidate_schema_validator_rejects_non_mapping_input() -> None:
    results = CandidateSchemaValidator().validate(["not", "a", "candidate"])

    assert results[0].is_valid is False
    assert results[0].field == "candidate"
    assert results[0].message == "Candidate must be a mapping or Pydantic model."


def test_candidate_schema_validator_rejects_boolean_confidence() -> None:
    results = CandidateSchemaValidator().validate(
        {
            "candidate_id": "cand-001",
            "overall_confidence": True,
        }
    )

    assert len(results) == 1
    assert results[0].field == "candidate.overall_confidence"
    assert results[0].message == "overall_confidence must be a numeric value, not a boolean."
