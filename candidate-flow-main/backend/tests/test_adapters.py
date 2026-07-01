"""Unit tests for source adapters."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from app.adapters import AtsJsonAdapter, CsvAdapter, NotesAdapter, ResumeAdapter
from app.models import SourceType


def test_csv_adapter_returns_one_fragment_per_row_without_normalizing(tmp_path: Path) -> None:
    csv_file = tmp_path / "recruiter.csv"
    csv_file.write_text(
        "full_name,email,phone,skills\n"
        "Ada Lovelace, ADA@EXAMPLE.COM , 555 0100 , Python; SQL\n"
        "Grace Hopper,grace@example.com,, COBOL\n",
        encoding="utf-8",
    )

    fragments = CsvAdapter().parse(csv_file)

    assert len(fragments) == 2
    assert fragments[0].source == SourceType.RECRUITER_CSV
    assert fragments[0].metadata["row_number"] == 2
    assert fragments[0].fields["email"] == " ADA@EXAMPLE.COM "
    assert fragments[0].fields["phone"] == " 555 0100 "
    assert fragments[0].fields["skills"] == " Python; SQL"
    assert fragments[0].confidence == 0.85


def test_csv_adapter_collects_empty_file_error(tmp_path: Path) -> None:
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("", encoding="utf-8")

    fragments = CsvAdapter().parse(csv_file)

    assert len(fragments) == 1
    assert fragments[0].fields == {}
    assert fragments[0].parsing_errors == ["CSV file is empty"]
    assert fragments[0].confidence == 0.0


def test_ats_json_adapter_parses_object_without_normalizing(tmp_path: Path) -> None:
    json_file = tmp_path / "ats.json"
    json_file.write_text(
        json.dumps(
            {
                "full_name": "Ada Lovelace",
                "email": " ADA@EXAMPLE.COM ",
                "phone": "555 0100",
            }
        ),
        encoding="utf-8",
    )

    fragments = AtsJsonAdapter().parse(json_file)

    assert len(fragments) == 1
    assert fragments[0].source == SourceType.ATS_JSON
    assert fragments[0].fields["email"] == " ADA@EXAMPLE.COM "
    assert fragments[0].fields["phone"] == "555 0100"
    assert fragments[0].confidence == 0.95


def test_ats_json_adapter_skips_non_object_array_items(tmp_path: Path) -> None:
    json_file = tmp_path / "ats-list.json"
    json_file.write_text(json.dumps([{"full_name": "Ada"}, "bad item"]), encoding="utf-8")

    fragments = AtsJsonAdapter().parse(json_file)

    assert len(fragments) == 1
    assert fragments[0].fields == {"full_name": "Ada"}
    assert fragments[0].parsing_errors == ["Item 1 is not a JSON object and was skipped"]
    assert fragments[0].confidence == 0.75


def test_ats_json_adapter_collects_malformed_json_error(tmp_path: Path) -> None:
    json_file = tmp_path / "bad.json"
    json_file.write_text("{not valid json", encoding="utf-8")

    fragments = AtsJsonAdapter().parse(json_file)

    assert len(fragments) == 1
    assert fragments[0].fields == {}
    assert fragments[0].parsing_errors[0].startswith("JSON parser error:")
    assert fragments[0].confidence == 0.0


def test_notes_adapter_returns_raw_text_without_extracting(tmp_path: Path) -> None:
    notes_file = tmp_path / "notes.txt"
    notes_file.write_text("Met candidate. Email: ADA@EXAMPLE.COM. Phone: 555 0100.", encoding="utf-8")

    fragments = NotesAdapter().parse(notes_file)

    assert len(fragments) == 1
    assert fragments[0].source == SourceType.RECRUITER_NOTES
    assert fragments[0].fields == {
        "raw_text": "Met candidate. Email: ADA@EXAMPLE.COM. Phone: 555 0100."
    }
    assert fragments[0].confidence == 0.7


def test_notes_adapter_collects_empty_file_error(tmp_path: Path) -> None:
    notes_file = tmp_path / "empty.txt"
    notes_file.write_text("   ", encoding="utf-8")

    fragments = NotesAdapter().parse(notes_file)

    assert fragments[0].fields == {"raw_text": "   "}
    assert fragments[0].parsing_errors == ["Notes file is empty"]
    assert fragments[0].confidence == 0.0


def test_resume_adapter_returns_raw_page_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_bytes(b"%PDF-1.4 fake test file")
    monkeypatch.setitem(sys.modules, "pdfplumber", _fake_pdfplumber(["Page 1 text", "Page 2 text"]))

    fragments = ResumeAdapter().parse(resume_file)

    assert len(fragments) == 1
    assert fragments[0].source == SourceType.RESUME
    assert fragments[0].fields == {"raw_text": "Page 1 text\n\nPage 2 text"}
    assert fragments[0].confidence == 0.8


def test_resume_adapter_collects_empty_page_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_bytes(b"%PDF-1.4 fake test file")
    monkeypatch.setitem(sys.modules, "pdfplumber", _fake_pdfplumber([None]))

    fragments = ResumeAdapter().parse(resume_file)

    assert fragments[0].fields == {}
    assert fragments[0].parsing_errors == [
        "Page 1 produced no text",
        "Resume PDF produced no extractable text",
    ]
    assert fragments[0].confidence == 0.0


def test_adapters_raise_for_unreadable_files(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        CsvAdapter().parse(missing)
    with pytest.raises(FileNotFoundError):
        AtsJsonAdapter().parse(tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError):
        NotesAdapter().parse(tmp_path / "missing.txt")
    with pytest.raises(FileNotFoundError):
        ResumeAdapter().parse(tmp_path / "missing.pdf")


def _fake_pdfplumber(page_texts: list[str | None]) -> types.SimpleNamespace:
    class FakePage:
        def __init__(self, text: str | None) -> None:
            self._text = text

        def extract_text(self) -> str | None:
            return self._text

    class FakePdf:
        pages = [FakePage(text) for text in page_texts]

        def __enter__(self) -> "FakePdf":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    return types.SimpleNamespace(open=lambda _path: FakePdf())

