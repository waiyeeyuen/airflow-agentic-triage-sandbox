# Part B harness

This harness is inert by default. Building the plan, static audit and scoring empty results makes no
GitHub write and spends no AI credits. Only `replay.py --execute` can open a sandbox issue, and it
requires a direct-approval file, private-repository check, valid secret name, enabled kill-switch
variable, frozen oracle hash, Builder ancestor and exact case order.

## Safe preparation commands

```powershell
python evals/golden/harness/build_replay_plan.py
python evals/golden/harness/static_audit.py
python evals/golden/harness/replay.py --case-id airflow-69284
python evals/golden/harness/score.py
```

The third command is plan-only without `--execute`; the fourth reports 0/21 completed until real
captures exist. Unit/config checks remain:

```powershell
python -m unittest discover -s scripts/tests -v
python -m unittest discover -s evals/golden/harness -p 'test_*.py' -v
python evals/golden/verify_cases.py
```

## After direct approval

Use `approval.example.json` only as a template and keep the real approval file outside the
repository. The first approval must be scoped to exactly 100 AIC. Replay one case, wait for
completion, then capture and score:

```powershell
python evals/golden/harness/replay.py --case-id airflow-69284 --execute `
  --approval-file <absolute-uncommitted-approval.json>
python evals/golden/harness/capture.py --case-id airflow-69284
python evals/golden/harness/score.py
```

Repeat in `replay_plan.json` order only after reviewing the first audit. See
`governance_test_plan.md` for kill-switch, cancellation, budget, burst, no-skill and phone tests.
