"""Source priority strategy for deterministic conflict resolution."""

from __future__ import annotations

from typing import Any

from app.merger.models import MergeCandidateValue
from app.models.candidate_fragment import DEFAULT_SOURCE_PRIORITIES, SourceType


class SourcePriorityStrategy:
    """Encapsulate source trust ranking and stable value ordering."""

    def __init__(self, priorities: dict[SourceType, int] | None = None) -> None:
        self._priorities = priorities or DEFAULT_SOURCE_PRIORITIES

    def priority_for(self, source: SourceType) -> int:
        """Return configured priority for a source."""

        return self._priorities[source]

    def sort_key(self, candidate_value: MergeCandidateValue) -> tuple[Any, ...]:
        """Return an ascending sort key where the best value sorts first."""

        return (
            -candidate_value.confidence,
            -candidate_value.source_priority,
            -candidate_value.extracted_at.timestamp(),
            self.stable_value_key(candidate_value.value),
        )

    @staticmethod
    def stable_value_key(value: Any) -> str:
        """Create a deterministic comparable representation for tie-breaking."""

        if isinstance(value, dict):
            items = sorted((str(key), SourcePriorityStrategy.stable_value_key(item)) for key, item in value.items())
            return repr(items)
        if isinstance(value, list):
            return repr([SourcePriorityStrategy.stable_value_key(item) for item in value])
        return repr(value)

