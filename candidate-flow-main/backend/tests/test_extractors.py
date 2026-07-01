"""Unit tests for deterministic CandidateFragment extractors."""

from __future__ import annotations

from app.extractors import (
    EducationExtractor,
    EmailExtractor,
    ExperienceExtractor,
    NameExtractor,
    PhoneExtractor,
    SkillsExtractor,
)
from app.models import CandidateFragment, SourceType


def test_email_extractor_finds_emails_without_normalizing_case() -> None:
    fragment = CandidateFragment(
        source=SourceType.RECRUITER_NOTES,
        fields={"raw_text": "Contact ADA@EXAMPLE.COM or ada.work+test@Example.co.in."},
    )

    result = EmailExtractor().extract(fragment)

    assert result.field_name == "emails"
    assert result.values == ["ADA@EXAMPLE.COM", "ada.work+test@Example.co.in"]
    assert result.metadata.extractor == "email"
    assert result.metadata.confidence == 0.9


def test_email_extractor_returns_empty_result_when_absent() -> None:
    fragment = CandidateFragment(source=SourceType.RESUME, fields={"raw_text": "No email here"})

    result = EmailExtractor().extract(fragment)

    assert result.values == []
    assert result.metadata.confidence == 0.0


def test_phone_extractor_keeps_source_format() -> None:
    fragment = CandidateFragment(
        source=SourceType.ATS_JSON,
        fields={"phone": "+1 (415) 555-2671 ext. 9", "notes": "Backup 555 0100"},
    )

    result = PhoneExtractor().extract(fragment)

    assert result.values == ["+1 (415) 555-2671 ext. 9", "555 0100"]
    assert result.metadata.method == "regex_phone_pattern"


def test_skills_extractor_reads_structured_field_without_canonicalizing() -> None:
    fragment = CandidateFragment(
        source=SourceType.RECRUITER_CSV,
        fields={"skills": " Python; SQL/ML Ops | Data Modeling "},
    )

    result = SkillsExtractor().extract(fragment)

    assert result.values == ["Python", "SQL", "ML Ops", "Data Modeling"]
    assert result.metadata.confidence == 0.78


def test_skills_extractor_reads_labeled_raw_text_section() -> None:
    fragment = CandidateFragment(
        source=SourceType.RESUME,
        fields={"raw_text": "Ada Lovelace\nSkills: Python, SQL; Data Modeling\nExperience: Engineer"},
    )

    result = SkillsExtractor().extract(fragment)

    assert result.values == ["Python", "SQL", "Data Modeling"]
    assert result.metadata.evidence == ["Skills: Python, SQL; Data Modeling"]


def test_name_extractor_prefers_explicit_full_name() -> None:
    fragment = CandidateFragment(
        source=SourceType.ATS_JSON,
        fields={"full_name": " Ada Lovelace ", "raw_text": "Grace Hopper"},
    )

    result = NameExtractor().extract(fragment)

    assert result.field_name == "full_name"
    assert result.values == ["Ada Lovelace"]
    assert result.metadata.method == "explicit_name_field"


def test_name_extractor_uses_resume_heading_when_no_explicit_name() -> None:
    fragment = CandidateFragment(
        source=SourceType.RESUME,
        fields={"raw_text": "\nAda Lovelace\nada@example.com\nSkills: Python"},
    )

    result = NameExtractor().extract(fragment)

    assert result.values == ["Ada Lovelace"]
    assert result.metadata.confidence == 0.55


def test_experience_extractor_reads_structured_entries_without_date_normalization() -> None:
    fragment = CandidateFragment(
        source=SourceType.ATS_JSON,
        fields={
            "experience": [
                {
                    "company": "Analytical Engines Ltd",
                    "title": "Engineer",
                    "start_date": "Jan 2020",
                    "end_date": "Present",
                    "ignored": "not copied",
                }
            ]
        },
    )

    result = ExperienceExtractor().extract(fragment)

    assert result.values == [
        {
            "company": "Analytical Engines Ltd",
            "end_date": "Present",
            "start_date": "Jan 2020",
            "title": "Engineer",
        }
    ]
    assert result.metadata.confidence == 0.76


def test_experience_extractor_reads_labeled_raw_text_line() -> None:
    fragment = CandidateFragment(
        source=SourceType.RECRUITER_NOTES,
        fields={"raw_text": "Experience: Senior Engineer at Example Corp (Jan 2020 - Mar 2024)"},
    )

    result = ExperienceExtractor().extract(fragment)

    assert result.values == [
        {
            "company": "Example Corp",
            "title": "Senior Engineer",
            "dates": "Jan 2020 - Mar 2024",
            "summary": None,
        }
    ]


def test_education_extractor_reads_structured_entries_without_year_validation() -> None:
    fragment = CandidateFragment(
        source=SourceType.ATS_JSON,
        fields={
            "education": [
                {
                    "institution": "University of London",
                    "degree": "BSc",
                    "field": "Mathematics",
                    "end_year": "1842",
                }
            ]
        },
    )

    result = EducationExtractor().extract(fragment)

    assert result.values == [
        {
            "degree": "BSc",
            "end_year": "1842",
            "field": "Mathematics",
            "institution": "University of London",
        }
    ]
    assert result.metadata.method == "explicit_education_fields_and_labeled_lines"


def test_education_extractor_reads_labeled_raw_text_line() -> None:
    fragment = CandidateFragment(
        source=SourceType.RESUME,
        fields={"raw_text": "Education: BSc Mathematics from University of London (1842)"},
    )

    result = EducationExtractor().extract(fragment)

    assert result.values == [
        {
            "institution": "University of London",
            "degree": "BSc Mathematics",
            "end_year": "1842",
        }
    ]


def test_extractors_do_not_throw_on_empty_fragment() -> None:
    fragment = CandidateFragment(source=SourceType.RECRUITER_CSV, fields={})
    extractors = [
        EmailExtractor(),
        PhoneExtractor(),
        SkillsExtractor(),
        NameExtractor(),
        ExperienceExtractor(),
        EducationExtractor(),
    ]

    results = [extractor.extract(fragment) for extractor in extractors]

    assert all(result.values == [] for result in results)
    assert all(result.metadata.confidence == 0.0 for result in results)

