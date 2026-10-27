# Deployment and operations

This is a tested development application with production-oriented boundaries, not an audited production service. Review the status document before exposing it to users.

## Docker / PostgreSQL

1. Copy `.env.example` to an ignored `.env` if one does not exist. Set a random URL-safe `POSTGRES_PASSWORD` and a generated Fernet `ENCRYPTION_KEY`. Keep the same key on API and worker. Back it up separately from encrypted files.
2. Set `APP_URL`, `API_URL`, `NEXT_PUBLIC_API_URL` to deployed origins. For production use HTTPS and `PRODUCTION=true`. PostgreSQL is mandatory in production. The Python process refuses production startup without HTTPS APP_URL, encryption key and PostgreSQL.
3. Build/run: `docker compose up --build -d`. The web build embeds `NEXT_PUBLIC_API_URL`; rebuild when it changes. Compose injects the PostgreSQL URL into API/worker and shares encrypted attachment storage.
4. Put a supported HTTPS reverse proxy in front of the loopback-bound 3000 and 8000 ports. Use app/API subdomains under the same site for the session cookie. Limit uploads at the proxy to about 11 MB. Configure TLS, HSTS, request throttling and timeouts there. Do not expose PostgreSQL publicly.
5. Register the exact OAuth callbacks in your providers and store credentials in the environment's secure configuration.
6. Check API health and a real signed-in workflow. Run the controlled one-email test separately. A container health check does not certify provider credentials or application behavior.

Dockerfiles run as non-root. The API initializes the schema before the worker starts. One worker is the default. PostgreSQL row locks serialize jobs and account limits; uncertain sends reserve quota and duplicate history. SQLite is for single-worker local development only. Do not deploy multiple replicas against SQLite.

## Schema and migration

`backend/schema.sql` contains initial PostgreSQL DDL. SQLAlchemy creates the same initial tables for a new database. Schema creation is idempotent; **it does not migrate existing tables**. Review and version database migrations before changing this schema in a deployed service. Back up and test restoration before upgrades. Do not run test fixtures against production.

## Secrets and storage

- Argon2 hashes protect account passwords; random session tokens are hashed in the database, HttpOnly, SameSite=Lax, and Secure in production.
- Origin plus a custom request header protects authenticated mutations against CSRF. CORS allows only APP_URL. All tenant-owned records are checked server-side.
- Resume bytes and OAuth token blobs are encrypted using Fernet authenticated encryption. Resume SHA-256 is verified again before dispatch. Extracted text, profile, message text and audit metadata remain sensitive database data: provision encrypted volumes/database storage and access restrictions.
- A development key file is generated only outside production. Never distribute that file or use it as a production secret.
- Key rotation needs a controlled decrypt/re-encrypt migration for existing token and file blobs. Online multi-key rotation is not supplied. Keep the old key until every record has been migrated and verified.
- Client-secret rotation uses provider-supported overlap, replacing environment values and restarting API/worker. Do not log request bodies, OAuth callback query strings, authorization headers or tokens at the reverse proxy. API container disables access logs so callback codes are not logged.
- Local disk is private, not a public upload bucket. A managed object storage adapter and malware scanner are not supplied. Resume processing is limited by extension, signature, size, PDF page count and DOCX expansion size; add sandboxed parsing and malware scanning before a public upload service.

## Dispatch and recovery

The worker writes a durable `sending` marker before requesting provider dispatch. Only 429 responses are automatically retried (maximum four attempts, exponential backoff with Retry-After). Transport/5xx outcomes are ambiguous and are marked `unknown`; they are never blindly retried. This is intentionally conservative: exactly-once external delivery cannot be guaranteed across a crash with providers that lack idempotency support.

Pause prevents new worker dispatches; an in-flight request may already be accepted. Global per-user duplicate records prevent another initial contact at the same company or address. Deleted accounts intentionally delete their history. One follow-up is a separate unique, explicitly approved record; it respects global daily quota and is cancelled on meaningful replies, opt-outs or scope change.

Monitor worker liveness, `failed`, `unknown` and stranded `sending` records, schedule errors and expired credentials. Alerts should not include tokens, full resume text or message contents. Reconcile uncertain sends against provider Sent mail before any manual recovery.

## Privacy and compliance

Collect only professional details the user chooses to supply. Default product retention is until user deletion; define a legally reviewed retention period and backup expiry policy for your deployment. Account deletion removes active database records and encrypted files, but not provider mail, external logs or backups. Data export is JSON plus resume downloads; opportunity CSV is spreadsheet-safe.

Hunter deliverability verification is not lawful-basis verification. The sender must review recipient location, applicable outreach law, recruitment purpose and opt-out rules. This build does not determine jurisdiction-specific legal eligibility. Do not launch unattended global outreach without those policies. It has no tracking pixels, access-control bypasses, personal-address inference or spam-evasion features.

Before public production release, add operational email verification/password recovery, stronger distributed authentication throttling, formal migrations, monitoring, security review, backup restoration tests, comprehensive reply pagination/event subscriptions, jurisdiction-specific policy enforcement and deployment-specific privacy notices. These are concrete remaining release requirements, not features this build claims to provide.
