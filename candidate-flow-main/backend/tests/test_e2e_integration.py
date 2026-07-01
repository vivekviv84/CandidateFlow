"""End-to-end integration tests for the application layer."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from app.api.dependencies import CandidatePipelineService, PipelineInput
from main import app as cli_app


DATASETS = Path(__file__).resolve().parents[1] / "sample_datasets"


def test_e2e_service_valid_dataset() -> None:
    dataset = DATASETS / "valid"

    response = CandidatePipelineService().transform(
        PipelineInput(
            csv_path=dataset / "recruiter.csv",
            ats_path=dataset / "ats.json",
            notes_path=dataset / "notes.txt",
            config_path=dataset / "config.json",
        )
    )

    assert response.candidate["full_name"] == "Ada Lovelace"
    assert response.processing_summary.sources_processed == 3
    assert response.processing_summary.fields_extracted > 0
    assert response.processing_summary.overall_confidence > 0
    assert response.provenance
    assert "Output generated" in response.processing_summary.logs


def test_e2e_service_conflict_dataset_explainability() -> None:
    dataset = DATASETS / "conflicts"
    service = CandidatePipelineService()

    response = service.transform(
        PipelineInput(
            csv_path=dataset / "recruiter.csv",
            ats_path=dataset / "ats.json",
            notes_path=dataset / "notes.txt",
        )
    )
    explanation = service.explain("full_name", response)

    assert response.processing_summary.conflicts_resolved >= 1
    assert explanation.selected_value is not None
    assert explanation.rule is not None


def test_e2e_cli_duplicate_dataset() -> None:
    dataset = DATASETS / "duplicates"
    runner = CliRunner()

    result = runner.invoke(
        cli_app,
        ["transform", "--csv", str(dataset / "recruiter.csv"), "--ats", str(dataset / "ats.json")],
    )

    assert result.exit_code == 0
    assert '"duplicates_removed"' in result.output
    assert "Ada Lovelace" in result.output


def test_e2e_invalid_inputs_degrade_gracefully() -> None:
    dataset = DATASETS / "invalid_inputs"

    response = CandidatePipelineService().transform(
        PipelineInput(
            csv_path=dataset / "recruiter.csv",
            ats_path=dataset / "ats.json",
            notes_path=dataset / "notes.txt",
        )
    )

    assert response.processing_summary.sources_processed >= 1
    assert response.candidate["candidate_id"]
    assert response.processing_summary.processing_time_ms >= 0


def test_e2e_missing_fields_dataset_still_projects_candidate() -> None:
    dataset = DATASETS / "missing_fields"

    response = CandidatePipelineService().transform(
        PipelineInput(
            csv_path=dataset / "recruiter.csv",
            ats_path=dataset / "ats.json",
        )
    )

    assert response.processing_summary.sources_processed == 2
    assert response.candidate["candidate_id"] == "candidate-unknown"
    assert response.candidate["full_name"] == "Ada Lovelace"
    assert response.processing_summary.conflicts_resolved >= 0
