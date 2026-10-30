# Part B harness

This harness is inert by default. Building the plan, static audit and scoring empty results makes no
GitHub write and spends no AI credits. Only `replay.py --execute` can open a sandbox issue, and it
requires a direct-approval file, private-repository check, valid secret name, enabled kill-switch
variable, frozen oracle hash, exact Builder commit approval and case order. Round 3 defaults to
`evals/golden/actual/round_3`; the replay guard refuses the preserved Round 1 directory and stale
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
repository. The fresh Round 3 approval must name Builder commit
`2a5e692b9066cb0cf54d98d5d9ead75525afeeb3`, case `airflow-69284`, and exactly 25 AIC. Replay one
case, wait for completion, then capture and score:

```powershell
python evals/golden/harness/replay.py --case-id airflow-69284 --execute `
  --round-dir evals/golden/actual/round_3 `
  --approval-file <absolute-uncommitted-round3-approval.json>
python evals/golden/harness/capture.py --case-id airflow-69284 --round-dir evals/golden/actual/round_3
python evals/golden/harness/score.py --round-dir evals/golden/actual/round_3
```

Repeat in `replay_plan.json` order only after reviewing the first audit. See
`governance_test_plan.md` for kill-switch, cancellation, budget, burst, no-skill and phone tests.
