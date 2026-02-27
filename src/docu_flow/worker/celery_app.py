"""
Celery application — used for long-running protocol processing jobs.

The FastAPI background task approach works for small loads.
For production scale, submit jobs via Celery tasks instead.
"""

from celery import Celery

from docu_flow.config import settings

celery_app = Celery(
    "docu_flow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["docu_flow.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,               # don't ack until task completes
    worker_prefetch_multiplier=1,      # process one task at a time per worker
)
