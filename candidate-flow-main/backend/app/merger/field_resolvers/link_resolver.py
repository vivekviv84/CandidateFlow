"""Link field resolver."""

from __future__ import annotations

from app.merger.field_resolvers.base import FieldResolver
from app.merger.models import FieldResolution, MergeCandidateValue, MergeDecision


class LinkResolver(FieldResolver):
    """Keep one link per platform using scalar ranking within each platform."""

    def resolve(self, values: list[MergeCandidateValue]) -> FieldResolution:
        platform_groups = self.duplicates.group_links(values)
        resolved: dict[str, str] = {}
        decisions: list[MergeDecision] = []

        for platform in sorted(platform_groups):
            group = platform_groups[platform]
            selected = self._best(group)
            selected_url = selected.value["url"]
            resolved[platform] = selected_url
            discarded = [value for value in group if value != selected]
            metrics = self._compute_consensus(group)
            m = metrics[self._get_equivalence_key(selected)]
            has_consensus = max(x["support_count"] for x in metrics.values()) > 1
            decisions.append(
                MergeDecision(
                    field=f"{self.field_name}.{platform}",
                    selected_value=selected_url,
                    selected_source=selected.source,
                    candidate_values=group,
                    discarded_values=discarded,
                    resolver=self.__class__.__name__,
                    strategy="consensus_ranking" if has_consensus else "one_link_per_platform",
                    reason="Selected link by cross-source consensus." if has_consensus else "Selected one link for this platform by deterministic ranking.",
                    confidence=selected.confidence,
                    support_count=m["support_count"],
                    consensus_score=m["consensus_score"],
                    supporting_sources=m["supporting_sources"],
                    aggregate_confidence=m["aggregate_confidence"],
                )
            )

        return FieldResolution(field_name=self.field_name, value=resolved, decisions=decisions)

