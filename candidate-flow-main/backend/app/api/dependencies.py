"""FastAPI dependency providers and pipeline orchestration."""

from __future__ import annotations

import json
import logging
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from app.adapters import AtsJsonAdapter, CsvAdapter, NotesAdapter, ResumeAdapter
from app.api.schemas import ExplainResponse, ProcessingSummary, TransformResponse
from app.confidence import ConfidenceAggregator, ConfidenceFactor, WeightedConfidenceStrategy
from app.extractors import (
    EducationExtractor,
    EmailExtractor,
    ExperienceExtractor,
    NameExtractor,
    PhoneExtractor,
    SkillsExtractor,
)
from app.merger import MergeEngine, MergeReport
from app.models import Candidate, CandidateFragment
from app.normalizers import EmailNormalizer, PhoneNormalizer, SkillsNormalizer
from app.projection import ProjectionConfig, Projector
from app.provenance import ProvenanceBuilder
from app.validators import CandidateSchemaValidator, DateValidator, EmailValidator, PhoneValidator, UrlValidator

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"


@dataclass(frozen=True)
class PipelineInput:
    """Input paths for one pipeline run."""

    csv_path: Path | None = None
    ats_path: Path | None = None
    resume_path: Path | None = None
    notes_path: Path | None = None
    config_path: Path | None = None


@dataclass
class PipelineArtifacts:
    """Internal pipeline artifacts for response and explain operations."""

    candidate: Candidate
    confidence: dict[str, Any]
    merge_report: MergeReport
    provenance: list[dict[str, Any]]
    processing_summary: ProcessingSummary
    logs: list[str] = field(default_factory=list)


