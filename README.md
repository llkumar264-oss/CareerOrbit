# CareerOrbit

A working Next.js + FastAPI career workspace with persistent profiles, encrypted resume attachments, API-backed opportunity discovery, transparent matching, campaign approval, OAuth mail connectors, durable dispatch, reply synchronization and one explicitly approved follow-up.

**Release status: development build, not yet certified for production.** Real Gmail/Outlook and paid discovery need your own provider registrations and credentials. No email has been sent during development. Read [capabilities and limitations](docs/STATUS.md) before deployment.

## Quick start on another computer

Download and extract the source ZIP. Start Docker Desktop, then double-click `START-WINDOWS.bat` on Windows, or run `bash START-MAC-LINUX.sh` on Mac/Linux. The launcher creates private local configuration, builds the app and starts PostgreSQL, API, worker and frontend. The first launch needs internet access and several minutes. See [START-HERE.txt](START-HERE.txt) for Hindi instructions and Windows script-unblocking guidance.

## Run locally

Requires Python 3.12+, Node 24, npm. Docker is optional for local SQLite and required for the supplied PostgreSQL deployment.

```bash
cd /workspace/CareerOrbit
python -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
npm ci --prefix frontend --cache /workspace/.npm-cache
npm run build --prefix frontend
# Optional: copy .env.example to .env and configure providers securely.
./scripts/start.sh
```

The supervisor starts the API on port 8000, web app on 3000, and a single durable worker. Logs are in `storage/logs/`. Use the environment's supported application access mechanism; these ports are local development services. Stop the supervisor to stop its children. Do not run more than one worker with SQLite. Existing isolated checkouts are sufficient; do not create a worktree for ordinary tasks.

For hot reload, run in three terminals from this directory:

```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --no-access-log
PYTHONPATH=backend .venv/bin/python -m app.worker
npm run dev --prefix frontend
```

The first API startup creates the schema. SQLite development data is in `careerorbit.db`; resume files and a development encryption key are under ignored `storage/`. Preserve that key or the existing attachments and OAuth tokens become unreadable. Never commit `.env`, storage, keys, database dumps or tokens.

## Verify

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests -q
npm run typecheck --prefix frontend
npm run build --prefix frontend
.venv/bin/python scripts/dry_run.py > /tmp/careerorbit-dry-run.json
# With API and web already running, and Chromium installed:
CHROMIUM_PATH=/usr/bin/chromium frontend/node_modules/.bin/playwright test --config frontend/playwright.config.ts
```

The dry run contains exactly **100 explicitly synthetic opportunities**, no network calls and no sends. It never inserts synthetic leads into live data. Backend provider calls are mocked in tests, including successful sends, expired tokens, rate limits and outages. Browser tests use real local HTTP/database flows on desktop and mobile.

For PostgreSQL, use a disposable database whose name ends in `_test`:

```bash
TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST/careerorbit_test' PYTHONPATH=backend .venv/bin/pytest backend/tests -q
```

Tests **drop and recreate the target schema**. Never point them at an application database. Use secret environment injection rather than placing a real password in shell history.

## Repository

```text
backend/
  app/
    config.py        typed runtime configuration
    db.py            sessions, SQLite/PostgreSQL initialization
    models.py        persistent entities and uniqueness constraints
    schemas.py       request validation and campaign constraints
    security.py      sessions, Argon2 passwords, encryption, CSRF
    providers.py     Greenhouse, Lever, Adzuna, SerpApi, Hunter
    matching.py      explained weighted scores and exclusions
    llm.py           optional structured evidence-selection adapter
    outreach.py      grounded writing, approval hashes, attachment checks
    mail.py          OAuth PKCE, refresh, MIME, Gmail/Graph, reply reading
    worker.py        durable dispatch, scheduling, retry and follow-up processing
    main.py          REST API; OpenAPI at /docs
  tests/             functional and mocked provider tests
  schema.sql         initial PostgreSQL DDL generated from the models
  requirements.lock  exact installed Python dependency versions
frontend/
  app/               responsive authenticated workspace and forms
  lib/api.ts         credentialed requests and safe source links
  e2e/               desktop/mobile browser workflow
  package-lock.json  frozen npm dependency graph
scripts/             repeatable installation, startup, 100-record dry run
docs/                user, deployment, OAuth, architecture and status guides
compose.yaml         PostgreSQL, API, durable worker and frontend
.env.example         configuration names; no credential values
```

## Guides

- [Using CareerOrbit](docs/USER_GUIDE.md)
- [OAuth and research API setup](docs/PROVIDERS.md)
- [Deployment and security](docs/DEPLOYMENT.md)
- [Architecture and data model](docs/ARCHITECTURE.md)
- [Implemented capabilities, costs and limitations](docs/STATUS.md)
- [Controlled live-email test](docs/LIVE_TEST.md)

A campaign target is a ceiling and a research objective, not a promise of enough eligible matches. Provider acceptance means **sent**, not delivered, read, an interview or a submitted portal application.
