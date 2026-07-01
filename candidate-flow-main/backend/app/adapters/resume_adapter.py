"""Resume PDF adapter.

This adapter reads text from a PDF resume and stores the raw page text. It does
not extract emails, phones, dates, skills, or any structured candidate facts.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from app.models import CandidateFragment, SourceType

logger = logging.getLogger(__name__)


class ResumeAdapter:
    """Parse resume PDF files into a single candidate fragment."""

    def parse(self, file_path: str | Path) -> list[CandidateFragment]:
        """Read a resume PDF and return a fragment containing raw text.

        Raises:
            FileNotFoundError: When the file does not exist.
            OSError: When the file cannot be read.
            RuntimeError: When pdfplumber is not installed.
        """

        path = Path(file_path)
        logger.info("Extracting resume PDF text from %s", path)
        self._ensure_readable(path)
        pdfplumber = self._load_pdfplumber()

        page_texts: list[str] = []
        parsing_errors: list[str] = []
        try:
            with pdfplumber.open(path) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    try:
                        text = page.extract_text()
                    except Exception as exc:  # pragma: no cover - parser-specific failures vary.
                        logger.warning("Failed to extract page %s from %s: %s", page_number, path, exc)
                        parsing_errors.append(f"Page {page_number} extraction failed: {exc}")
                        continue

                    if text:
                        page_texts.append(text)
                    else:
                        parsing_errors.append(f"Page {page_number} produced no text")
        except Exception as exc:
            logger.warning("Resume PDF parser error in %s: %s", path, exc)
            return [self._fragment(path, "", [f"PDF parser error: {exc}"])]

        raw_text = "\n\n".join(page_texts)
        if not raw_text:
            parsing_errors.append("Resume PDF produced no extractable text")

        fragment = self._fragment(path, raw_text, parsing_errors)
        logger.info("Loaded resume fragment from %s", path)
        return [fragment]

    @staticmethod
    def _ensure_readable(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Resume PDF file not found: {path}")
        if not path.is_file():
            raise OSError(f"Resume PDF path is not a file: {path}")

    @staticmethod
    def _load_pdfplumber() -> Any:
        try:
            return importlib.import_module("pdfplumber")
        except ImportError as exc:
            raise RuntimeError("pdfplumber is required to parse resume PDFs") from exc

    @staticmethod
    def _fragment(path: Path, raw_text: str, errors: list[str]) -> CandidateFragment:
        return CandidateFragment(
            source=SourceType.RESUME,
            metadata={
                "file_name": path.name,
                "content_type": "application/pdf",
            },
            fields={"raw_text": raw_text} if raw_text else {},
            parsing_errors=errors,
            confidence=ResumeAdapter._confidence(raw_text, errors),
        )

    @staticmethod
    def _confidence(raw_text: str, parsing_errors: list[str]) -> float:
        if not raw_text:
            return 0.0
        if parsing_errors:
            return 0.65
        return 0.8

