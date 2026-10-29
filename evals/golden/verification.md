# Golden-input verification

Verified on 29 October 2026 UTC before any agent run.

- 18 unique historical cases; all creation timestamps are within 1 July–30 September 2026 UTC.
- Each source was freshly re-fetched through GraphQL `userContentEdits`; all 18 reconstructed first-version title/body hashes match `source.json`.
- For edited bodies, the oldest saved version has `editedAt == issue.createdAt`; unedited bodies have an empty edit history.
- Every `input.json` contains only event-time text, creation labels/template, and a dated prior-issue snapshot reference. Post-event outcomes are isolated in `reference.json` and marked `not_agent_input`.
- Every prior snapshot entry was created strictly before its case and contains only title and labels reconstructed as of that cutoff; no collection-time labels are present.
- Replay text contains no `@` and no Apache Airflow issue/PR cross-reference. The unsanitised source URL and hash remain only in committed evidence files.
- Three no-action historical cases and three constructed adversarial cases are present. Expectations cover every case, limit labels to three, and allow at most one comment.
- No workflow or model run has occurred; `actual/` and run logs do not yet exist.

Per-case machine-readable checks are in `verification_results.json`; fresh responses are in `raw/verification_graphql/`.

Known limitation: replay issues will be authored by Jasmine rather than the historical reporters, so author association cannot be reproduced.
