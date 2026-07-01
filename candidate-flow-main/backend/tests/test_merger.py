"""Unit tests for the deterministic merge engine."""

from __future__ import annotations

from datetime import datetime, timezone

from app.merger import MergeEngine
from app.models import CandidateFragment, SourceType


def test_merge_engine_resolves_scalar_conflict_by_confidence_then_priority() -> None:
    fragments = [
        CandidateFragment(
            source=SourceType.RESUME,
            fields={"candidate_id": "cand-001", "full_name": "A. Lovelace"},
            confidence=0.9,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={"candidate_id": "cand-001", "full_name": "Ada Lovelace"},
            confidence=0.9,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    result = MergeEngine().merge(fragments)

    assert result.candidate.full_name == "Ada Lovelace"
    name_decision = next(decision for decision in result.report.decisions if decision.field == "full_name")
    assert name_decision.selected_source == SourceType.ATS_JSON
    assert name_decision.discarded_values[0].value == "A. Lovelace"


def test_merge_engine_unions_and_deduplicates_list_values() -> None:
    fragments = [
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={"candidate_id": "cand-001", "emails": ["ada@example.com", "work@example.com"]},
            confidence=0.95,
        ),
        CandidateFragment(
            source=SourceType.RECRUITER_CSV,
            fields={"email": "ada@example.com"},
            confidence=0.85,
        ),
    ]

    result = MergeEngine().merge(fragments)

    assert result.candidate.emails == ["ada@example.com", "work@example.com"]
    email_decisions = [decision for decision in result.report.decisions if decision.field == "emails"]
    assert len(email_decisions) == 2
    duplicate_decision = next(decision for decision in email_decisions if decision.selected_value == "ada@example.com")
    assert len(duplicate_decision.discarded_values) == 1


def test_merge_engine_keeps_one_link_per_platform() -> None:
    fragments = [
        CandidateFragment(
            source=SourceType.RESUME,
            fields={"candidate_id": "cand-001", "links": {"github": "https://github.com/from-resume"}},
            confidence=0.8,
        ),
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={"links": {"github": "https://github.com/from-ats", "linkedin": "https://linkedin.com/in/ada"}},
            confidence=0.9,
        ),
    ]

    result = MergeEngine().merge(fragments)

    assert result.candidate.links == {
        "github": "https://github.com/from-ats",
        "linkedin": "https://linkedin.com/in/ada",
    }
    assert any(decision.field == "links.github" for decision in result.report.decisions)


def test_merge_engine_merges_duplicate_skills_by_canonical_name() -> None:
    fragments = [
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={
                "candidate_id": "cand-001",
                "skills": [{"name": "Python", "canonical_name": "Python"}],
            },
            confidence=0.95,
        ),
        CandidateFragment(
            source=SourceType.RESUME,
            fields={"skills": [{"name": "py", "canonical_name": "Python"}]},
            confidence=0.7,
        ),
    ]

    result = MergeEngine().merge(fragments)

    assert len(result.candidate.skills) == 1
    assert result.candidate.skills[0].canonical_name == "Python"
    assert result.candidate.skills[0].sources == [SourceType.ATS_JSON, SourceType.RESUME]


def test_merge_engine_merges_experience_entries_by_company_and_title() -> None:
    fragments = [
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={
                "candidate_id": "cand-001",
                "experience": [
                    {
                        "company": "Example Corp",
                        "title": "Engineer",
                        "start_date": "2020-01",
                        "end_date": "2023-01",
                        "summary": "Built systems.",
                    }
                ],
            },
            confidence=0.9,
        ),
        CandidateFragment(
            source=SourceType.RESUME,
            fields={
                "experience": [
                    {
                        "company": "Example Corp",
                        "title": "Engineer",
                        "start_date": "2019-12",
                        "end_date": "Present",
                        "summary": "Built distributed candidate data systems.",
                    }
                ],
            },
            confidence=0.75,
        ),
    ]

    result = MergeEngine().merge(fragments)

    assert len(result.candidate.experience) == 1
    experience = result.candidate.experience[0]
    assert experience.company == "Example Corp"
    assert experience.start_date == "2019-12"
    assert experience.end_date == "Present"
    assert experience.summary == "Built distributed candidate data systems."


def test_merge_engine_merges_duplicate_education_entries() -> None:
    fragments = [
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={
                "candidate_id": "cand-001",
                "education": [
                    {
                        "institution": "University of London",
                        "degree": "BSc",
                        "field": "Mathematics",
                        "end_year": 2024,
                    }
                ],
            },
            confidence=0.9,
        ),
        CandidateFragment(
            source=SourceType.RECRUITER_CSV,
            fields={
                "education": [
                    {
                        "institution": "University of London",
                        "degree": "BSc",
                        "field": "Mathematics",
                        "end_year": 2024,
                    }
                ],
            },
            confidence=0.8,
        ),
    ]

    result = MergeEngine().merge(fragments)

    assert len(result.candidate.education) == 1
    assert result.candidate.education[0].institution == "University of London"
    education_decision = next(decision for decision in result.report.decisions if decision.field == "education")
    assert len(education_decision.candidate_values) == 2


def test_merge_engine_generates_candidate_provenance_from_decisions() -> None:
    result = MergeEngine().merge(
        [
            CandidateFragment(
                source=SourceType.ATS_JSON,
                fields={"candidate_id": "cand-001", "full_name": "Ada Lovelace"},
                confidence=0.95,
            )
        ]
    )

    assert result.candidate.candidate_id == "cand-001"
    assert result.candidate.provenance
    assert {record.field for record in result.candidate.provenance} >= {"candidate_id", "full_name"}
    assert result.report.fragments_seen == 1
    assert "candidate_id" in result.report.fields_resolved


def test_merge_engine_uses_deterministic_fallback_candidate_id() -> None:
    result = MergeEngine().merge([])

    assert result.candidate.candidate_id == "candidate-unknown"
    assert result.report.warnings == ["candidate_id was missing; generated deterministic fallback id."]
