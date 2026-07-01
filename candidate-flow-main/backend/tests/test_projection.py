"""Unit tests for Module 8A projection layer."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import Candidate, Education, Experience, ProvenanceRecord, Skill, SourceType
from app.models.config import RuntimeConfig
from app.projection import FieldMapper, MissingFieldStrategy, ProjectionConfig, ProjectionError, Projector


def _candidate() -> Candidate:
    return Candidate(
        candidate_id="cand-001",
        full_name="Ada Lovelace",
        emails=["ada@example.com"],
        phones=["+14155552671"],
        location="London, GB",
        links={"github": "https://github.com/ada"},
        headline="Computing pioneer",
        years_experience=5.0,
        skills=[
            Skill(
                name="Python",
                canonical_name="Python",
                confidence=0.9,
                sources=[SourceType.ATS_JSON],
            )
        ],
        experience=[
            Experience(
                company="Analytical Engines Ltd",
                title="Engineer",
                start_date="2020-01",
                end_date="Present",
                summary="Built systems.",
                confidence=0.8,
                source=SourceType.RESUME,
            )
        ],
        education=[
            Education(
                institution="University of London",
                degree="BSc",
                field="Mathematics",
                end_year=2024,
                confidence=0.7,
                source=SourceType.RECRUITER_CSV,
            )
        ],
        provenance=[
            ProvenanceRecord(
                field="full_name",
                selected_value="Ada Lovelace",
                source=SourceType.ATS_JSON,
                method="fixture",
                reason="Fixture value.",
                confidence=0.95,
            )
        ],
        overall_confidence=0.88,
    )


def test_projector_projects_all_fields_by_default() -> None:
    output = Projector().project(_candidate())

    assert output["candidate_id"] == "cand-001"
    assert output["full_name"] == "Ada Lovelace"
    assert output["overall_confidence"] == 0.88
    assert output["provenance"][0]["field"] == "full_name"


def test_projector_selects_fields() -> None:
    config = ProjectionConfig(selected_fields=["candidate_id", "full_name", "emails"])

    output = Projector().project(_candidate(), config)

    assert output == {
        "candidate_id": "cand-001",
        "full_name": "Ada Lovelace",
        "emails": ["ada@example.com"],
    }


def test_projector_renames_selected_fields() -> None:
    config = ProjectionConfig(
        selected_fields=["candidate_id", "full_name"],
        rename_fields={"candidate_id": "id", "full_name": "profile.name"},
    )

    output = Projector().project(_candidate(), config)

    assert output == {"id": "cand-001", "profile": {"name": "Ada Lovelace"}}


def test_projector_supports_path_based_mapping() -> None:
    config = ProjectionConfig(
        field_mappings={
            "id": "candidate_id",
            "profile.primary_email": "emails.0",
            "profile.github": "links.github",
            "profile.first_skill": "skills.0.canonical_name",
        }
    )

    output = Projector().project(_candidate(), config)

    assert output == {
        "id": "cand-001",
        "profile": {
            "primary_email": "ada@example.com",
            "github": "https://github.com/ada",
            "first_skill": "Python",
        },
    }


def test_projector_excludes_confidence_recursively() -> None:
    config = ProjectionConfig(include_confidence=False)

    output = Projector().project(_candidate(), config)

    assert "overall_confidence" not in output
    assert "confidence" not in output["skills"][0]
    assert "confidence" not in output["experience"][0]
    assert "confidence" not in output["education"][0]
    assert "confidence" not in output["provenance"][0]


def test_projector_excludes_provenance() -> None:
    config = ProjectionConfig(include_provenance=False)

    output = Projector().project(_candidate(), config)

    assert "provenance" not in output
    assert output["overall_confidence"] == 0.88


def test_projector_missing_field_null_strategy() -> None:
    config = ProjectionConfig(selected_fields=["missing.path"])

    output = Projector().project(_candidate(), config)

    assert output == {"missing": {"path": None}}


def test_projector_missing_field_omit_strategy() -> None:
    config = ProjectionConfig(
        selected_fields=["candidate_id", "missing.path"],
        on_missing=MissingFieldStrategy.OMIT,
    )

    output = Projector().project(_candidate(), config)

    assert output == {"candidate_id": "cand-001"}


def test_projector_missing_field_error_strategy() -> None:
    config = ProjectionConfig(selected_fields=["missing.path"], on_missing=MissingFieldStrategy.ERROR)

    with pytest.raises(ProjectionError, match="Missing projection field: missing.path"):
        Projector().project(_candidate(), config)


def test_projection_config_rejects_blank_selected_fields() -> None:
    with pytest.raises(ValidationError):
        ProjectionConfig(selected_fields=["candidate_id", " "])


def test_projection_config_can_be_built_from_runtime_config() -> None:
    runtime_config = RuntimeConfig(
        output_fields=["candidate_id"],
        rename_fields={"candidate_id": "id"},
        field_mappings={"profile.name": "full_name"},
        include_confidence=False,
        include_provenance=False,
        missing_field_strategy="omit",
    )

    config = ProjectionConfig.from_runtime_config(runtime_config)

    assert config.selected_fields == ["candidate_id"]
    assert config.rename_fields == {"candidate_id": "id"}
    assert config.field_mappings == {"profile.name": "full_name"}
    assert config.include_confidence is False
    assert config.include_provenance is False
    assert config.on_missing == MissingFieldStrategy.OMIT


def test_field_mapper_gets_and_sets_paths() -> None:
    mapper = FieldMapper()
    output: dict[str, object] = {}

    assert mapper.get_path({"a": {"b": ["x"]}}, "a.b.0") == "x"
    mapper.set_path(output, "profile.name", "Ada Lovelace")

    assert output == {"profile": {"name": "Ada Lovelace"}}