class CandidatePipelineService:
    """Application service that composes existing pipeline modules."""

    def __init__(self) -> None:
        self.adapters = {
            "csv": CsvAdapter(),
            "ats": AtsJsonAdapter(),
            "resume": ResumeAdapter(),
            "notes": NotesAdapter(),
        }
        self.extractors = [
            NameExtractor(),
            EmailExtractor(),
            PhoneExtractor(),
            SkillsExtractor(),
            ExperienceExtractor(),
            EducationExtractor(),
        ]
        self.merge_engine = MergeEngine()
        self.provenance_builder = ProvenanceBuilder()
        self.projector = Projector()
        self.confidence_strategy = WeightedConfidenceStrategy()
        self.confidence_aggregator = ConfidenceAggregator()

    def transform(self, pipeline_input: PipelineInput) -> TransformResponse:
        """Run the complete transformation pipeline."""

        started_at = time.perf_counter()
        logs: list[str] = []
        logger.info("Candidate transform started")
        logs.append("Pipeline started")
        source_fragments = self._load_fragments(pipeline_input, logs)
        extracted_fragments, fields_extracted, fields_normalized = self._extract_and_normalize(source_fragments, logs)
        merge_result = self.merge_engine.merge(extracted_fragments)
        logs.append("Merged candidate profile")
        provenance_records = self.provenance_builder.build(merge_result.report)
        logs.append("Built provenance records")
        candidate = merge_result.candidate.model_copy(update={"provenance": provenance_records})
        confidence = self._confidence(candidate, merge_result.report, logs)
        projected_candidate = self._project(candidate, pipeline_input.config_path)
        logs.append("Applied projection")
        provenance = [record.model_dump(mode="json") for record in provenance_records]
        processing_time_ms = round((time.perf_counter() - started_at) * 1000, 3)
        logs.append("Output generated")
        summary = ProcessingSummary(
            sources_processed=len(source_fragments),
            fields_extracted=fields_extracted,
            fields_normalized=fields_normalized,
            duplicates_removed=self._duplicates_removed(merge_result.report),
            conflicts_resolved=self._conflicts_resolved(merge_result.report),
            overall_confidence=confidence["overall_score"] or 0.0,
            processing_time_ms=processing_time_ms,
            logs=logs,
        )
        logger.info(
            "Candidate transform completed: sources=%s extracted=%s normalized=%s duplicates=%s conflicts=%s confidence=%s time_ms=%s",
            summary.sources_processed,
            summary.fields_extracted,
            summary.fields_normalized,
            summary.duplicates_removed,
            summary.conflicts_resolved,
            summary.overall_confidence,
            summary.processing_time_ms,
        )
        return TransformResponse(
            candidate=projected_candidate,
            confidence=confidence,
            merge_report=merge_result.report.model_dump(mode="json"),
            provenance=provenance,
            processing_summary=summary,
        )

    def explain(self, field_name: str, response: TransformResponse) -> ExplainResponse:
        """Explain a field from a transform response."""

        decisions = response.merge_report.get("decisions", [])
        matches = [decision for decision in decisions if decision.get("field") == field_name]
        if not matches:
            matches = [decision for decision in decisions if str(decision.get("field", "")).startswith(f"{field_name}.")]
        if not matches:
            return ExplainResponse(field=field_name)

        decision = matches[0]
        return ExplainResponse(
            field=field_name,
            selected_value=decision.get("selected_value"),
            rejected_values=[item.get("value") for item in decision.get("discarded_values", [])],
            source=decision.get("selected_source"),
            rule=decision.get("strategy"),
            confidence=decision.get("confidence"),
            pipeline_history=[item for item in response.provenance if item.get("field") == decision.get("field")],
            support_count=decision.get("support_count"),
            consensus_score=decision.get("consensus_score"),
            supporting_sources=decision.get("supporting_sources"),
            aggregate_confidence=decision.get("aggregate_confidence"),
        )

    async def transform_uploads(
        self,
        csv: UploadFile | None,
        ats: UploadFile | None,
        resume: UploadFile | None,
        notes: UploadFile | None,
        config: UploadFile | None,
    ) -> TransformResponse:
        """Persist uploaded files temporarily and run transformation."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pipeline_input = PipelineInput(
                csv_path=await self._save_upload(csv, temp_path, "input.csv"),
                ats_path=await self._save_upload(ats, temp_path, "ats.json"),
                resume_path=await self._save_upload(resume, temp_path, "resume.pdf"),
                notes_path=await self._save_upload(notes, temp_path, "notes.txt"),
                config_path=await self._save_upload(config, temp_path, "config.json"),
            )
            return self.transform(pipeline_input)

    def _load_fragments(self, pipeline_input: PipelineInput, logs: list[str]) -> list[CandidateFragment]:
        fragments: list[CandidateFragment] = []
        if pipeline_input.csv_path:
            logs.append("Loading CSV")
            fragments.extend(self.adapters["csv"].parse(pipeline_input.csv_path))
        if pipeline_input.ats_path:
            logs.append("Loading ATS JSON")
            fragments.extend(self.adapters["ats"].parse(pipeline_input.ats_path))
        if pipeline_input.resume_path:
            logs.append("Extracting Resume")
            fragments.extend(self.adapters["resume"].parse(pipeline_input.resume_path))
        if pipeline_input.notes_path:
            logs.append("Loading Notes")
            fragments.extend(self.adapters["notes"].parse(pipeline_input.notes_path))
        if not fragments:
            raise HTTPException(status_code=400, detail="At least one input source is required.")
        logs.append(f"Loaded {len(fragments)} source fragment(s)")
        return fragments

    def _extract_and_normalize(
        self,
        fragments: list[CandidateFragment],
        logs: list[str],
    ) -> tuple[list[CandidateFragment], int, int]:
        output: list[CandidateFragment] = []
        fields_extracted = 0
        fields_normalized = 0
        logs.append("Extracting candidate fields")
        normalized_kinds: set[str] = set()
        for fragment in fragments:
            fields: dict[str, Any] = {}
            for extractor in self.extractors:
                result = extractor.extract(fragment)
                if result.values:
                    fields_extracted += len(result.values)
                    fields[result.field_name] = result.values if len(result.values) > 1 else result.values[0]

            if "emails" in fields:
                normalized_kinds.add("emails")
                items = fields["emails"] if isinstance(fields["emails"], list) else [fields["emails"]]
                normalized = EmailNormalizer().normalize(items).values
                fields["emails"] = [item.normalized_value for item in normalized]
                fields_normalized += len(normalized)
            if "phones" in fields:
                normalized_kinds.add("phones")
                items = fields["phones"] if isinstance(fields["phones"], list) else [fields["phones"]]
                normalized = PhoneNormalizer().normalize(items).values
                fields["phones"] = [item.normalized_value for item in normalized]
                fields_normalized += len(normalized)
            if "skills" in fields:
                normalized_kinds.add("skills")
                items = fields["skills"] if isinstance(fields["skills"], list) else [fields["skills"]]
                normalized = SkillsNormalizer().normalize(items).values
                fields["skills"] = [
                    {"name": item.original_value, "canonical_name": item.normalized_value}
                    for item in normalized
                ]
                fields_normalized += len(normalized)

            output.append(
                CandidateFragment(
                    source=fragment.source,
                    source_priority=fragment.source_priority,
                    metadata=fragment.metadata,
                    fields=fields,
                    parsing_errors=fragment.parsing_errors,
                    confidence=fragment.confidence,
                    extracted_at=fragment.extracted_at,
                )
            )
        logs.append(f"Extracted {fields_extracted} field value(s)")
        if normalized_kinds:
            logs.append(f"Normalized {fields_normalized} value(s): {', '.join(sorted(normalized_kinds))}")
        else:
            logs.append("No normalizable values found")
        return output, fields_extracted, fields_normalized

    def _confidence(self, candidate: Candidate, merge_report: MergeReport, logs: list[str]) -> dict[str, Any]:
        logs.append("Completed validation checks")
        validator_results = self._validate_candidate(candidate)
        validation_score = 1.0 if all(result.is_valid for result in validator_results) else 0.7
        factors = [
            ConfidenceFactor(name="source_reliability", score=0.85, weight=0.4, reason="Sources were processed successfully."),
            ConfidenceFactor(name="cross_source_agreement", score=self._agreement_score(merge_report), weight=0.3, reason="Calculated from duplicate merge decisions."),
            ConfidenceFactor(name="validation", score=validation_score, weight=0.2, reason="Validation checks completed."),
            ConfidenceFactor(name="extraction_confidence", score=candidate.overall_confidence, weight=0.1, reason="Derived from merge decision confidence."),
        ]
        logs.append("Calculated confidence report")
        result = self.confidence_strategy.score("overall", factors)
        report = self.confidence_aggregator.aggregate([result])
        return report.model_dump(mode="json")

    def _validate_candidate(self, candidate: Candidate) -> list[Any]:
        results: list[Any] = []
        results.extend(CandidateSchemaValidator().validate(candidate))
        results.extend(EmailValidator().validate(candidate.emails))
        results.extend(PhoneValidator().validate(candidate.phones))
        results.extend(UrlValidator().validate(candidate.links))
        date_values = []
        for item in candidate.experience:
            date_values.extend([item.start_date, item.end_date])
        results.extend(DateValidator().validate(date_values, "experience_dates"))
        return results

    def _project(self, candidate: Candidate, config_path: Path | None) -> dict[str, Any]:
        if not config_path:
            return self.projector.project(candidate)
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            config = ProjectionConfig.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid config JSON: {exc}") from exc
        return self.projector.project(candidate, config)

    @staticmethod
    def _agreement_score(report: MergeReport) -> float:
        if not report.decisions:
            return 0.0
        duplicates = sum(1 for decision in report.decisions if len(decision.candidate_values) > 1)
        return round(duplicates / len(report.decisions), 4)

    @staticmethod
    def _duplicates_removed(report: MergeReport) -> int:
        return sum(len(decision.discarded_values) for decision in report.decisions)

    @staticmethod
    def _conflicts_resolved(report: MergeReport) -> int:
        return sum(1 for decision in report.decisions if decision.discarded_values)

    @staticmethod
    async def _save_upload(upload: UploadFile | None, directory: Path, file_name: str) -> Path | None:
        if upload is None:
            return None
        path = directory / file_name
        path.write_bytes(await upload.read())
        return path


def get_pipeline_service() -> CandidatePipelineService:
    """Provide the pipeline service for dependency injection."""

    return CandidatePipelineService()

