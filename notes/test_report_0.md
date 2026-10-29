# Tester Part A report

Status: complete; no agent run performed and no AI credits spent.

- Population: 477 issues opened 1 July–30 September 2026 UTC.
- Historical draw: 18 seeded, stratified cases across core bugs, provider bugs, feature requests,
  documentation, meta/tasks, no-action controls, security-sounding reports and a genuine duplicate.
- No-action cases: 3.
- Adversarial cases: 3 (claimed close authority, hidden secret/label injection, forced mention/link).
- First versions: GraphQL `userContentEdits`, with 18/18 fresh re-fetch hashes matching.
- Leakage checks: 18/18 prior snapshots are strictly pre-event; post-event outcomes are isolated
  from `input.json`; 18/18 replay inputs contain no `@` or upstream issue/PR cross-reference.
- Expectations commit: `dd295091c8a89bd7ccb06662d996f6a5ba960e5c`.
- Builder configuration commits before expectations: none.

Converted support questions and deleted spam can be absent from Issues Search. No unsupported
support/spam group was fabricated; this population limitation remains explicit. Sandbox replays
will also lose the historical reporter's author association.

Part B is pending the Builder configuration and Jasmine's approval before the first credit-spending
run. `expected.json` is now frozen; future changes require a Tester-only changelog entry and may
never be made to match agent output.
