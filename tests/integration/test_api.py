"""
Integration tests for the FastAPI endpoints.

These tests mock the pipeline to avoid real LLM/PDF calls.
Set DOCU_FLOW_INTEGRATION=1 and provide a real PDF + API key to run live.
"""

from __future__ import annotations

import io
import json
import os
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from docu_flow.api.main import app
from docu_flow.schemas.criteria import (
    CriterionType,
    DisqualificationPower,
    EligibilityCriterion,
    ExtractedCriteria,
    ExtractionMetadata,
    ScreeningDecision,
)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _mock_extracted() -> ExtractedCriteria:
    return ExtractedCriteria(
        protocol_title="Test Protocol v1.0",
        criteria=[
            EligibilityCriterion(
                id="exc_001",
                criterion_type=CriterionType.EXCLUSION,
                text="Pregnant or lactating women.",
                source_page=5,
                disqualification_power=DisqualificationPower.VERY_HIGH,
            ),
        ],
        top_disqualifiers=[
            EligibilityCriterion(
                id="exc_001",
                criterion_type=CriterionType.EXCLUSION,
                text="Pregnant or lactating women.",
                source_page=5,
                disqualification_power=DisqualificationPower.VERY_HIGH,
            ),
        ],
        metadata=ExtractionMetadata(
            model_used="claude-sonnet-4-6",
            extraction_confidence=0.95,
            section_found=True,
        ),
    )


class TestHealthEndpoint:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestProtocolUpload:
    @patch("docu_flow.api.routes.protocols._process_protocol")
    def test_upload_pdf_accepted(self, mock_process, client):
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake content")
        resp = client.post(
            "/protocols/upload",
            files={"file": ("protocol.pdf", fake_pdf, "application/pdf")},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "protocol_id" in data
        assert data["status"] == "processing"

    def test_upload_non_pdf_rejected(self, client):
        resp = client.post(
            "/protocols/upload",
            files={"file": ("document.docx", b"fake", "application/octet-stream")},
        )
        assert resp.status_code == 400

    def test_get_unknown_protocol_404(self, client):
        resp = client.get("/protocols/does-not-exist")
        assert resp.status_code == 404


class TestScreeningEndpoint:
    def test_screen_unknown_protocol_404(self, client):
        resp = client.post(
            "/screening/screen",
            json={
                "patient_id": "p001",
                "protocol_id": "does-not-exist",
                "patient_data": {},
            },
        )
        assert resp.status_code == 404

    @patch("docu_flow.api.routes.screening.run_screening_pipeline")
    @patch("docu_flow.api.routes.screening._jobs")
    def test_screen_disqualified(self, mock_jobs, mock_pipeline, client):
        from docu_flow.schemas.criteria import ScreeningResult
        mock_jobs.__contains__ = lambda self, k: True
        mock_jobs.__getitem__ = lambda self, k: MagicMock(
            status="ready",
            extracted_criteria=_mock_extracted(),
        )
        mock_pipeline.return_value = ScreeningResult(
            patient_id="p001",
            protocol_id="proto123",
            decision=ScreeningDecision.DISQUALIFIED,
            confidence=0.98,
        )

        resp = client.post(
            "/screening/screen",
            json={
                "patient_id": "p001",
                "protocol_id": "proto123",
                "patient_data": {"is_pregnant": True},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["decision"] == "disqualified"
