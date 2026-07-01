"""Recruiter notes TXT adapter.

This adapter reads plain-text recruiter notes and stores raw text only. Any
interpretation of the notes belongs to extractor modules, not this adapter.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.models import CandidateFragment, SourceType

logger = logging.getLogger(__name__)


class NotesAdapter:
    """Parse recruiter notes text files into a single candidate fragment."""

    def parse(self, file_path: str | Path) -> list[CandidateFragment]:
        """Read a notes TXT file and return a raw-text fragment.

        Raises:
            FileNotFoundError: When the file does not exist.
            OSError: When the file cannot be read.
        """

        path = Path(file_path)
        logger.info("Loading recruiter notes from %s", path)
        self._ensure_readable(path)

        parsing_errors: list[str] = []
        try:
            raw_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            logger.warning("Recruiter notes encoding error in %s: %s", path, exc)
            return [self._fragment(path, "", [f"TXT encoding error: {exc}"])]

        if not raw_text.strip():
            parsing_errors.append("Notes file is empty")

        fragment = self._fragment(path, raw_text, parsing_errors)
        logger.info("Loaded recruiter notes fragment from %s", path)
        return [fragment]

    @staticmethod
    def _ensure_readable(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Recruiter notes file not found: {path}")
        if not path.is_file():
            raise OSError(f"Recruiter notes path is not a file: {path}")

    @staticmethod
    def _fragment(path: Path, raw_text: str, errors: list[str]) -> CandidateFragment:
        return CandidateFragment(
            source=SourceType.RECRUITER_NOTES,
            metadata={
                "file_name": path.name,
                "content_type": "text/plain",
            },
            fields={"raw_text": raw_text} if raw_text else {},
            parsing_errors=errors,
            confidence=NotesAdapter._confidence(raw_text, errors),
        )

    @staticmethod
    def _confidence(raw_text: str, parsing_errors: list[str]) -> float:
        if not raw_text.strip():
            return 0.0
        if parsing_errors:
            return 0.55
        return 0.7

