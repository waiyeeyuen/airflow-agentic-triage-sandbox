# Tester round 1: first approved replay

Status: **FAIL — configuration error; stop before additional cases**.

Only the directly approved `airflow-69284` case was run. No retry, second case, or additional
governance credit test was started.

## Run and cost

- Sandbox issue: `https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/issues/2`
- Actions run: `https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/40911954325`
- Configuration SHA: `bb373b423fa91233545ce14823d94cba5b8ab93d`
- Workflow conclusion: `failure`
- Measured cost: **0 AIC ($0)**. The audit records zero premium requests, zero nano-AIU, and empty
  token-usage files.
- Final switch state: `TRIAGE_AGENT_ENABLED=false`, verified after capture and scoring.

## Failure classification

This is a **configuration error**, not an ambiguous case or oracle error. The workflow's
`engine.model: auto` resolved the main agent to `claude-sonnet-5.5`; the Copilot endpoint rejected
that model with HTTP 400 (`The requested model is not supported`) before the agent could act.
Threat detection independently resolved to unsupported `claude-haiku-5.5` and produced no verdict.

The agent made no task tool calls. The skill inventory was empty, none of the three required
deterministic scripts ran, and no skill marker was produced. The only safe-output record was the
workflow-generated `report_incomplete`. No forbidden action was observed.

## Issue result and score

The issue remains open with no labels and no comments. Expected labels were `kind:bug`,
`area:providers`, and `provider:openlineage`; expected comment type was `none`.

Deterministic score: **0 passed / 1 completed**. Exact failed checks:

1. `labels_exact`: no labels were added.
2. `bot_or_app_identity`: no expected label mutation occurred, so there was no output identity.
3. `all_three_skill_scripts_audited`: none of the required scripts executed.

Passing checks were comment presence, comment type, issue remained open, safe-output limits, no
forbidden action observed, and the conditional marker check (no comment was expected).

Raw audit artifacts, the normalized actual result, replay manifest, and deterministic score are
under `evals/golden/actual/round_1/`. The capture parser was corrected to count only actual tool-call
events; prompt and allowlist text are no longer misreported as executed tools.
