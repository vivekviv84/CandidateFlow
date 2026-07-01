"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.dependencies import APP_VERSION
from app.api.router import router

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Candidate Flow API",
        summary="Explainable candidate transformation API",
        description=(
            "Candidate Flow accepts recruiter CSV, ATS JSON, resume PDF, notes TXT, and optional "
            "projection configuration inputs. It returns a canonical candidate profile plus merge "
            "decisions, provenance, confidence details, and a processing summary for dashboard review."
        ),
        version=APP_VERSION,
        contact={"name": "Candidate Flow Engineering"},
        license_info={"name": "Internship Assignment"},
        openapi_tags=[
            {"name": "system", "description": "Health, version, and project metadata."},
            {
                "name": "pipeline",
                "description": "Candidate transformation, merge reporting, confidence visualization, and explanations.",
            },
        ],
    )
    app.include_router(router)
    return app


app = create_app()
