# Builder round 2: concrete model pin

## Finding accepted

The only approved replay, `airflow-69284` at configuration SHA
`bb373b423fa91233545ce14823d94cba5b8ab93d`, failed before task execution. The main `auto` model
became unsupported `claude-sonnet-5.5`; threat detection independently selected unsupported
`claude-haiku-5.5`. The run spent **0 AIC ($0)**, made no task tool or deterministic-script calls,
created no requested safe output, and scored 0/1. See [Tester round 1](test_report_1.md) and the
[main resolution record](../evals/golden/actual/round_1/cases/airflow-69284/audit/run-40911954325/agent/model-resolution.json).

## Correction

Both the main Copilot engine and `safe-outputs.threat-detection.engine` now explicitly request
`gpt-5-mini`. The captured run catalog lists that exact ID under the active `github-copilot`
provider with the Responses wire API in
[`models.json`](../evals/golden/actual/round_1/cases/airflow-69284/audit/run-40911954325/models.json).
This avoids alias/default selection while retaining the same provider.

The official gh-aw engine reference says exact live IDs take precedence and unavailable IDs fail
at first inference. The official environment-variable reference says an explicit
`safe-outputs.threat-detection.engine.model` takes precedence for detection. The threat-detection
reference and security specification allow the engine object with `id` and `model`:

- <https://github.github.com/gh-aw/reference/engines/>
- <https://github.github.com/gh-aw/reference/environment-variables/>
- <https://github.github.com/gh-aw/reference/threat-detection/>
- <https://github.com/github/gh-aw/blob/main/specs/security-architecture-spec.md#td-14-engine-configuration-object>

## Verification and boundary

The v1.0.1 compiler was run in strict release mode with action SHA
`0627fdbe4beb5f3b71aa569f8d97150b87f2111a`. A second identical compilation produced the same lock
hash, `0EEAC426FCAE6C6F9D8B661528C05281BBEAD904601B00C4361BE94E07F755F1`. Builder unit tests,
harness unit tests, and golden-input verification pass.

No workflow was dispatched. `TRIAGE_AGENT_ENABLED` remains false as recorded by Tester, so the
model pin and resulting behaviour remain untested until a separately approved Part B replay.
