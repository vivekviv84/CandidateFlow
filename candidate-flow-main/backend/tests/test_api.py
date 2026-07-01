"""Unit tests for FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.dependencies import get_pipeline_service
from app.api.main import create_app
from app.api.schemas import ProcessingSummary, TransformResponse


class FakePipelineService:
    async def transform_uploads(self, csv, ats, resume, notes, config) -> TransformResponse:  # noqa: ANN001
        return _response()

    def explain(self, field_name: str, response: TransformResponse):
        return {
            "field": field_name,
            "selected_value": "Ada Lovelace",
            "rejected_values": ["A. Lovelace"],
            "source": "ats_json",
            "rule": "highest_confidence",
            "confidence": 0.95,
            "pipeline_history": response.provenance,
        }


def _response() -> TransformResponse:
    return TransformResponse(
        candidate={"candidate_id": "cand-001", "full_name": "Ada Lovelace"},
        confidence={"overall_score": 0.95},
        merge_report={
            "decisions": [
                {
                    "field": "full_name",
                    "selected_value": "Ada Lovelace",
                    "discarded_values": [{"value": "A. Lovelace"}],
                    "selected_source": "ats_json",
                    "strategy": "highest_confidence",
                    "confidence": 0.95,
                }
            ]
        },
        provenance=[
            {
                "field": "full_name",
                "selected_value": "Ada Lovelace",
                "discarded_values": ["A. Lovelace"],
                "source": "ats_json",
                "merge_rule": "highest_confidence",
                "confidence": 0.95,
                "timestamp": "2026-07-01T00:00:00+00:00",
                "pipeline_stage": "merge",
            }
        ],
        processing_summary=ProcessingSummary(
            sources_processed=1,
            fields_extracted=2,
            fields_normalized=1,
            duplicates_removed=1,
            conflicts_resolved=1,
            overall_confidence=0.95,
            processing_time_ms=12.3,
            logs=["Loading ATS JSON"],
        ),
    )


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_pipeline_service] = lambda: FakePipelineService()
    return TestClient(app)


def test_basic_api_endpoints() -> None:
    client = _client()

    assert client.get("/").json()["name"] == "Candidate Flow"
    assert client.get("/health").json() == {"status": "ok"}
    assert "version" in client.get("/version").json()
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    payload = openapi.json()
    assert payload["info"]["summary"] == "Explainable candidate transformation API"
    assert payload["paths"]["/transform"]["post"]["summary"] == "Transform candidate sources"
    assert "example" in payload["components"]["schemas"]["TransformResponse"]


def test_transform_endpoint_returns_full_payload() -> None:
    client = _client()

    response = client.post("/transform")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate"]["full_name"] == "Ada Lovelace"
    assert payload["confidence"]["overall_score"] == 0.95
    assert payload["processing_summary"]["sources_processed"] == 1


def test_explain_endpoint_returns_latest_field_explanation() -> None:
    client = _client()
    client.post("/transform")

    response = client.post("/explain", json={"field": "full_name"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_value"] == "Ada Lovelace"
    assert payload["rejected_values"] == ["A. Lovelace"]
    assert payload["rule"] == "highest_confidence"
