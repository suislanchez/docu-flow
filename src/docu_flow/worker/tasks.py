"""Celery tasks for async protocol processing."""

from __future__ import annotations

from pathlib import Path

from docu_flow.logging import configure_logging, log
from docu_flow.pipeline.orchestrator import run_protocol_pipeline
from docu_flow.worker.celery_app import celery_app

configure_logging()


@celery_app.task(bind=True, name="process_protocol", max_retries=2)
def process_protocol(self, protocol_id: str, pdf_path: str) -> dict:  # type: ignore[override]
    """
    Process a protocol PDF and return serialised ExtractedCriteria.

    Args:
        protocol_id: Stable identifier for this protocol job.
        pdf_path:    Absolute path to the uploaded PDF.

    Returns:
        dict: Serialised ExtractedCriteria (JSON-compatible).
    """
    log.info("task.process_protocol.start", protocol_id=protocol_id, pdf=pdf_path)
    try:
        extracted = run_protocol_pipeline(Path(pdf_path))
        result = extracted.model_dump(mode="json")
        log.info("task.process_protocol.done", protocol_id=protocol_id)
        return {"status": "ready", "protocol_id": protocol_id, "data": result}
    except Exception as exc:  # noqa: BLE001
        log.error("task.process_protocol.error", protocol_id=protocol_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30) from exc
