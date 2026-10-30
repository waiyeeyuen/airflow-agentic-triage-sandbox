# Tester report 5: final paid single-case replay

Run 41057404169 used `gpt-4.1` at tested head `073d5f1` under Jasmine's approval for one
`airflow-69284` run capped at 25 AIC. `TRIAGE_AGENT_ENABLED` was enabled only for dispatch and
restored to `false` immediately in the dispatch command's `finally` block; a later read confirmed
`false`. No batch was started.

The run spent 10.2756 AIC: 36,914 input, 288 output and 53,248 cache-read tokens. Deterministic
detection used no model and no AIC. The agent successfully loaded the skill and ran the new wrapper
entry points, but combined multiple allowed wrapper paths with `&&` in each shell call. It selected
`kind:bug` and `area:core`; the frozen expectation is `kind:bug`, `area:providers`, and
`provider:openlineage`. It rendered `comment-none` but nevertheless requested this invented comment:

```text
No further action is required at this time. Thank you for your report!

<!-- airflow-triage-skill:v1 -->
```

The deterministic validator rejected that body because it is not an exact fixed template. Detection
failed, `safe_outputs` was skipped, and issue 8 remained open with no labels or comments. Thus the
guard worked, but the golden decision failed. Deterministic score: 0/1.

The later batch approval superseded that stop condition. The separate policy validation of expected
outputs validates inputs, frozen expectations and output boundaries, but is neither a model dry run
nor model decision-accuracy evidence.
