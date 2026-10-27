# Controlled one-email live test

No real outreach was sent while implementing this application. Provider transport tests use mocked responses only.

## Preconditions

- Deploy behind HTTPS, configure PostgreSQL and encryption, and register OAuth as described in PROVIDERS.md.
- Use a dedicated test account and a recipient mailbox **you own**. Never run the first live test against a company.
- Configure the relevant public board and Hunter API credentials if exercising the complete research/contact workflow.
- Do not insert test vacancies into a real company's source history. Use your own authorized test Greenhouse/Lever board with an actual email-accepting test posting if one is available. Its description must explicitly publish your owned professional test address and email application instructions. The dry-run fixtures cannot be promoted to real opportunities.

## Complete controlled workflow

1. Register a CareerOrbit account, confirm an accurate profile, upload and approve a non-sensitive test resume.
2. Connect your Gmail/Outlook account with send-only OAuth. Separately grant read access only if testing synchronization.
3. Create one campaign with company target=1, initial emails=1, daily cap=1, an appropriate current sending window, and review mode. Configure only your authorized test board.
4. Run research. Verify the exact real source URL and recipient you own. Discover/verify the source-listed address using Hunter, then generate a draft.
5. Inspect the correct recipient/company/title and attachment. Check the explicit campaign authorization statement and approve exactly this draft.
6. Start one worker. Observe pending → sending → sent. Inspect provider Sent mail and the recipient inbox. Download/open the attachment and compare it with your original file. Provider acceptance alone is not proof of inbox delivery.
7. Restart the worker and verify it does not send the original again. Verify campaign sent=1, and inspect the audit event/provider ID (Graph uses an accepted correlation ID).
8. Reply from your owned recipient mailbox. Use **Sync replies**, inspect the persisted reply and dashboard, and confirm a meaningful reply suppresses a follow-up. Reply “stop” and verify suppression too.
9. Pause the campaign. A new campaign/edit needs a new scope approval. Never increase the live test quota during this check.

If you do not have your own authorized test board/Hunter verification, the transport can be checked directly in a separate developer harness using an owned address and synthetic message/resume objects, calling `app.mail.send` with a connected test mailbox. That test exercises real MIME/OAuth transport only; it does **not** validate live job discovery, contact evidence or the full approval queue. Do not bypass application guards in a production database to make the full workflow appear tested.

## Credential errors and uncertain results

A missing or expired credential must fail visibly without a fabricated sent event. Rate limits retry conservatively. A timeout/5xx can mean the provider accepted a message: an `unknown` or stranded `sending` record needs Sent-mail reconciliation before an operator considers repair. Do not automatically replay it. Keep quotas at one and preserve all evidence.
