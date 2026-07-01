"""Unit tests for provenance builder."""

from __future__ import annotations

from datetime import datetime, timezone

from app.merger import MergeCandidateValue, MergeDecision, MergeReport
from app.models import SourceType
from app.provenance import ProvenanceBuilder


def test_provenance_builder_converts_merge_decisions() -> None:
    timestamp = datetime(2026, 7, 1, tzinfo=timezone.utc)
    selected = MergeCandidateValue(
        field="full_name",
        value="Ada Lovelace",
        source=SourceType.ATS_JSON,
        source_priority=100,
        confidence=0.95,
        extracted_at=timestamp,
    )
    discarded = MergeCandidateValue(
        field="full_name",
        value="A. Lovelace",
        source=SourceType.RESUME,
        source_priority=60,
        confidence=0.75,
        extracted_at=timestamp,
    )
    report = MergeReport(
        decisions=[
            MergeDecision(
                field="full_name",
                selected_value="Ada Lovelace",
                selected_source=SourceType.ATS_JSON,
                candidate_values=[selected, discarded],
                discarded_values=[discarded],
                resolver="ScalarResolver",
                strategy="highest_confidence",
                reason="Highest confidence won.",
                confidence=0.95,
                timestamp=timestamp,
            )
        ]
    )

    records = ProvenanceBuilder().build(report)

    assert len(records) == 1
    assert records[0].field == "full_name"
    assert records[0].selected_value == "Ada Lovelace"
    assert records[0].discarded_values == ["A. Lovelace"]
    assert records[0].source == SourceType.ATS_JSON
    assert records[0].merge_rule == "highest_confidence"
    assert records[0].method == "highest_confidence"
    assert records[0].confidence == 0.95
    assert records[0].timestamp == timestamp
    assert records[0].pipeline_stage == "merge"


def test_provenance_builder_builds_json_entries() -> None:
    timestamp = datetime(2026, 7, 1, tzinfo=timezone.utc)
    selected = MergeCandidateValue(
        field="emails",
        value="ada@example.com",
        source=SourceType.ATS_JSON,
        source_priority=100,
        confidence=0.9,
        extracted_at=timestamp,
    )
    report = MergeReport(
        decisions=[
            MergeDecision(
                field="emails",
                selected_value="ada@example.com",
                selected_source=SourceType.ATS_JSON,
                candidate_values=[selected],
                resolver="ListResolver",
                strategy="union_exact_deduplicate",
                reason="Selected representative.",
                confidence=0.9,
                timestamp=timestamp,
            )
        ]
    )

    entries = ProvenanceBuilder().build_entries(report)

    assert entries[0].field == "emails"
    assert entries[0].timestamp == "2026-07-01T00:00:00+00:00"
    assert entries[0].pipeline_stage == "merge"
