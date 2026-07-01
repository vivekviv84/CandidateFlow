"""List field resolver."""

from __future__ import annotations

from app.merger.field_resolvers.base import FieldResolver
from app.merger.models import FieldResolution, MergeCandidateValue, MergeDecision


class ListResolver(FieldResolver):
    """Union and deduplicate list values deterministically."""

    def resolve(self, values: list[MergeCandidateValue]) -> FieldResolution:
        non_empty = [value for value in values if value.value not in ("", None)]
        if not non_empty:
            return FieldResolution(field_name=self.field_name, value=[])

        resolved: list[object] = []
        decisions: list[MergeDecision] = []
        for group in self.duplicates.group_exact(non_empty):
            selected = self._best(group)
            resolved.append(selected.value)
            discarded = [value for value in group if value != selected]
            metrics = self._compute_consensus(group)
            m = metrics[self._get_equivalence_key(selected)]
            has_consensus = max(x["support_count"] for x in metrics.values()) > 1
            decisions.append(
                MergeDecision(
                    field=self.field_name,
                    selected_value=selected.value,
                    selected_source=selected.source,
                    candidate_values=group,
                    discarded_values=discarded,
                    resolver=self.__class__.__name__,
                    strategy="consensus_ranking" if has_consensus else "union_exact_deduplicate",
                    reason="Kept one representative by cross-source consensus." if has_consensus else "Kept one representative for each exact duplicate value.",
                    confidence=selected.confidence,
                    support_count=m["support_count"],
                    consensus_score=m["consensus_score"],
                    supporting_sources=m["supporting_sources"],
                    aggregate_confidence=m["aggregate_confidence"],
                )
            )

        ranked_values = sorted(
            resolved,
            key=lambda item: self.priority.sort_key(next(value for value in non_empty if value.value == item)),
        )
        return FieldResolution(field_name=self.field_name, value=ranked_values, decisions=decisions)

