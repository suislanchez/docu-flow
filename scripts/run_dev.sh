#!/usr/bin/env bash
# Start the API server in development mode (requires .env to be set)
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
uvicorn docu_flow.api.main:app --host 0.0.0.0 --port 8000 --reload
