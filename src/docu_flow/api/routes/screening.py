"""
/screening endpoints

POST /screening/screen
  Screen a patient against a pre-processed protocol's top disqualifiers.
  Returns a ScreeningResult synchronously (fast — top-8 filter only).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from docu_flow.api.routes.protocols import _jobs
from docu_flow.logging import log
from docu_flow.pipeline.orchestrator import run_screening_pipeline
from docu_flow.schemas.criteria import ScreeningRequest, ScreeningResult

router = APIRouter()


@router.post("/screen", response_model=ScreeningResult)
async def screen_patient(request: ScreeningRequest) -> ScreeningResult:
    job = _jobs.get(request.protocol_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Protocol '{request.protocol_id}' not found.")
    if job.status == "processing":
        raise HTTPException(status_code=409, detail="Protocol is still being processed. Try again shortly.")
    if job.status == "error":
        raise HTTPException(status_code=422, detail=f"Protocol processing failed: {job.error}")
    if job.extracted_criteria is None:
        raise HTTPException(status_code=422, detail="No criteria available for this protocol.")

    log.info("screening.start", patient_id=request.patient_id, protocol_id=request.protocol_id)
    result = run_screening_pipeline(request, job.extracted_criteria)
    return result
