"""Base field resolver abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.merger.duplicate_detector import DuplicateDetector
from app.merger.models import FieldResolution, MergeCandidateValue
from app.merger.source_priority import SourcePriorityStrategy


class FieldResolver(ABC):
    """Resolve one canonical field from candidate source values using consensus ranking."""

    def __init__(self, field_name: str, priority: SourcePriorityStrategy, duplicates: DuplicateDetector) -> None:
        self.field_name = field_name
        self.priority = priority
        self.duplicates = duplicates

    @abstractmethod
    def resolve(self, values: list[MergeCandidateValue]) -> FieldResolution:
        """Resolve source values into a canonical field value."""

    def _get_equivalence_key(self, val: MergeCandidateValue) -> Any:
        v = val.value
        if isinstance(v, dict):
            if "url" in v:
                return str(v.get("url") or "").casefold()
            if "canonical_name" in v or "name" in v:
                return str(v.get("canonical_name") or v.get("name") or "").casefold()
            if "institution" in v or "degree" in v:
                return (
                    f"{str(v.get('institution') or '').casefold()}|"
                    f"{str(v.get('degree') or '').casefold()}|"
                    f"{str(v.get('field') or '').casefold()}|"
                    f"{str(v.get('end_year') or '').casefold()}"
                )
            if "company" in v or "title" in v:
                return f"{str(v.get('company') or '').casefold()}|{str(v.get('title') or '').casefold()}"
            return self.duplicates._key(v)
        return str(v).casefold() if isinstance(v, str) else v

    def _compute_consensus(self, values: list[MergeCandidateValue]) -> dict[Any, dict[str, Any]]:
        total_sources = len(set(val.source for val in values))
        
        groups: dict[Any, list[MergeCandidateValue]] = {}
        for val in values:
            key = self._get_equivalence_key(val)
            groups.setdefault(key, []).append(val)
            
        metrics: dict[Any, dict[str, Any]] = {}
        for key, group_vals in groups.items():
            supporting_sources = sorted(list(set(val.source for val in group_vals)))
            support_count = len(supporting_sources)
            consensus_score = support_count / total_sources if total_sources > 0 else 0.0
            
            priority_sum = sum(val.source_priority for val in group_vals)
            if priority_sum > 0:
                agg_confidence = sum(val.confidence * val.source_priority for val in group_vals) / priority_sum
            else:
                agg_confidence = sum(val.confidence for val in group_vals) / len(group_vals)
                
            metrics[key] = {
                "support_count": support_count,
                "consensus_score": consensus_score,
                "supporting_sources": supporting_sources,
                "aggregate_confidence": agg_confidence,
            }
        return metrics

    def _best(self, values: list[MergeCandidateValue]) -> MergeCandidateValue:
        if not values:
            raise ValueError("No values to select from.")
        if len(values) == 1:
            return values[0]
            
        metrics = self._compute_consensus(values)
        max_support = max(m["support_count"] for m in metrics.values())
        
        if max_support <= 1:
            return sorted(values, key=self.priority.sort_key)[0]
            
        def consensus_sort_key(val: MergeCandidateValue) -> tuple[Any, ...]:
            key = self._get_equivalence_key(val)
            m = metrics[key]
            return (
                -m["support_count"],
                -m["consensus_score"],
                -m["aggregate_confidence"],
                -val.source_priority,
                -val.extracted_at.timestamp(),
                self.priority.stable_value_key(val.value)
            )
            
        return sorted(values, key=consensus_sort_key)[0]

