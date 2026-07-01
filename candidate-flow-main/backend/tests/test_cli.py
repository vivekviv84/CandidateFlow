"""Unit tests for Typer CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from main import app


runner = CliRunner()


def test_cli_health_and_version() -> None:
    health = runner.invoke(app, ["health"])
    version = runner.invoke(app, ["version"])

    assert health.exit_code == 0
    assert '"status": "ok"' in health.output
    assert version.exit_code == 0
    assert '"version"' in version.output


def test_cli_transform_with_csv(tmp_path) -> None:  # noqa: ANN001
    csv_file = tmp_path / "candidate.csv"
    csv_file.write_text("full_name,email,phone,skills\nAda Lovelace,ada@example.com,4155552671,Python\n", encoding="utf-8")

    result = runner.invoke(app, ["transform", "--csv", str(csv_file)])

    assert result.exit_code == 0
    assert '"candidate"' in result.output
    assert "Ada Lovelace" in result.output


def test_cli_explain_with_csv(tmp_path) -> None:  # noqa: ANN001
    csv_file = tmp_path / "candidate.csv"
    csv_file.write_text("full_name,email,skills\nAda Lovelace,ada@example.com,Python\n", encoding="utf-8")

    result = runner.invoke(app, ["explain", "--field", "full_name", "--csv", str(csv_file)])

    assert result.exit_code == 0
    assert '"field": "full_name"' in result.output


def test_cli_validate_with_csv(tmp_path) -> None:  # noqa: ANN001
    csv_file = tmp_path / "candidate.csv"
    csv_file.write_text("full_name,email,skills\nAda Lovelace,ada@example.com,Python\n", encoding="utf-8")

    result = runner.invoke(app, ["validate", "--csv", str(csv_file)])

    assert result.exit_code == 0
    assert '"status": "ok"' in result.output
