"""Build candidate provenance from merge reports."""

from __future__ import annotations

import logging

from app.merger import MergeReport
from app.models import ProvenanceRecord
from app.provenance.models import ProvenanceEntry

logger = logging.getLogger(__name__)


class ProvenanceBuilder:
    """Convert merge decisions into candidate provenance entries."""

    def build(self, merge_report: MergeReport) -> list[ProvenanceRecord]:
        """Return candidate provenance records from a merge report."""

        logger.info("Building provenance from %s merge decision(s)", len(merge_report.decisions))
        return [
            ProvenanceRecord(
                field=decision.field,
                selected_value=decision.selected_value,
                source=decision.selected_source,
                method=decision.strategy,
                merge_rule=decision.strategy,
                reason=decision.reason,
                confidence=decision.confidence,
                timestamp=decision.timestamp,
                discarded_values=[item.value for item in decision.discarded_values],
                pipeline_stage="merge",
            )
            for decision in merge_report.decisions
        ]

    def build_entries(self, merge_report: MergeReport) -> list[ProvenanceEntry]:
        """Return standalone provenance entries suitable for JSON responses."""

        return [
            ProvenanceEntry(
                field=record.field,
                selected_value=record.selected_value,
                discarded_values=record.discarded_values,
                source=record.source,
                merge_rule=record.merge_rule or record.method,
                confidence=record.confidence,
                timestamp=record.timestamp.isoformat(),
                pipeline_stage=record.pipeline_stage,
            )
            for record in self.build(merge_report)
        ]
