#!/usr/bin/env bash
set -euo pipefail
cd /workspace/CareerOrbit
python -m venv .venv
.venv/bin/python -m pip install --cache-dir /workspace/.pip-cache -r backend/requirements.lock
.venv/bin/python scripts/init_env.py
npm ci --prefix frontend --cache /workspace/.npm-cache --no-audit --no-fund
npm run build --prefix frontend
