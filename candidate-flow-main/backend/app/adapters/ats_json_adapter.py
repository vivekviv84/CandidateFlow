"""ATS JSON adapter.

The adapter preserves source field values as supplied by the ATS. It does not
normalize emails, phones, dates, skills, or reconcile multiple candidates.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.models import CandidateFragment, SourceType

logger = logging.getLogger(__name__)


class AtsJsonAdapter:
    """Parse ATS JSON files into candidate fragments."""

    def parse(self, file_path: str | Path) -> list[CandidateFragment]:
        """Read an ATS JSON file and return one or more fragments.

        A top-level object returns one fragment. A top-level array returns one
        fragment per object. Malformed JSON returns a single error fragment.

        Raises:
            FileNotFoundError: When the file does not exist.
            OSError: When the file cannot be read.
        """

        path = Path(file_path)
        logger.info("Loading ATS JSON from %s", path)
        self._ensure_readable(path)

        try:
            with path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except json.JSONDecodeError as exc:
            logger.warning("ATS JSON parser error in %s: %s", path, exc)
            return [self._error_fragment(path, [f"JSON parser error: {exc}"])]
        except UnicodeDecodeError as exc:
            logger.warning("ATS JSON encoding error in %s: %s", path, exc)
            return [self._error_fragment(path, [f"JSON encoding error: {exc}"])]

        records, errors = self._records_from_payload(payload)
        if not records:
            return [self._error_fragment(path, errors or ["JSON file contains no candidate records"])]

        fragments = [
            CandidateFragment(
                source=SourceType.ATS_JSON,
                metadata={
                    "file_name": path.name,
                    "record_index": index,
                },
                fields=record,
                parsing_errors=errors.copy(),
                confidence=self._confidence(record, errors),
            )
            for index, record in enumerate(records)
        ]

        logger.info("Loaded %s ATS JSON fragment(s) from %s", len(fragments), path)
        return fragments

    @staticmethod
    def _ensure_readable(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"ATS JSON file not found: {path}")
        if not path.is_file():
            raise OSError(f"ATS JSON path is not a file: {path}")

    @staticmethod
    def _records_from_payload(payload: Any) -> tuple[list[dict[str, Any]], list[str]]:
        errors: list[str] = []
        if isinstance(payload, dict):
            return [payload], errors
        if isinstance(payload, list):
            records: list[dict[str, Any]] = []
            for index, item in enumerate(payload):
                if isinstance(item, dict):
                    records.append(item)
                else:
                    errors.append(f"Item {index} is not a JSON object and was skipped")
            return records, errors
        return [], ["Top-level JSON value must be an object or an array of objects"]

    @staticmethod
    def _confidence(fields: dict[str, Any], parsing_errors: list[str]) -> float:
        if not fields:
            return 0.0
        if parsing_errors:
            return 0.75
        return 0.95

    @staticmethod
    def _error_fragment(path: Path, errors: list[str]) -> CandidateFragment:
        return CandidateFragment(
            source=SourceType.ATS_JSON,
            metadata={"file_name": path.name},
            fields={},
            parsing_errors=errors,
            confidence=0.0,
        )

