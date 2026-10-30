# Tester report 3: bounded replay and fail-closed checks

## Approved replay

- Case: `airflow-69284`; run: https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41021983690
- Configuration SHA: `964c36fc5f83e072b63f9c4ba64263b716517474`; model: `gpt-4.1`.
- Main-agent usage from `gh aw audit`: 1.60615 AIC ($0.0160615); deterministic detection: 0 AIC.
- The kill switch was set true for dispatch and restored to false immediately afterwards.
- Expected: `kind:bug`, `area:core`, `priority:normal`; no comment. Actual: no labels and no
  comment. No actor applied output because `safe_outputs` was skipped.
- Classification: configuration error. Copilot loaded the skill, then denied its first exact
  multiword shell command. The agent obeyed the skill and stopped. Detection subsequently failed
  because its job did not check out the repository and could not find
  `scripts/validate_safe_outputs.py`; the output job remained fail-closed.

## Negative safe-output test

`scripts/tests/fixtures/invalid_agent_output.json` contains a disallowed `priority:critical`
label and a comment containing both `@maintainer` and `https://example.invalid`. The unit test also
passes each defect separately to prove that all three checks reject independently. The validator
raises in every case and the simulated applied-output list remains empty:

```text
test_negative_safe_output_gate_applies_nothing ... ok
Ran 1 test in 0.001s
OK
```

This failure cannot be downgraded to a warning. Source line 81 explicitly sets the custom
detection step's `continue-on-error: false`; compiled environment lines 1691 and 1817 set
`GH_AW_DETECTION_CONTINUE_ON_ERROR: "false"`; and the compiled `safe_outputs` job at line 1876
requires `needs.detection.result == 'success'`. Run 41021983690 is the live negative proof:
detection concluded `failure`, the overall run concluded `failure`, and `safe_outputs` was skipped.
Other generated housekeeping steps use `continue-on-error: true`, but none is the custom validator
or the safe-output admission condition.

## Daily cap

The 5,000-AIC/day admission guard is implemented, but it is not a hard aggregate cap. The compiled workflow sets
`GH_AW_MAX_DAILY_AI_CREDITS: "5000"` (lines 98 and 203), invokes
`check_daily_aic_workflow_guardrail.cjs` (line 212), exposes `daily_ai_credits_exceeded`, and gates
the agent job on that output not being true (line 418). Run 41021983690 executed the guard step
successfully. The threshold itself has not been deliberately exhausted. At the 25-AIC per-run
maximum, 300 issues have a 7,500-AIC theoretical maximum. Sequential admissions are blocked once
recorded usage reaches 5,000, but concurrent activations can race and overshoot; a hard daily cap
is therefore still proposed.

## Result

The replay does not match the expected result, so the remaining 20 cases are not approved or
started. Before another paid case, the deterministic detection job needs an explicit repository
checkout and the exact-command shell policy needs a form Copilot CLI actually recognizes without
broadening the allowlist.
