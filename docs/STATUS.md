# Capabilities, limitations and cost

This is a working, tested development release. It is not a complete implementation of every enhancement in the original product specification and must not be described as production-certified.

## Operational locally

- Persistent account/session authentication, owner-scoped access, CSRF checks and Argon2 password hashing.
- Editable structured profile, multiple encrypted PDF/DOCX original resume versions, extraction review, explicit resume approval and relevance-based selection.
- Multi-campaign preferences for categories, locations, currencies/periods, salary disclosure, targets, caps, dates and sending windows. A conservative natural-language parser produces an editable draft without authorizing sends.
- Greenhouse/Lever/Adzuna/SerpApi adapters with provenance, classification, weighted matching and deduplication. API calls require network access; paid providers require keys.
- Hunter address discovery/verification adapters, manually sourced contacts and direct extraction of published professional emails. No inferred address patterns.
- Grounded personalized drafts, attachment integrity/MIME checks, exact-scope approvals, queue, quota/duplicate/suppression enforcement and durable dispatch state.
- Implemented Gmail/Outlook OAuth and real provider requests, encrypted tokens and refresh. These remain credential-gated; no live mailbox authorization or send was tested.
- Separately authorized reply synchronization, persisted categories, notifications, opt-out suppression and one approved follow-up with durable scheduling/retries.
- Dashboard from real stored events, search, CSV, application pipeline, user-recorded calendar, privacy export/deletion, audit history and expiry-bounded recurring research.
- Keyword-based career-fit gaps and suspicious payment-language flags. These are advisory, not authenticity/eligibility guarantees.
- PostgreSQL deployment configuration and initial schema; SQLite for local development.

## Deliberate boundaries and remaining work

- Autopilot dispatches **exact approved recipients and drafts**; newly discovered contacts require another review. Fully autonomous criteria-wide research-to-send authorization is not implemented.
- Public board discovery needs user-supplied company slugs. Broad discovery requires Adzuna or another configured search service. The free fallback does not autonomously enumerate all companies worldwide.
- ATS portal submission is manual and user-reported. No third-party portal form is falsely reported submitted.
- Gmail follow-ups use original thread IDs. Graph follow-ups currently use a new `Re:` message; native reply actions, Sent Item reconciliation and robust bounce correlation remain work.
- Inbox synchronization is bounded to the latest 100 messages (Gmail query: last 30 days). No continuous webhook subscription or complete pagination. Read consent and explicit sync are required; the worker does not periodically read the mailbox.
- Follow-ups require separate explicit approval. Only one is allowed, and meaningful/unclassified replies suppress it. Incoming replies not yet synchronized cannot suppress a send; sync before authorizing follow-ups.
- English email writing only. No unsupported multilingual promise.
- Frankfurter daily rates support same-period currency comparisons when available. Original values and the rate source/date are retained. Hourly/monthly/annual periods are never inferred or interconverted. ATS resume rewriting and OCR are not implemented.
- Ranking is transparent keyword scoring; comprehensive natural-language eligibility extraction, institution-page crawling, legal-domain entity resolution and jurisdiction-specific outreach policy enforcement are not implemented.
- Target industry distributions, company-size filters, startup/lab classifications, learning from feedback, native Excel files, statistical resume-effectiveness analytics and actual monetary billing synchronization remain enhancements. No fabricated data fills these gaps.
- Country suggestions cover common markets; arbitrary names can be entered. No complete global country/city database.
- Account email verification/password reset, a public SaaS hardened auth gateway, formal schema migrations and operational secret rotation tooling are not supplied. See the deployment release requirements.
- Contact validation confirms deliverability through Hunter; manual publication/permission review is still required. No system can infer legal consent solely from a provider's score.

## Cost

No LLM is required for the default workflow. Greenhouse/Lever public reads avoid paid discovery credits, subject to terms and rate limits. Adzuna, Hunter and SerpApi plans determine their own fees. A configurable campaign monthly discovery-call cap defaults to 300 and is measured across recorded account usage; it is not a monetary spending guarantee. Hunter verification/search and optional LLM requests need provider-side spending limits too. The dashboard reports recorded calls, not invented prices. Apply billing caps/alerts at every paid provider and hosting platform.

Repeated research deduplicates records. It still consumes provider requests. This version does not implement a shared cross-account research cache. Limit board lists and schedule frequency. Keep PostgreSQL and the single worker appropriately sized rather than provisioning unnecessary infrastructure.

## Verification record

See `docs/VALIDATION.md` for commands and actual outcomes from this environment. Mocked success is never live-provider evidence. No interview, delivery or recruiter-response statistics were invented.
