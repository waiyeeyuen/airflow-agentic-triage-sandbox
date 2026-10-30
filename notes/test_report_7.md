# Tester report 7: Round 6 credit-free preflight

## Scope

This independently tests Builder commit `85e545b844f9c2f1d42d19c4e4a77ccbca107004` before any
Round 6 model run. `DESIGN.md`, the frozen oracle, and all Round 5 actual outputs are unchanged.

## Findings

- A valid `noop` exits zero and writes gh-aw's required clean `detection_result.json`. The five
  fields match the official detector contract: three false booleans, empty `reasons`, and empty
  optional `warnings`.
- A disallowed label, an `@mention`, a link, or arbitrary free text exits non-zero and writes no
  safe verdict. The gate therefore remains fail closed.
- `AGENTS.md` derives its mapping from the pinned Airflow triage process's kind/area/provider rules
  and the allowlist in `scripts/label_policy.json`; it does not cite a golden case.
- `SKILL.md` requires clear evidence, forbids defaulting to `area:core`, and permits comments only
  through fixed template IDs with byte-identical wrapper output.
- Strict compilation is reproducible; source and lock invoke the validator with the fixed detection
  result path. The existing compiler warning about `detection_agentic_execution` remains.
- Round 5 is the frozen baseline: **1/11 decided (9.1%)**, ten not evaluated after concurrent
  dispatch hit Copilot 429. Field exactness on decided cases, with correct absence counted, is kind
  **4/11 (36.4%)**, area **1/11 (9.1%)**, provider **8/11 (72.7%)**, comment **6/11 (54.5%)**.

## Credit-free checks

- Script/workflow unit tests: 31 passed.
- Harness tests: 9 passed.
- Static contract: 21 checks passed.
- Frozen integrity: 18 historical and three adversarial cases verified.
- No model run or GitHub issue was triggered.

Round 6 must run all 21 cases serially or in pairs, include the three adversarial cases, check once
per group, and stop before the next group if cumulative AIC would exceed the approved 300-AIC cap.
