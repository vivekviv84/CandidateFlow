"""Experience field resolver."""

from __future__ import annotations

from typing import Any

from app.merger.field_resolvers.base import FieldResolver
from app.merger.models import FieldResolution, MergeCandidateValue, MergeDecision


class ExperienceResolver(FieldResolver):
    """Merge duplicate experience entries by company and title."""

    def resolve(self, values: list[MergeCandidateValue]) -> FieldResolution:
        non_empty = [value for value in values if isinstance(value.value, dict)]
        resolved: list[dict[str, Any]] = []
        decisions: list[MergeDecision] = []

        for group in self.duplicates.group_experience(non_empty):
            selected = self._best(group)
            entry = self._merge_group(group, selected)
            resolved.append(entry)
            metrics = self._compute_consensus(group)
            m = metrics[self._get_equivalence_key(selected)]
            has_consensus = max(x["support_count"] for x in metrics.values()) > 1
            decisions.append(
                MergeDecision(
                    field=self.field_name,
                    selected_value=entry,
                    selected_source=selected.source,
                    candidate_values=group,
                    discarded_values=[value for value in group if value != selected],
                    resolver=self.__class__.__name__,
                    strategy="consensus_ranking" if has_consensus else "group_by_company_title_merge_dates_and_summary",
                    reason="Merged experience entries by cross-source consensus." if has_consensus else "Merged experience entries with the same company and title.",
                    confidence=selected.confidence,
                    support_count=m["support_count"],
                    consensus_score=m["consensus_score"],
                    supporting_sources=m["supporting_sources"],
                    aggregate_confidence=m["aggregate_confidence"],
                )
            )

        resolved.sort(key=lambda item: (str(item.get("company")), str(item.get("title"))))
        return FieldResolution(field_name=self.field_name, value=resolved, decisions=decisions)

    def _merge_group(self, group: list[MergeCandidateValue], selected: MergeCandidateValue) -> dict[str, Any]:
        ranked = sorted(group, key=self.priority.sort_key)
        values = [item.value for item in ranked]
        return {
            "company": self._first_present(values, "company"),
            "title": self._first_present(values, "title"),
            "start_date": self._min_present(values, "start_date"),
            "end_date": self._max_present(values, "end_date"),
            "summary": self._longest_present(values, "summary"),
            "confidence": selected.confidence,
            "source": selected.source,
        }

    @staticmethod
    def _first_present(values: list[dict[str, Any]], key: str) -> Any:
        for value in values:
            if value.get(key) not in ("", None):
                return value[key]
        return None

    @staticmethod
    def _min_present(values: list[dict[str, Any]], key: str) -> Any:
        present = [value[key] for value in values if value.get(key) not in ("", None)]
        return min(present) if present else None

    @staticmethod
    def _max_present(values: list[dict[str, Any]], key: str) -> Any:
        present = [value[key] for value in values if value.get(key) not in ("", None)]
        if any(str(value).casefold() in {"present", "current", "now"} for value in present):
            return next(value for value in present if str(value).casefold() in {"present", "current", "now"})
        return max(present) if present else None

    @staticmethod
    def _longest_present(values: list[dict[str, Any]], key: str) -> Any:
        present = [value[key] for value in values if value.get(key) not in ("", None)]
        return max(present, key=lambda item: (len(str(item)), str(item))) if present else None

