# Independent holdout evaluation

This directory freezes ten new historical cases for an independent evaluation of the configuration
at `3ff7fd2a6f2b5a674db04bbe734ed0ff296b3ff9`. No agent or model run occurred before expectations
were committed and pushed.

## Frozen-expectation commit

`96727004b780f961f5c7e331e8024221116b2762`

That commit contains the selection, first-version inputs, dated prior-issue snapshots, two independent
GraphQL fetches, SHA-256 hashes, reference outcomes, verification results and `expected.json`.

## Selection

The source is the same 477-issue population in
`evals/golden/raw/population_normalized.json`. The seed is recorded in `seed.txt`. Within each original
stratum, candidates are ranked by SHA-256 of `seed|group|issue_number`, exactly as in the golden-set
method. The 18 golden IDs are excluded. The duplicate group had only one population case, already
in the golden set, so the holdout has no duplicate case.

| Group | Draw |
|---|---:|
| Core bug | 2 |
| Provider bug | 1 |
| Feature request | 1 |
| Documentation | 1 |
| Security-sounding | 1 |
| No action needed | 2 |
| Meta or task | 2 |

## Frozen expectations

| Case | Group | Labels to add | Comment |
|---|---|---|---|
| airflow-69262 | provider bug | `area:core` | none |
| airflow-70164 | security-sounding | `security` | `security_route` |
| airflow-70232 | core bug | `area:airflow-ctl` | none |
| airflow-70355 | meta or task | `area:providers` | none |
| airflow-70503 | meta or task | none | none |
| airflow-70631 | feature request | `kind:feature`, `area:providers`, `provider:google` | none |
| airflow-71747 | no action needed | none | none |
| airflow-72284 | documentation | none | none |
| airflow-72612 | no action needed | none | none |
| airflow-73941 | core bug | `area:providers`, `provider:fab` | none |

Reasons and every difference from later maintainer action are recorded in `expected.json`. Post-event
facts in `reference.json` are never agent inputs.

## Reproduce the freeze

From the repository root with authenticated GitHub CLI read access:

```powershell
python evals/holdout/prepare_holdout.py --gh gh
python evals/holdout/verify_cases.py
```

The first command performs read-only GraphQL requests. Replay text replaces every `@` and strips
Apache Airflow issue/PR references. The second command checks disjoint selection, first-version
hashes, input boundaries, strict prior-snapshot cutoffs, neutralisation and expectation coverage.

## Pre-run AIC estimate

The final golden attempts used 179.36 AIC for 21 cases, or 8.54 AIC per case. At the same mean,
ten holdout cases are estimated at about **85.4 AIC**. The approved execution phase, if granted,
will stop at **120 AIC total**, even if cases remain unfinished; each individual run retains the
submitted configuration's 25-AIC cap.

## Sequential-runner correction

Case `airflow-70164` first ran as
[41189835746](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41189835746).
It failed with HTTP 429 after exhausting the shared per-run model-invocation limit (20/20), not a
concurrent-dispatch rate limit. The next dispatch,
[41190347793](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41190347793),
was skipped before activation, ran no model and used 0 AIC. This was a harness sequencing error:
`run_sequential.py` turned the switch off after dispatch but before `pre_activation` evaluated it.
The runner now keeps the switch on until `pre_activation` visibly completes successfully, then
turns it off. The one replacement dispatch,
[41190831283](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41190831283),
completed successfully and is the single retry of the first model attempt.
