# Builder round 3: reflect-backed model pin

## Evidence correction

Round 2 used the generic captured `models.json` as availability evidence. That was the wrong source
for the user's model-selection requirement. The authoritative saved run evidence here is
[`awf-reflect.json`](../evals/golden/actual/round_1/cases/airflow-69284/audit/run-40911954325/sandbox/firewall/awf-reflect.json).

In that file, the endpoint with `provider == "copilot"` and `configured == true` includes exact
`gpt-4.1` in its `models` array. It does not include `gpt-5-mini`. The reflect catalogue is active,
network-origin evidence, and the provider model metadata records `gpt-4.1` as observed at
`2026-10-29T16:31:55.769Z`.

## Correction and evaluation invariant

The main GitHub Copilot engine and `safe-outputs.threat-detection.engine` now both pin exact
`gpt-4.1`. Every golden-set run must use this same pinned model for both roles; mixing model IDs
would make comparisons non-equivalent. A model change requires an explicit configuration change
and a complete golden-set rerun.

The official gh-aw engine reference says exact live IDs take precedence, and the v1.0.1 schema
accepts the same `id` and `model` engine object for threat detection. No live run was performed.
The Tester-recorded switch remains false, so runtime behaviour is still unverified.

## Local verification

The v1.0.1 compiler was run in strict release mode with action SHA
`0627fdbe4beb5f3b71aa569f8d97150b87f2111a`. The generated lock pins `gpt-4.1` for the agent and
detection jobs, and a second identical compilation produced the same lock hash. Builder unit tests,
harness unit tests, and golden-input verification pass. The stable lock SHA-256 is
`ED1B1AC5E126962291E1076B6DA2ABCB7E7473E31134F36FF05DC4CF0BC2286F`.
