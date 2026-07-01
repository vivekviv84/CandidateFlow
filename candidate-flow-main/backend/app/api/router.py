"""FastAPI router for Candidate Flow."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile

from app.api.dependencies import APP_VERSION, CandidatePipelineService, get_pipeline_service
from app.api.schemas import (
    ExplainRequest,
    ExplainResponse,
    HealthResponse,
    ProjectInfo,
    TRANSFORM_RESPONSE_EXAMPLE,
    TransformResponse,
    VersionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()
_LAST_TRANSFORM: TransformResponse | None = None


@router.get(
    "/",
    response_model=ProjectInfo,
    tags=["system"],
    summary="Project information",
    description="Return project name, description, and API version for the Candidate Flow service.",
)
def project_info() -> ProjectInfo:
    """Return project information."""

    return ProjectInfo(
        name="Candidate Flow",
        description="Explainable multi-source candidate data transformation engine.",
        version=APP_VERSION,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health check",
    description="Return a lightweight health response for uptime checks.",
)
def health() -> HealthResponse:
    """Return service health."""

    return HealthResponse()


@router.get(
    "/version",
    response_model=VersionResponse,
    tags=["system"],
    summary="API version",
    description="Return the current Candidate Flow API version.",
)
def version() -> VersionResponse:
    """Return application version."""

    return VersionResponse(version=APP_VERSION)


@router.post(
    "/transform",
    response_model=TransformResponse,
    tags=["pipeline"],
    summary="Transform candidate sources",
    description=(
        "Accept CSV, ATS JSON, resume PDF, notes TXT, and optional projection config JSON. "
        "Runs the complete approved pipeline and returns candidate output, confidence, "
        "merge report, provenance, and processing summary."
    ),
    responses={
        200: {
            "description": "Successful transformation.",
            "content": {"application/json": {"example": TRANSFORM_RESPONSE_EXAMPLE}},
        },
        400: {
            "description": "Invalid input or transformation failure.",
            "content": {"application/json": {"example": {"detail": "At least one input source is required."}}},
        },
        500: {"description": "Runtime upload parser dependency is missing."},
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "example": {
                        "csv": "recruiter.csv",
                        "ats": "ats.json",
                        "resume": "resume.pdf",
                        "notes": "notes.txt",
                        "config": "projection-config.json",
                    }
                }
            }
        }
    },
)
async def transform(
    request: Request,
    service: CandidatePipelineService = Depends(get_pipeline_service),
) -> TransformResponse:
    """Transform uploaded candidate sources into canonical output."""

    global _LAST_TRANSFORM
    try:
        uploads = await _uploads_from_request(request)
        response = await service.transform_uploads(
            uploads.get("csv"),
            uploads.get("ats"),
            uploads.get("resume"),
            uploads.get("notes"),
            uploads.get("config"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Transform failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _LAST_TRANSFORM = response
    return response


@router.post(
    "/explain",
    response_model=ExplainResponse,
    tags=["pipeline"],
    summary="Explain a field decision",
    description=(
        "Explain the latest transformation decision for a field. The response includes selected value, "
        "rejected values, source, rule, confidence, and provenance history."
    ),
    responses={
        200: {
            "description": "Field explanation returned.",
            "content": {
                "application/json": {
                    "example": {
                        "field": "full_name",
                        "selected_value": "Ada Lovelace",
                        "rejected_values": ["A. Lovelace"],
                        "source": "ats_json",
                        "rule": "highest_confidence_then_source_priority_then_timestamp_then_stable_value",
                        "confidence": 0.95,
                        "pipeline_history": [{"pipeline_stage": "merge", "field": "full_name"}],
                    }
                }
            },
        },
        404: {
            "description": "No prior transform result is available.",
            "content": {
                "application/json": {"example": {"detail": "No transform result is available to explain."}}
            },
        },
    },
)
def explain(
    request: ExplainRequest,
    service: CandidatePipelineService = Depends(get_pipeline_service),
) -> ExplainResponse:
    """Explain the latest transform decision for one field."""

    if _LAST_TRANSFORM is None:
        raise HTTPException(status_code=404, detail="No transform result is available to explain.")
    return service.explain(request.field, _LAST_TRANSFORM)


async def _uploads_from_request(request: Request) -> dict[str, UploadFile | None]:
    """Return supported uploads from a multipart request."""

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        return {"csv": None, "ats": None, "resume": None, "notes": None, "config": None}

    try:
        form = await request.form()
    except AssertionError as exc:
        raise HTTPException(status_code=500, detail="python-multipart is required for file uploads.") from exc

    from starlette.datastructures import UploadFile as StarletteUploadFile

    uploads: dict[str, UploadFile | None] = {}
    for field in ("csv", "ats", "resume", "notes", "config"):
        value: Any = form.get(field)
        uploads[field] = value if isinstance(value, StarletteUploadFile) else None
    return uploads
