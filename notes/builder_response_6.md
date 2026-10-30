# Builder response 6: general improvement after Round 5

## Frozen baseline

Round 5 remains unchanged at commit `286fa092f4c6453365efaf502629ecdfb0469653`.
It produced decisions for 11/21 cases; 1/11 decided cases matched the complete frozen result, while
10/21 were not evaluated because concurrent dispatch encountered Copilot 429 responses. The
committed Round 5 actuals and proposal score remain the before-improvement evidence. This round does
not alter `evals/golden/expected.json` or any Round 5 actual output.

## Bug fix: successful deterministic detection

Round 5 `airflow-72278` showed that `validate_safe_outputs.py` accepted the correct `noop`, but gh-aw's
later `Conclude threat detection` step failed because
`/tmp/gh-aw/threat-detection/detection_result.json` did not exist. The validator now writes gh-aw's
structured safe verdict after, and only after, deterministic validation succeeds. The workflow
passes that exact output path. A regression invokes the CLI with a no-op payload and verifies both a
zero exit code and the five expected safe-verdict fields. Invalid output still exits before writing a
safe verdict, so the gate remains fail closed.

## One general instruction improvement

The change is based on Airflow's general taxonomy, not individual golden cases. The pinned triage
process distinguishes core and providers, names detailed core areas, and requires `area:providers`
with `provider:x` ([lines 173–199](https://github.com/apache/airflow/blob/270b2abfc258c512a0b931af425904321360d043/ISSUE_TRIAGE_PROCESS.rst#L173-L199),
[lines 271–279](https://github.com/apache/airflow/blob/270b2abfc258c512a0b931af425904321360d043/ISSUE_TRIAGE_PROCESS.rst#L271-L279)).
`AGENTS.md` maps those concepts only to labels in `scripts/label_policy.json`, prefers a supported
specific area over generic core, and forbids provider labels without `area:providers`.

The skill now requires clear title/body evidence for every kind, area and provider; ambiguity means
no label rather than a default `area:core`. It also permits comments only by the existing template
IDs and requires the final body to match the wrapper-rendered bytes, never model-authored free text.
The deterministic label and comment validators remain the enforcing boundary.

## Credit-free verification

- `python -m unittest discover -s scripts/tests -v`: 31/31 passed.
- `python -m unittest discover -s evals/golden/harness -p 'test_*.py' -v`: 8/8 passed.
- Pinned gh-aw v1.0.1 strict compilation succeeded and regenerated
  `.github/workflows/issue-triage.lock.yml`; the existing compiler warning about its own unknown
  `detection_agentic_execution` step reference remains. A repeat strict compile produced the same
  SHA-256 `0ad4bdd3da9f9c0bd9266a1f30ff88eaa2c956e6a2000c657f7ad288e3dfb6cf`.
- No workflow or model run was triggered, and `DESIGN.md` was not edited.
