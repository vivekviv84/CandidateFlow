"""Recruiter CSV adapter.

This adapter only reads CSV data and wraps each row in a CandidateFragment.
It intentionally does not normalize, merge, extract derived facts, or score
individual fields.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.models import CandidateFragment, SourceType

logger = logging.getLogger(__name__)


class CsvAdapter:
    """Parse recruiter CSV files into candidate fragments."""

    def parse(self, file_path: str | Path) -> list[CandidateFragment]:
        """Read a recruiter CSV file and return one fragment per data row.

        Args:
            file_path: Path to a readable CSV file.

        Raises:
            FileNotFoundError: When the file does not exist.
            OSError: When the file cannot be read.
        """

        path = Path(file_path)
        logger.info("Loading recruiter CSV from %s", path)
        self._ensure_readable(path)

        parsing_errors: list[str] = []
        try:
            data_frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        except pd.errors.EmptyDataError:
            logger.warning("Recruiter CSV is empty: %s", path)
            return [self._error_fragment(path, ["CSV file is empty"])]
        except pd.errors.ParserError as exc:
            logger.warning("Recruiter CSV parser error in %s: %s", path, exc)
            return [self._error_fragment(path, [f"CSV parser error: {exc}"])]
        except UnicodeDecodeError as exc:
            logger.warning("Recruiter CSV encoding error in %s: %s", path, exc)
            return [self._error_fragment(path, [f"CSV encoding error: {exc}"])]

        if data_frame.empty:
            logger.info("Recruiter CSV has headers but no candidate rows: %s", path)
            return [self._error_fragment(path, ["CSV file contains no candidate rows"])]

        fragments: list[CandidateFragment] = []
        for row_number, row in enumerate(data_frame.to_dict(orient="records"), start=2):
            fields = self._drop_empty_values(row)
            row_errors = parsing_errors.copy()
            if not fields:
                row_errors.append(f"Row {row_number} has no non-empty values")

            fragments.append(
                CandidateFragment(
                    source=SourceType.RECRUITER_CSV,
                    metadata={
                        "file_name": path.name,
                        "row_number": row_number,
                        "columns": list(data_frame.columns),
                    },
                    fields=fields,
                    parsing_errors=row_errors,
                    confidence=self._confidence(fields, row_errors),
                )
            )

        logger.info("Loaded %s recruiter CSV fragment(s) from %s", len(fragments), path)
        return fragments

    @staticmethod
    def _ensure_readable(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")
        if not path.is_file():
            raise OSError(f"CSV path is not a file: {path}")

    @staticmethod
    def _drop_empty_values(row: dict[str, Any]) -> dict[str, Any]:
        return {
            str(key): value
            for key, value in row.items()
            if value is not None and str(value).strip() != ""
        }

    @staticmethod
    def _confidence(fields: dict[str, Any], parsing_errors: list[str]) -> float:
        if not fields:
            return 0.0
        if parsing_errors:
            return 0.6
        return 0.85

    @staticmethod
    def _error_fragment(path: Path, errors: list[str]) -> CandidateFragment:
        return CandidateFragment(
            source=SourceType.RECRUITER_CSV,
            metadata={"file_name": path.name},
            fields={},
            parsing_errors=errors,
            confidence=0.0,
        )

