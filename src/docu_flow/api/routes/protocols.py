"""
/protocols endpoints

POST /protocols/upload
  Upload a protocol PDF. Triggers the extraction pipeline as a background task.
  Returns a protocol_id.

GET  /protocols/{protocol_id}
  Retrieve extracted criteria for a previously processed protocol.

DELETE /protocols/{protocol_id}
  Remove stored artifacts for a protocol.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from docu_flow.config import settings
from docu_flow.logging import log
from docu_flow.pipeline.orchestrator import run_protocol_pipeline
from docu_flow.schemas.criteria import ExtractedCriteria
from docu_flow.utils.pdf_utils import safe_filename

router = APIRouter()


class UploadResponse(BaseModel):
    protocol_id: str
    filename: str
    status: str  # "processing" | "ready" | "error"


class ProtocolStatus(BaseModel):
    protocol_id: str
    status: str
    extracted_criteria: ExtractedCriteria | None = None
    error: str | None = None


# In-memory job store (replace with Redis/DB in production)
_jobs: dict[str, ProtocolStatus] = {}


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_protocol(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Clinical trial protocol PDF"),
) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    protocol_id = str(uuid.uuid4())
    safe_name = safe_filename(file.filename or "protocol.pdf")
    dest = settings.upload_dir / f"{protocol_id}_{safe_name}"

    # Stream upload to disk
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    log.info("protocols.uploaded", protocol_id=protocol_id, filename=safe_name, size=dest.stat().st_size)

    _jobs[protocol_id] = ProtocolStatus(protocol_id=protocol_id, status="processing")
    background_tasks.add_task(_process_protocol, protocol_id, dest)

    return UploadResponse(protocol_id=protocol_id, filename=safe_name, status="processing")


@router.get("/{protocol_id}", response_model=ProtocolStatus)
async def get_protocol(protocol_id: str) -> ProtocolStatus:
    job = _jobs.get(protocol_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Protocol '{protocol_id}' not found.")
    return job


@router.delete("/{protocol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protocol(protocol_id: str) -> None:
    if protocol_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Protocol '{protocol_id}' not found.")
    del _jobs[protocol_id]
    # Remove uploaded files
    for f in settings.upload_dir.glob(f"{protocol_id}_*"):
        f.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

def _process_protocol(protocol_id: str, pdf_path: Path) -> None:
    try:
        extracted = run_protocol_pipeline(pdf_path)
        _jobs[protocol_id] = ProtocolStatus(
            protocol_id=protocol_id,
            status="ready",
            extracted_criteria=extracted,
        )
        log.info("protocols.processing_done", protocol_id=protocol_id)
    except Exception as exc:  # noqa: BLE001
        log.error("protocols.processing_failed", protocol_id=protocol_id, error=str(exc))
        _jobs[protocol_id] = ProtocolStatus(
            protocol_id=protocol_id,
            status="error",
            error=str(exc),
        )
