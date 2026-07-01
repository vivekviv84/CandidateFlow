"""Candidate Flow command-line interface."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import typer

from app.api.dependencies import APP_VERSION, CandidatePipelineService, PipelineInput

logging.basicConfig(level=logging.INFO)

app = typer.Typer(help="Candidate Flow candidate transformation CLI.")


def _input(
    csv: Path | None,
    ats: Path | None,
    resume: Path | None,
    notes: Path | None,
    config: Path | None,
) -> PipelineInput:
    return PipelineInput(csv_path=csv, ats_path=ats, resume_path=resume, notes_path=notes, config_path=config)


def _print_json(value: Any) -> None:
    typer.echo(json.dumps(value, indent=2, sort_keys=False, default=str))


@app.command()
def transform(
    csv: Path | None = typer.Option(None, "--csv", help="Recruiter CSV file."),
    ats: Path | None = typer.Option(None, "--ats", help="ATS JSON file."),
    resume: Path | None = typer.Option(None, "--resume", help="Resume PDF file."),
    notes: Path | None = typer.Option(None, "--notes", help="Recruiter notes TXT file."),
    config: Path | None = typer.Option(None, "--config", help="Projection config JSON file."),
) -> None:
    """Transform candidate sources and print pretty JSON."""

    response = CandidatePipelineService().transform(_input(csv, ats, resume, notes, config))
    _print_json(response.model_dump(mode="json"))


@app.command()
def explain(
    field: str = typer.Option(..., "--field", help="Field name to explain."),
    csv: Path | None = typer.Option(None, "--csv", help="Recruiter CSV file."),
    ats: Path | None = typer.Option(None, "--ats", help="ATS JSON file."),
    resume: Path | None = typer.Option(None, "--resume", help="Resume PDF file."),
    notes: Path | None = typer.Option(None, "--notes", help="Recruiter notes TXT file."),
    config: Path | None = typer.Option(None, "--config", help="Projection config JSON file."),
) -> None:
    """Transform sources and explain one field decision."""

    service = CandidatePipelineService()
    response = service.transform(_input(csv, ats, resume, notes, config))
    _print_json(service.explain(field, response).model_dump(mode="json"))


@app.command()
def validate(
    csv: Path | None = typer.Option(None, "--csv", help="Recruiter CSV file."),
    ats: Path | None = typer.Option(None, "--ats", help="ATS JSON file."),
    resume: Path | None = typer.Option(None, "--resume", help="Resume PDF file."),
    notes: Path | None = typer.Option(None, "--notes", help="Recruiter notes TXT file."),
    config: Path | None = typer.Option(None, "--config", help="Projection config JSON file."),
) -> None:
    """Run transformation and print validation-related summary."""

    response = CandidatePipelineService().transform(_input(csv, ats, resume, notes, config))
    _print_json(
        {
            "status": "ok",
            "validation_errors": response.candidate.get("validation_errors", []),
            "overall_confidence": response.processing_summary.overall_confidence,
        }
    )


@app.command()
def version() -> None:
    """Print application version."""

    _print_json({"version": APP_VERSION})


@app.command()
def health() -> None:
    """Print health status."""

    _print_json({"status": "ok"})


if __name__ == "__main__":
    app()
