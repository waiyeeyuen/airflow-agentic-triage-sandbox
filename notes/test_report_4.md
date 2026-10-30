# Tester report 4: no-credit wrapper repair

## Scope and result

Tested Builder commit `b9d722a44b3763f441709893f178c49a2499ff0f` only in the private
`waiyeeyuen/airflow-agentic-triage-sandbox` checkout. No issue was opened, no workflow was
dispatched, no agent/model was run, and 0 AIC was spent. The repaired deterministic path passes.

The Tester-owned static audit was updated from the obsolete three Python-command, read-only GitHub
MCP, and AI-detector assumptions. It now checks the exact no-argument wrappers, disabled generic
GitHub MCP, deterministic model-free detector, default-false admission, and pinned credentialless
detection checkout. The generated static contract passes all 21 checks.

## Frozen oracle and label policy

`git diff --exit-code dd295091 -- evals/golden/expected.json` returned 0. The current and frozen
`airflow-69284` entries are identical: add `kind:bug`, `area:providers`, and
`provider:openlineage`; duplicate `null`; no comment; comment type `none`. The 19-label taxonomy in
`scripts/label_policy.json` contains those exact labels, limits additions to three, permits one
kind/area/provider label, requires `area:providers` with a provider label, and makes `security`
exclusive. `python evals/golden/verify_cases.py` reported `verified 18 historical and 3
adversarial cases`.

## Repaired `airflow-69284` path

Focused command (0.772 s):

```powershell
python -m unittest scripts.tests.test_triage_scripts.WrapperTests.test_fixed_wrapper_sequence_preserves_duplicate_labels_and_comment scripts.tests.test_triage_scripts.WrapperTests.test_wrappers_reject_arguments_before_reading_fixed_files scripts.tests.test_triage_scripts.WrapperTests.test_wrapper_runtime_never_reads_stdin scripts.tests.test_triage_scripts.CliTests.test_safe_output_validator_accepts_templates_and_rejects_mentions_links scripts.tests.test_triage_scripts.CliTests.test_negative_safe_output_gate_applies_nothing -v
```

All five tests passed. The sequence exercised search, label-none, kind-bug, area-providers,
provider-openlineage, and comment-none in that exact order. It produced top duplicate candidate
`69275`, validated labels `['kind:bug', 'area:providers', 'provider:openlineage']`, and
`{'comment_type': 'none', 'body': ''}`. A candidate is not treated as a duplicate decision. The
entry wrapper rejects an unexpected argument before reading fixed files, and both a closed stdin
and a stdin object that raises on read completed without a read or wait.

Linux/container limitation: WSL returned `Wsl/E_ACCESSDENIED`; Docker reported no Linux engine;
Git Bash exited `-1073741502` before executing. Therefore the exact shebang-launched one-word
commands could not safely be run on Linux in this environment. The same committed executable entry
file was tested for argument rejection through Python, the same runtime entry points were tested in
sequence with isolated fixed-path substitutes, and `git ls-files --stage` verified every wrapper is
mode `100755`. This is the only platform limitation in this round.

## Workflow, lock, and detection

The source and compiled lock contain exactly the enumerated wrapper commands. Each command is one
word; neither allowlist contains broad `python` or `python3` access. Generic shell commands remain
explicitly denied. The detection job first uses pinned
`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` with
`persist-credentials: false`, then runs `scripts/validate_safe_outputs.py`.

Strict reproduction (1.725 s) used installed `gh-aw v1.0.1`:

```powershell
gh aw compile issue-triage --action-mode release --action-tag 0627fdbe4beb5f3b71aa569f8d97150b87f2111a --no-check-update --strict
```

Exit was 0. Lock SHA-256 was unchanged before and after:
`EB6F416A0A50D1654E56E45C4A9939022D8343CAFDEA81705A90C96C62441337`. The compiler emitted one
existing `step-reference` warning for `DETECTION_AGENTIC_EXECUTION_OUTCOME`; it still reported one
successful strict compilation. This warning did not alter the lock.

Direct valid fixture validation took 0.279 s, exited 0, and returned
`{"comment_calls":1,"items":2,"label_calls":1,"valid":true}`. The invalid combined fixture took
0.303 s, exited 1, and rejected `priority:critical`. Focused tests separately rejected an invalid
label, an `@mention`, and an HTTP link, and kept the simulated applied-output list empty. The lock
manifest has `"admission": false`; the safe-output job is gated on
`needs.detection.result == 'success'`. Thus invalid output fails detection and is not admitted.

## Full commands and outcomes

- `python evals/golden/harness/build_replay_plan.py`: planned 21 cases, first `airflow-69284`, no
  GitHub writes.
- `python evals/golden/harness/static_audit.py`: PASS, 21/21 static checks; live execution false.
- `python -m unittest discover -s scripts/tests -v`: 29/29 passed (1.165 s).
- `python -m unittest discover -s evals/golden/harness -p 'test_*.py' -v`: 8/8 passed (0.040 s).
- `python evals/golden/verify_cases.py`: 21/21 inputs verified.
- `python evals/golden/harness/replay.py --case-id airflow-69284`: plan-only output; no write.
- `python evals/golden/harness/score.py`: preserved Round 3 evidence remains 0/1 for its historical
  failed run; it is not a new execution and does not contradict this deterministic repair test.
- `(Get-Content DESIGN.md).Count`: exactly 150, within the limit.

The combined build/static/unit/harness/integrity/plan/score command took 5.7 s wall time. GitHub CLI
authentication is currently invalid, the no-skill control variant is absent, and this no-credit
round prohibited remote execution; these remain accurately marked as live blockers. No Builder
issue was found in the repaired deterministic path.
