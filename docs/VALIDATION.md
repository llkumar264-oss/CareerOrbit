# Validation record — 2026-10-27

| Check | Outcome |
|---|---|
| Backend functional/mocked-provider suite, SQLite | **28 passed** |
| Same suite, disposable PostgreSQL 17 database | **28 passed** |
| Frontend production build | Passed, including TypeScript compilation |
| Standalone TypeScript check | Passed |
| Playwright desktop and mobile on local processes | Passed; registration, confirmed profile, campaign creation, pause, persistence, no horizontal viewport overflow |
| Playwright desktop and mobile on Docker/PostgreSQL stack | **2 passed**; real HTTP and persistent database flows |
| Docker API, worker and web image builds | Passed |
| Docker Compose startup | PostgreSQL/API healthy; worker and frontend started; browser functional checks passed |
| Frozen dependency reinstall and build | Passed with writable workspace caches |
| npm production-dependency audit | 0 reported vulnerabilities at validation time; not a full security audit |
| Synthetic dry run | Exactly 100 labeled synthetic companies; 80 eligible after geography filtering; zero network calls, zero sends |
| Current local startup | API health status=ok; frontend HTTP 200; worker startup confirmed |
| Live Greenhouse / Lever read | **Blocked**: environment egress proxy returned 403 Forbidden for provider domains |
| Live OAuth, token exchange and real email delivery | **Not run**: no configured provider credentials or authorized mailbox |
| Live paid research/contact services and FX endpoint | **Not validated**; adapters tested with mocked provider responses |
| Environment draft persistence | Confirmed saved: install_script, start_skill, provider domains, client-ID variable requirements and optional personal provider-secret requirements |
| Publication / restoration in a fresh task | **Not performed**; publication belongs to the user/platform |

The backend suite includes a complete mocked-provider workflow: register → confirm profile → upload/parse/approve resume → OAuth callback/state validation → discover opportunity → verify contact → generate draft → approve exact scope → dispatch → persist provider acceptance → synchronize interview-category reply → export/delete. Only provider boundaries are mocked. An interview-category email does not manufacture an interview date or a portal submission.

Other checks cover attachments, tampering, ineligible/expired records, wrong-company contacts, placeholder rejection, signature-bound approval invalidation, daily caps, transient/ambiguous failures, suppression, one follow-up and cancellation after replies, invalid OAuth state, token refresh, provider outages and structured LLM output validation.

One non-failing Starlette test-client deprecation warning remains. The installed FastAPI/Starlette test client advises an eventual httpx2 migration. Browser tests use installed system Chromium because downloading another browser was blocked; no browser download is needed for this environment.

Docker's initial dependency build could not resolve the execution environment's proxy. Validation used a temporary build override with the existing proxy hostname resolution, existing proxy variables and public CA bundle supplied as a BuildKit secret. TLS verification remained enabled. Non-root source ownership was corrected in the Dockerfile. Standard deployment uses the network/trust configuration appropriate to its Docker host. Local cloud development does not depend on Docker images or running containers surviving publication.

The Docker stack was stopped after testing, preserving its volumes. The documented local API, worker and frontend were restarted. Disposable PostgreSQL test containers and generated browser-test accounts were cleaned up. No real company outreach, live test emails or recruiter response statistics were generated.
