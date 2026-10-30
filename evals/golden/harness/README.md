# Part B harness

This harness is inert by default. Building the plan, static audit and scoring empty results makes no
GitHub write and spends no AI credits. Only `replay.py --execute` can open a sandbox issue, and it
requires a direct-approval file, private-repository check, valid secret name, enabled kill-switch
variable, frozen oracle hash, exact Builder commit approval and case order. Round 2 defaults to
`evals/golden/actual/round_2`; the replay guard refuses the preserved Round 1 directory and stale
manifests.

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
repository. The fresh Round 2 approval must name Builder commit
`ac75039cce1ff9983cc62619cfefb42c4e2f1d38`, case `airflow-69284`, and exactly 100 AIC. Replay one
case, wait for completion, then capture and score:

```powershell
python evals/golden/harness/replay.py --case-id airflow-69284 --execute `
  --round-dir evals/golden/actual/round_2 `
  --approval-file <absolute-uncommitted-round2-approval.json>
python evals/golden/harness/capture.py --case-id airflow-69284 --round-dir evals/golden/actual/round_2
python evals/golden/harness/score.py --round-dir evals/golden/actual/round_2
```

Repeat in `replay_plan.json` order only after reviewing the first audit. See
`governance_test_plan.md` for kill-switch, cancellation, budget, burst, no-skill and phone tests.
