"""Scalar field resolver."""

from __future__ import annotations

from app.merger.field_resolvers.base import FieldResolver
from app.merger.models import FieldResolution, MergeCandidateValue, MergeDecision


class ScalarResolver(FieldResolver):
    """Resolve a scalar field by deterministic confidence and source ranking."""

    def resolve(self, values: list[MergeCandidateValue]) -> FieldResolution:
        non_empty = [value for value in values if value.value not in ("", None)]
        if not non_empty:
            return FieldResolution(field_name=self.field_name, value=None)

        selected = self._best(non_empty)
        discarded = [value for value in non_empty if value != selected]
        metrics = self._compute_consensus(non_empty)
        m = metrics[self._get_equivalence_key(selected)]
        has_consensus = max(x["support_count"] for x in metrics.values()) > 1
        decision = MergeDecision(
            field=self.field_name,
            selected_value=selected.value,
            selected_source=selected.source,
            candidate_values=non_empty,
            discarded_values=discarded,
            resolver=self.__class__.__name__,
            strategy="consensus_ranking" if has_consensus else "highest_confidence_then_source_priority_then_timestamp_then_stable_value",
            reason="Selected by cross-source consensus." if has_consensus else "Selected the highest-ranked scalar value deterministically.",
            confidence=selected.confidence,
            support_count=m["support_count"],
            consensus_score=m["consensus_score"],
            supporting_sources=m["supporting_sources"],
            aggregate_confidence=m["aggregate_confidence"],
        )
        return FieldResolution(field_name=self.field_name, value=selected.value, decisions=[decision])

