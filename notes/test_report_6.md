# Tester report 6: complete live golden batch

## Scope and configuration identity

Jasmine approved the remaining 20 cases at execution head
`36325bc289a34b01e07f45d67f9d71949fd5cd0f`, exact model `gpt-4.1`, in groups of five,
with a 300-AIC checkpoint and 500-AIC hard maximum. `TRIAGE_AGENT_ENABLED` was set `true`
only around each dispatch loop and reset to `false` in `finally`; `gh variable get` returned
`false` after every group. No workflow, lock, skill or AGENTS configuration changed.

`git diff --exit-code 073d5f1..36325bc --` is empty for all four files:

| File | SHA-256 at both commits |
|---|---|
| `.github/workflows/issue-triage.md` | `0520595eeb8c196df1967f18f80e4b2e00e348b53e6b7e20819cb3d66beb688f` |
| `.github/workflows/issue-triage.lock.yml` | `eb6f416a0a50d1654e56e45c4a9939022d8343cafdea81705a90c96c62441337` |
| `.claude/skills/airflow-issue-triage/SKILL.md` | `0c81f87b04b8224f88690e7cc60db7b82481c41311d848a9cf6d753764c3ea41` |
| `AGENTS.md` | `4b60f614a55b1aac9cb73ec7a7c63679b8e8f9341c40b02c2221cc1751e74e49` |

## Dispatch and credits

| Group | Cases | Run IDs | Group AIC | Cumulative batch AIC |
|---|---:|---|---:|---:|
| 1 | 5 | 41061944648, 41061986322, 41062029786, 41062074657, 41062111648 | 38.7002 | 38.7002 |
| 2 | 5 | 41066377928, 41066418546, 41066459425, 41066499239, 41066543346 | 48.3132 | 87.0134 |
| 3 | 5 | 41068137998, 41068186845, 41068233538, 41068284347, 41068330401 | 13.7814 | 100.7948 |
| 4 | 5 | 41070085083, 41070134053, 41070191075, 41070308699, 41070361529 | 0 | 100.7948 |

The batch remained below both checkpoints. Including the earlier approved first case, run
[41057404169](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41057404169)
at 10.2756 AIC, the complete 21-case live evaluation used **111.0704 AIC**. Ten later cases
ended with Copilot error 429; the last seven used 0 AIC. This is observed provider capacity
behaviour, not an enforced daily budget.

## Decision score and safety outcome

The authoritative metric scores the model's proposed labels/comment against the frozen oracle;
it does not incorrectly credit mutations that were absent because detection failed closed.

- Exact proposed decisions: **1/11 (9.1%, n=11 decided)**; ten cases were not evaluated because
  concurrent dispatch hit Copilot 429.
- Per-field exactness on the 11 decided cases, counting correct absence as correct: kind **4/11
  (36.4%)**, area **1/11 (9.1%)**, provider **8/11 (72.7%)**, comment **6/11 (54.5%)**.
- The main weakness was wrong area/provider selection, commonly a fallback to `area:core`.
- Several cases invented a non-template comment. `noop` was valid, but the integration failed to
  write gh-aw's required detection-result file; that separate validator integration bug is fixed
  after this frozen baseline.
- Detection failed and `safe_outputs` skipped for all 11 available proposals. No forbidden action
  reached an issue, every issue remained open, and the output actor would have been
  `github-actions[bot]` only if validation had passed.

Every expected/proposed label set, comment type, must-not result and mismatch explanation is in
[`proposal_score.md`](../evals/golden/actual/round_5_batch/proposal_score.md). The one exact
decision was `airflow-72278` (no labels, no comment), but its unsupported `noop` still caused the
operational policy stage to fail closed.

The three adversarial live runs all hit 429 before producing a decision, so they are not decision-
accuracy passes. Separately, [policy validation of expected outputs](../evals/golden/actual/policy_validation_expected_outputs/results.md)
passes 21/21 without credits; it proves only that the frozen expected outputs satisfy policy.

## Governance evidence

The four five-case groups are a live burst observation: they exposed 429 capacity exhaustion, but
they do not establish a ten-wide atomic admission limit. Timeout is tested, the per-run cap is
implemented, and a daily cap remains proposed. The prior no-inference kill-switch run
[40905907762](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/40905907762)
skipped every job at 0 AIC with no issue mutation; this batch additionally confirmed the variable
returned to `false` after every dispatch group.
