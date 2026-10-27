#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
if command -v curl >/dev/null && curl -fsS --max-time 3 http://localhost:8000/api/health 2>/dev/null | grep -q 'live_sending'; then
  if curl -fsS --max-time 3 http://localhost:3000/ 2>/dev/null | grep -q 'CareerOrbit'; then
    echo 'CareerOrbit is already running on localhost:3000.'
    exit 0
  fi
fi
if ! command -v docker >/dev/null; then
  echo 'Install and start Docker Desktop (or Docker Engine with Compose), then run this script again.' >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo 'Start Docker Desktop or Docker Engine, then run this script again.' >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo 'Docker Compose is missing. Update Docker Desktop or install the Docker Compose plugin.' >&2
  exit 1
fi
if ! command -v curl >/dev/null; then
  echo 'Install curl to run the startup readiness check, then try again.' >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  docker run --rm -i --user "$(id -u):$(id -g)" --mount "type=bind,source=$project_dir,target=/project" --workdir /project python:3.12-slim python - <<'PY'
from pathlib import Path
import base64, os, secrets
keyfile = Path('storage/.encryption-key')
key = keyfile.read_text().strip() if keyfile.exists() else base64.urlsafe_b64encode(os.urandom(32)).decode()
template = Path('.env.example').read_text()
template = template.replace('ENCRYPTION_KEY=\n', 'ENCRYPTION_KEY=' + key + '\n').replace('POSTGRES_PASSWORD=\n', 'POSTGRES_PASSWORD=' + secrets.token_urlsafe(32) + '\n')
with Path('.env').open('x') as stream:
    stream.write(template)
Path('.env').chmod(0o600)
print('Created local configuration.')
PY
fi
echo 'Building and starting CareerOrbit. First launch may take several minutes.'
docker compose up --build -d
for attempt in {1..45}; do
  if curl -fsS --max-time 3 http://localhost:8000/api/health >/dev/null 2>&1 && curl -fsS --max-time 3 http://localhost:3000/ >/dev/null 2>&1; then
    echo 'CareerOrbit is ready at localhost:3000. Stop it with: docker compose stop'
    if command -v open >/dev/null; then open http://localhost:3000; fi
    exit 0
  fi
  sleep 2
done
echo 'Startup has not completed. Inspect: docker compose logs --tail=50' >&2
exit 1
