"""Skill field resolver."""

from __future__ import annotations

from app.merger.field_resolvers.base import FieldResolver
from app.merger.models import FieldResolution, MergeCandidateValue, MergeDecision


class SkillResolver(FieldResolver):
    """Merge duplicate skills by canonical key without conflict resolution beyond ranking."""

    def resolve(self, values: list[MergeCandidateValue]) -> FieldResolution:
        non_empty = [value for value in values if isinstance(value.value, dict)]
        resolved: list[dict[str, object]] = []
        decisions: list[MergeDecision] = []

        for group in self.duplicates.group_skills(non_empty):
            selected = self._best(group)
            skill = dict(selected.value)
            sources = []
            for value in sorted(group, key=self.priority.sort_key):
                if value.source not in sources:
                    sources.append(value.source)
            skill["sources"] = sources
            skill["confidence"] = selected.confidence
            skill.setdefault("canonical_name", skill.get("name"))
            resolved.append(skill)
            metrics = self._compute_consensus(group)
            m = metrics[self._get_equivalence_key(selected)]
            has_consensus = max(x["support_count"] for x in metrics.values()) > 1
            decisions.append(
                MergeDecision(
                    field=self.field_name,
                    selected_value=skill,
                    selected_source=selected.source,
                    candidate_values=group,
                    discarded_values=[value for value in group if value != selected],
                    resolver=self.__class__.__name__,
                    strategy="consensus_ranking" if has_consensus else "deduplicate_by_canonical_skill_key",
                    reason="Merged skill evidence by cross-source consensus." if has_consensus else "Merged skill evidence sharing the same canonical key.",
                    confidence=selected.confidence,
                    support_count=m["support_count"],
                    consensus_score=m["consensus_score"],
                    supporting_sources=m["supporting_sources"],
                    aggregate_confidence=m["aggregate_confidence"],
                )
            )

        resolved.sort(key=lambda skill: str(skill.get("canonical_name", skill.get("name", ""))))
        return FieldResolution(field_name=self.field_name, value=resolved, decisions=decisions)

