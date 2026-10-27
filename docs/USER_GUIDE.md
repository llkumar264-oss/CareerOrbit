# User guide

1. Create an account with a professional email and a password of at least 12 characters. This is CareerOrbit authentication; never enter a Gmail/Outlook password.
2. Open **Profile**. Add name, skills, work authorization, availability, education, coursework, experience, projects and career interests. Confirm accuracy. Saving changes pauses existing campaigns and revokes old approvals.
3. Upload PDF or DOCX resumes under **Resumes**. Read the extracted text, correct your profile separately, and approve the original file. Extraction is text-first; scanned PDFs need OCR externally. Multiple versions are supported. Files are never modified automatically.
4. Create a campaign (optionally paste an instruction and extract editable preferences): role keywords, opportunity categories, countries/cities, work arrangement, original salary currency/frequency, company and email targets, daily limits, timezone, sending hours, dates and exclusions. The default is draft only and 15 messages/day. The country picker includes common markets; arbitrary locations can be entered.
5. Supply real Greenhouse/Lever company board slugs or configured Adzuna market codes. Research retrieves real source data. Adzuna supports broader keyword/location discovery without supplying each company. Paid services need the server configuration in the provider guide. No crawler bypasses access controls.
6. Open **Opportunities**, select the campaign, and run research. Source URLs, category, score and exclusions are retained. Click a score to inspect its components. Career-fit analysis identifies keyword gaps and suspicious payment language; it cannot certify legitimacy.
7. Follow the official application method. Portal-only listings remain portal applications. Open the official link and submit there yourself, then record `portal submitted`. CareerOrbit does not submit ATS forms or claim an email is a portal application.
8. For listings explicitly inviting email applications, discover addresses published in the source or add a professional contact with its publication URL. Hunter checks deliverability. Review the source and recruiting purpose; a valid mailbox alone is not permission to contact. Do not add private/personal contacts.
9. Generate a draft. The original approved resume with the most matching skills is selected automatically. Drafts quote opportunity evidence and use only skills present in both the profile and resume. Review all claims, names, subjects, recipients and the attachment. Editing revokes campaign approval.
10. Configure Gmail or Outlook under **Connections**. Sending and optional mailbox reading require separate consent. An unconfigured provider produces an explicit error, never a fake connection or send.
11. Set the campaign to review mode, select exact drafts, select the sending mailbox, and check the explicit authorization statement. The queue dispatches only these approved recipients, messages and attachments within the limits. The current autopilot option also uses this exact-recipient boundary; new leads need new approval.
12. Pause from the campaign card at any time. Queued messages stop at the next worker check. An HTTP request already submitted to a provider cannot be recalled. Resume preserves valid scope; changing the scope requires a fresh approval.
13. Sync replies after granting read consent. Unsubscribe/bounce creates suppression. A meaningful or unclassified reply prevents follow-ups. After the configured waiting period (8 days default), review and explicitly approve one suggested follow-up. Only one follow-up is allowed. It is queued, respects the daily cap, and rechecks replies before dispatch.
14. Use **Applications** for pipeline statuses and interview dates. These are explicitly user-reported. Replies and sends are real stored provider events. Calendar lists actual recorded interviews and published deadlines.
15. Configure recurring research under **Connections** for the selected campaign, choosing daily/weekly frequency and expiry. Research deduplicates source IDs, updates evidence, and never authorizes new recipients by itself.
16. Export opportunities to CSV (Excel-compatible) or your account to JSON. Use **Privacy & audit** to inspect decisions or permanently delete the account. Revoke provider grants and delete provider Sent mail separately if desired.

## Queue outcomes

- `pending`: approved, waiting for a sending window, quota or transient retry.
- `sending`: durable dispatch marker written. A crash here requires reconciliation.
- `sent`: provider accepted the request; not proof of delivery or reading.
- `failed`: precondition or explicit provider rejection. Diagnose and reapprove where supported.
- `unknown`: provider might have accepted it; automatic retries are disabled to prevent duplicates.
- Follow-up `cancelled`: a reply, suppression or scope change removed authorization.

For `unknown` or stranded `sending`, pause the campaign and inspect the provider's Sent mail. There is deliberately no blind “retry anyway” button. An operator must reconcile provider evidence before any database repair. Preserve the audit log. Never reset a job merely to reach a target.
