"""Education field resolver."""

from __future__ import annotations

from typing import Any

from app.merger.field_resolvers.base import FieldResolver
from app.merger.models import FieldResolution, MergeCandidateValue, MergeDecision


class EducationResolver(FieldResolver):
    """Merge duplicate education entries by institution, degree, field, and year."""

    def resolve(self, values: list[MergeCandidateValue]) -> FieldResolution:
        non_empty = [value for value in values if isinstance(value.value, dict)]
        resolved: list[dict[str, Any]] = []
        decisions: list[MergeDecision] = []

        for group in self.duplicates.group_education(non_empty):
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
                    strategy="consensus_ranking" if has_consensus else "group_by_institution_degree_field_year",
                    reason="Merged education entries by cross-source consensus." if has_consensus else "Merged education entries with the same education identity.",
                    confidence=selected.confidence,
                    support_count=m["support_count"],
                    consensus_score=m["consensus_score"],
                    supporting_sources=m["supporting_sources"],
                    aggregate_confidence=m["aggregate_confidence"],
                )
            )

        resolved.sort(key=lambda item: (str(item.get("institution")), str(item.get("degree"))))
        return FieldResolution(field_name=self.field_name, value=resolved, decisions=decisions)

    def _merge_group(self, group: list[MergeCandidateValue], selected: MergeCandidateValue) -> dict[str, Any]:
        values = [item.value for item in sorted(group, key=self.priority.sort_key)]
        return {
            "institution": self._first_present(values, "institution"),
            "degree": self._first_present(values, "degree"),
            "field": self._first_present(values, "field"),
            "end_year": self._first_present(values, "end_year"),
            "confidence": selected.confidence,
            "source": selected.source,
        }

    @staticmethod
    def _first_present(values: list[dict[str, Any]], key: str) -> Any:
        for value in values:
            if value.get(key) not in ("", None):
                return value[key]
        return None

