# Holdout-input verification

Verified before any holdout agent run.

- 10 unique historical cases, disjoint from the 18 golden cases.
- Two no-action controls are present.
- Independent GraphQL re-fetches reproduce every first-version title/body SHA-256 hash.
- Inputs contain only event-time text, creation labels/template and a dated prior snapshot.
- Every prior-snapshot issue predates its case; post-event outcomes remain reference-only.
- Replay text contains no @mention and no Apache Airflow issue/PR cross-reference.
- Expectations cover all 10 cases and were recorded before any agent run.

Machine-readable per-case checks are in `verification_results.json`.
