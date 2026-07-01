"""Unit tests for the consensus-based merge ranking strategy."""

from __future__ import annotations

from datetime import datetime, timezone

from app.merger import MergeEngine
from app.models import CandidateFragment, SourceType


def test_consensus_majority_wins_over_single_higher_confidence() -> None:
    # Option A: "Ada Lovelace" has 2 supporting sources (support_count=2, consensus_score=2/3) but lower confidences (0.5).
    # Option B: "A. Lovelace" has 1 supporting source (support_count=1, consensus_score=1/3) but higher confidence (0.95).
    # Option A (consensus) must win over Option B.
    fragments = [
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={"candidate_id": "cand-001", "full_name": "Ada Lovelace"},
            confidence=0.5,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        CandidateFragment(
            source=SourceType.RESUME,
            fields={"candidate_id": "cand-001", "full_name": "Ada Lovelace"},
            confidence=0.5,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        CandidateFragment(
            source=SourceType.RECRUITER_CSV,
            fields={"candidate_id": "cand-001", "full_name": "A. Lovelace"},
            confidence=0.95,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    result = MergeEngine().merge(fragments)
    assert result.candidate.full_name == "Ada Lovelace"

    decision = next(d for d in result.report.decisions if d.field == "full_name")
    assert decision.support_count == 2
    assert decision.consensus_score == 2 / 3
    assert decision.selected_source in (SourceType.ATS_JSON, SourceType.RESUME)


def test_consensus_tie_on_support_count_resolved_by_aggregate_confidence() -> None:
    # Option 1: "Option 1" has support_count=2, confidences 0.9 (ATS_JSON, priority 80) and 0.8 (RESUME, priority 70)
    # Option 2: "Option 2" has support_count=2, confidences 0.7 (RECRUITER_CSV, priority 50) and 0.6 (RECRUITER_NOTES, priority 40)
    # Option 1 must win because of higher aggregated confidence.
    fragments = [
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={"candidate_id": "cand-001", "full_name": "Option 1"},
            confidence=0.9,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        CandidateFragment(
            source=SourceType.RESUME,
            fields={"candidate_id": "cand-001", "full_name": "Option 1"},
            confidence=0.8,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        CandidateFragment(
            source=SourceType.RECRUITER_CSV,
            fields={"candidate_id": "cand-001", "full_name": "Option 2"},
            confidence=0.7,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        CandidateFragment(
            source=SourceType.RECRUITER_NOTES,
            fields={"candidate_id": "cand-001", "full_name": "Option 2"},
            confidence=0.6,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    result = MergeEngine().merge(fragments)
    assert result.candidate.full_name == "Option 1"

    decision = next(d for d in result.report.decisions if d.field == "full_name")
    assert decision.support_count == 2
    assert decision.consensus_score == 0.5  # 2 supporting sources / 4 total sources
    assert decision.selected_source == SourceType.ATS_JSON  # ATS_JSON has higher priority than RESUME


def test_consensus_tie_on_confidence_resolved_by_source_priority() -> None:
    # Option 1: "Val 1" from ATS_JSON (priority 80), confidence 0.8
    # Option 2: "Val 2" from RECRUITER_CSV (priority 50), confidence 0.8
    # No consensus exists (max support_count = 1).
    # Option 1 must win due to higher source priority (fallback to existing deterministic ranking).
    fragments = [
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={"candidate_id": "cand-001", "full_name": "Val 1"},
            confidence=0.8,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        CandidateFragment(
            source=SourceType.RECRUITER_CSV,
            fields={"candidate_id": "cand-001", "full_name": "Val 2"},
            confidence=0.8,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    result = MergeEngine().merge(fragments)
    assert result.candidate.full_name == "Val 1"

    decision = next(d for d in result.report.decisions if d.field == "full_name")
    assert decision.support_count == 1
    assert decision.consensus_score == 0.5  # 1 source / 2 total sources


def test_consensus_deterministic_output_identical_inputs() -> None:
    fragments = [
        CandidateFragment(
            source=SourceType.ATS_JSON,
            fields={"candidate_id": "cand-001", "full_name": "Ada"},
            confidence=0.7,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        CandidateFragment(
            source=SourceType.RESUME,
            fields={"candidate_id": "cand-001", "full_name": "Ada Lovelace"},
            confidence=0.8,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        CandidateFragment(
            source=SourceType.RECRUITER_CSV,
            fields={"candidate_id": "cand-001", "full_name": "Ada Lovelace"},
            confidence=0.75,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    engine = MergeEngine()
    results = [engine.merge(fragments).candidate.full_name for _ in range(20)]
    assert all(r == "Ada Lovelace" for r in results)
