#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p storage/logs
export PYTHONPATH=backend
# Initialize once before launching concurrent API and worker processes.
.venv/bin/python -c 'from app.config import validate_runtime; from app.security import cipher; from app.main import Base, engine; validate_runtime(); cipher(); Base.metadata.create_all(engine)'
# Run this supervisor in the foreground; stopping it terminates only its children.
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log >storage/logs/api.log 2>&1 &
api_pid=$!
.venv/bin/python -m app.worker >storage/logs/worker.log 2>&1 &
worker_pid=$!
node frontend/node_modules/next/dist/bin/next start frontend --hostname 0.0.0.0 >storage/logs/web.log 2>&1 &
web_pid=$!
cleanup() { kill "$api_pid" "$worker_pid" "$web_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
for attempt in {1..30}; do
  if curl -fsS http://localhost:8000/api/health >/dev/null 2>&1 && curl -fsS http://localhost:3000/ >/dev/null 2>&1; then
    echo 'CareerOrbit API, worker and frontend started. Logs: storage/logs/'
    wait -n "$api_pid" "$worker_pid" "$web_pid"
    exit 1
  fi
  sleep 1
done
echo 'Startup failed. Inspect storage/logs/' >&2
exit 1
