# Provider configuration

Configure values in `.env` for local use or a deployment secret manager. All providers are called server-side. Never put credentials in `NEXT_PUBLIC_*`. Integration tests mock responses; real provider credentials are required to validate your tenant and permissions.

## Gmail OAuth

1. Create a Google Cloud project, enable the Gmail API, and configure the OAuth consent screen.
2. Create a **Web application** OAuth client. Set `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` securely.
3. Register exactly `API_URL/api/oauth/gmail/callback` (local API_URL defaults to `http://localhost:8000`). Use the deployed HTTPS API origin for a public deployment.
4. Add authorized testing users while the consent app is in testing. External production apps using Gmail scopes may require Google verification/security assessment. Testing-mode refresh tokens may expire after seven days depending on scopes and app status.
5. **Connect to send** requests `openid email gmail.send`. **Enable reply reading** separately requests `gmail.readonly` in addition. Read access is optional.
6. PKCE, one-use expiring state, the signed-in session and exact callback URL protect the flow. Tokens are encrypted server-side and refreshed when needed.

Google API domains: `accounts.google.com`, `oauth2.googleapis.com`, `www.googleapis.com`, `gmail.googleapis.com`.

## Microsoft Outlook / Microsoft 365

1. Register an application in Microsoft Entra ID with the account types your users require (the adapter uses the `common` authority).
2. Register a Web redirect URI exactly `API_URL/api/oauth/outlook/callback`.
3. Create and securely store `OUTLOOK_CLIENT_ID` and `OUTLOOK_CLIENT_SECRET`.
4. Configure delegated `User.Read`, `Mail.Send`, `openid`, `email`, `offline_access`. Add delegated `Mail.Read` only for separately authorized reply monitoring. Tenant policy may require administrator consent.
5. Connect through CareerOrbit. Expired/invalid refresh permissions require reconnection. Rotate client secrets before expiry.

Domains: `login.microsoftonline.com`, `graph.microsoft.com`. Graph `sendMail` returns 202 with no message ID. CareerOrbit stores `accepted:<job-id>` and a custom correlation header, not a fabricated Microsoft message ID. Graph follow-ups are separate `Re:` messages; native Outlook conversation threading and comprehensive Sent Items reconciliation are not yet implemented.

## Discovery

| Provider | Setup | Actual behavior |
|---|---|---|
| Greenhouse | Company board slugs in campaign sources | Public Job Board API; official active board listings; portal unless explicit email-application instructions are published |
| Lever | Company board slugs | Public Postings API; official listings; same portal boundary |
| Adzuna | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, supported two-letter market codes | Search query/location, first 50 results per market; original published salaries only; predicted salaries excluded |
| Hunter | `HUNTER_API_KEY` | Domain Search and Email Verifier; only `valid` status permits dispatch |
| SerpApi | `SERPAPI_API_KEY`, `sources.serpapi=["search"]` using API | Google Jobs search leads; kept **E/unverified**, not auto-promoted to active vacancies |

Board slugs are identifiers from a company's actual official board URL, not full URLs. A nonexistent slug returns an explicit provider error. A board slug is displayed as company identity when the provider response does not include its legal name. Verify the source before outreach.

Frankfurter provides daily reference FX rates without a key at `api.frankfurter.dev`. It is optional: unavailable rates leave comparison unverified; the original amounts are preserved.

Provider domains: `boards-api.greenhouse.io`, `api.lever.co`, `api.adzuna.com`, `api.hunter.io`, `serpapi.com`. Public APIs can be used without crawling arbitrary websites. Institution/custom-page crawling is not implemented; use official portal links. Terms, commercial plans, country coverage and quotas still apply.

## Optional LLM

Set `LLM_BASE_URL` to an HTTPS OpenAI-compatible endpoint, `LLM_API_KEY` and `LLM_MODEL`. Allow that exact provider domain in the environment network policy. The adapter accepts structured sentence/skill indexes, validates them, and selects only supplied opportunity excerpts and resume-backed skills. Invalid indexes fail closed. Without an LLM, deterministic extractive personalization is operational and incurs no LLM bill.

Resume files, contact addresses and mailbox tokens are not sent to the LLM. The selection request contains role title, source sentences and matching skill labels. Decide whether sharing those fields fits your organization's policy. External source text is never given tools or authority.

## Cloud onboarding

The environment draft stores required API domains but does not apply network policy immediately. Review/save environment settings and publish when appropriate. The initial live Greenhouse and Lever checks returned proxy `403 Forbidden`; successful mocked tests do not remove that blocker. Add only domains required for configured providers. No provider credentials were present during this build; do not paste secrets in chat.
