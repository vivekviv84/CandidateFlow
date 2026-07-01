"""Merge engine orchestration."""

from __future__ import annotations

import logging
from typing import Any

from app.merger.duplicate_detector import DuplicateDetector
from app.merger.field_resolvers import (
    EducationResolver,
    ExperienceResolver,
    FieldResolver,
    LinkResolver,
    ListResolver,
    ScalarResolver,
    SkillResolver,
)
from app.merger.models import FieldResolution, MergeCandidateValue, MergeReport, MergeResult
from app.merger.source_priority import SourcePriorityStrategy
from app.models import Candidate, CandidateFragment, Education, Experience, ProvenanceRecord, Skill

logger = logging.getLogger(__name__)


class MergeEngine:
    """Resolve candidate fragments into one canonical candidate and merge report."""

    FIELD_ALIASES: dict[str, tuple[str, ...]] = {
        "candidate_id": ("candidate_id", "id"),
        "full_name": ("full_name", "name", "candidate_name"),
        "emails": ("emails", "email"),
        "phones": ("phones", "phone"),
        "location": ("location",),
        "links": ("links",),
        "headline": ("headline",),
        "years_experience": ("years_experience",),
        "skills": ("skills",),
        "experience": ("experience",),
        "education": ("education",),
    }

    def __init__(
        self,
        priority_strategy: SourcePriorityStrategy | None = None,
        duplicate_detector: DuplicateDetector | None = None,
    ) -> None:
        self.priority = priority_strategy or SourcePriorityStrategy()
        self.duplicates = duplicate_detector or DuplicateDetector()
        self.resolvers = self._default_resolvers()

    def merge(self, fragments: list[CandidateFragment]) -> MergeResult:
        """Merge candidate fragments without reading, validating, or normalizing data."""

        logger.info("Merging %s candidate fragment(s)", len(fragments))
        resolutions: dict[str, FieldResolution] = {}
        report = MergeReport(fragments_seen=len(fragments))

        for field_name, resolver in self.resolvers.items():
            candidate_values = self._candidate_values_for(field_name, fragments)
            resolution = resolver.resolve(candidate_values)
            resolutions[field_name] = resolution
            report.decisions.extend(resolution.decisions)
            report.warnings.extend(resolution.warnings)
            if resolution.decisions:
                report.fields_resolved.append(field_name)

        candidate = self._candidate_from_resolutions(resolutions, report)
        logger.info("Merge produced candidate %s", candidate.candidate_id)
        return MergeResult(candidate=candidate, report=report)

    def _default_resolvers(self) -> dict[str, FieldResolver]:
        return {
            "candidate_id": ScalarResolver("candidate_id", self.priority, self.duplicates),
            "full_name": ScalarResolver("full_name", self.priority, self.duplicates),
            "emails": ListResolver("emails", self.priority, self.duplicates),
            "phones": ListResolver("phones", self.priority, self.duplicates),
            "location": ScalarResolver("location", self.priority, self.duplicates),
            "links": LinkResolver("links", self.priority, self.duplicates),
            "headline": ScalarResolver("headline", self.priority, self.duplicates),
            "years_experience": ScalarResolver("years_experience", self.priority, self.duplicates),
            "skills": SkillResolver("skills", self.priority, self.duplicates),
            "experience": ExperienceResolver("experience", self.priority, self.duplicates),
            "education": EducationResolver("education", self.priority, self.duplicates),
        }

    def _candidate_values_for(
        self,
        field_name: str,
        fragments: list[CandidateFragment],
    ) -> list[MergeCandidateValue]:
        values: list[MergeCandidateValue] = []
        aliases = self.FIELD_ALIASES[field_name]
        for fragment in fragments:
            for alias in aliases:
                if alias not in fragment.fields:
                    continue
                values.extend(self._values_from_field(field_name, fragment, alias, fragment.fields[alias]))
        return values

    def _values_from_field(
        self,
        field_name: str,
        fragment: CandidateFragment,
        alias: str,
        raw_value: Any,
    ) -> list[MergeCandidateValue]:
        if field_name in {"emails", "phones"}:
            items = raw_value if isinstance(raw_value, list) else [raw_value]
            return [self._candidate_value(field_name, item, fragment, alias) for item in items]

        if field_name == "links":
            if not isinstance(raw_value, dict):
                return []
            return [
                self._candidate_value(field_name, {"platform": platform, "url": url}, fragment, alias)
                for platform, url in raw_value.items()
            ]

        if field_name in {"skills", "experience", "education"}:
            items = raw_value if isinstance(raw_value, list) else [raw_value]
            return [
                self._candidate_value(field_name, self._structured_value(field_name, item), fragment, alias)
                for item in items
            ]

        return [self._candidate_value(field_name, raw_value, fragment, alias)]

    def _candidate_value(
        self,
        field_name: str,
        value: Any,
        fragment: CandidateFragment,
        alias: str,
    ) -> MergeCandidateValue:
        return MergeCandidateValue(
            field=field_name,
            value=value,
            source=fragment.source,
            source_priority=fragment.source_priority or self.priority.priority_for(fragment.source),
            confidence=fragment.confidence,
            extracted_at=fragment.extracted_at,
            metadata={"source_field": alias, **fragment.metadata},
        )

    @staticmethod
    def _structured_value(field_name: str, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if field_name == "skills":
            return {"name": value, "canonical_name": value}
        return {"raw": value}

    def _candidate_from_resolutions(
        self,
        resolutions: dict[str, FieldResolution],
        report: MergeReport,
    ) -> Candidate:
        candidate_id = resolutions["candidate_id"].value
        if not candidate_id:
            candidate_id = self._fallback_candidate_id()
            report.warnings.append("candidate_id was missing; generated deterministic fallback id.")

        provenance = [
            ProvenanceRecord(
                field=decision.field,
                selected_value=decision.selected_value,
                source=decision.selected_source,
                method=decision.strategy,
                reason=decision.reason,
                confidence=decision.confidence,
                timestamp=decision.timestamp,
                discarded_values=[discarded.value for discarded in decision.discarded_values],
            )
            for decision in report.decisions
        ]

        return Candidate(
            candidate_id=str(candidate_id),
            full_name=resolutions["full_name"].value,
            emails=[str(value) for value in resolutions["emails"].value],
            phones=[str(value) for value in resolutions["phones"].value],
            location=self._optional_string(resolutions["location"].value),
            links={str(key): str(value) for key, value in resolutions["links"].value.items()},
            headline=resolutions["headline"].value,
            years_experience=resolutions["years_experience"].value,
            skills=[Skill(**skill) for skill in resolutions["skills"].value],
            experience=[Experience(**item) for item in resolutions["experience"].value if "raw" not in item],
            education=[Education(**item) for item in resolutions["education"].value if "raw" not in item],
            provenance=provenance,
            overall_confidence=self._overall_confidence(report),
            validation_errors=[],
        )

    @staticmethod
    def _fallback_candidate_id() -> str:
        return "candidate-unknown"

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _overall_confidence(report: MergeReport) -> float:
        if not report.decisions:
            return 0.0
        return round(sum(decision.confidence for decision in report.decisions) / len(report.decisions), 4)
