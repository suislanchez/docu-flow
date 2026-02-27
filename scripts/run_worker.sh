#!/usr/bin/env bash
# Start the Celery worker
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
celery -A docu_flow.worker.celery_app worker --loglevel=info --concurrency=2
