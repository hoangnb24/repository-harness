# Client Update — <story id>

> **No secrets, no PII.** Do not paste credentials, access tokens,
> personal identifiers, or anything that should not appear in a
> retained channel log.

## Channel

<channel placeholder — examples only: chat tool, email, ticketing
inbox, or whatever distribution surface the org runs. Pick one channel
per update; do not cross-post>

## Recipients

<distribution list, channel name, or named recipients>

## Subject

<one-line subject — include story id, e.g. "US-NNN release ready for UAT">

## Body

<two-to-five sentence summary of what shipped, what to look for in the
release, and the next-action ask if any>

Examples of next-action asks:

- "Please confirm UAT acceptance by <date> per `01-uat-plan.md`."
- "No action required — release notes attached. Reference: `US-NNN.REQ-001`."
- "Bug found in <area>; rollback planned for <date>; update to follow."

## REQ References (optional)

If the update calls out specific delivered behavior, cite the REQ
token so the client can grep back to the story:

- `US-NNN.REQ-001` — <one-line restatement of what shipped>.

## Sent

- Date: YYYY-MM-DD
- Time: HH:MM (timezone)
- Sent by: <name or automation source>
- Channel log link (if applicable): <permalink to message>
