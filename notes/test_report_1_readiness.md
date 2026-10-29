# Tester round 1 readiness report

Status: **static preparation complete; live Part B not authorized or run**. No sandbox issue was
opened, `TRIAGE_AGENT_ENABLED` was not enabled, and no AI credits were spent.

## Local evidence

- Builder commit audited: `6251faf`.
- Frozen expectations unchanged: SHA-256
  `f08c7d11a3b39ca6522901d1c4d0571020da31f569b40e2249edf7345b1e3ad7`.
- `gh aw` v1.0.1 strict compilation succeeded with the pinned action SHA; regenerated
  `issue-triage.lock.yml` had no diff.
- Builder tests: 12/12 passed; harness tests: 5/5 passed; golden verification: 18/18 historical
  plus 3/3 adversarial inputs passed; `DESIGN.md` remains 121 lines.
- Static contract: 17/17 checks passed. Compiled GitHub MCP tools are read-only; the only mutating
  safe-output tools are `add_labels` and `add_comment`; the source/lock contain the kill switch,
  100-AIC/run and 5,000-AIC/day caps, per-issue concurrency, three-script allowlist, three-label/
  one-comment limits, and blocked mentions/domains/references.
- All 21 expected label sets pass `validate_labels.py`. The expected duplicate is present in the
  deterministic top five but ranks fourth, so model judgement—not a green run—must select it.

## Prepared harness

`evals/golden/harness/` now provides the pinned 21-case replay plan, private-repository and approval
guards, chronological one-case replay, run mapping, `gh aw audit --json --parse` capture, live issue
state/identity/tool/marker evidence, deterministic scoring, and governance test instructions.
Plan-only replay and an empty score were exercised; neither writes to GitHub.

## Blocking prerequisites

1. Jasmine must directly approve the first credit-spending run and its 100-AIC ($1 maximum) scope.
2. GitHub CLI must be re-authenticated; current `gh auth status` says the saved token is invalid.
3. Repository secret `COPILOT_GITHUB_TOKEN` must be added/confirmed without exposing its value.
4. Run the no-inference kill-switch skip test while `TRIAGE_AGENT_ENABLED=false`, then set it true
   only for the approved run. Secret/variable state could not be read while CLI auth was invalid.
5. The Builder must provide a separate no-skill control variant, or Jasmine must explicitly expand
   the Tester's authority for a temporary variant. The Tester did not edit Builder-owned files.
6. Jasmine alone must later perform the phone kill-switch test and supply tap count/screenshots.

After prerequisites, the exact first credit-spending action is opening the first chronological case
in the private sandbox:

```powershell
python evals/golden/harness/replay.py --case-id airflow-69284 --execute `
  --approval-file <absolute-uncommitted-approval.json>
```

The harness then maps its Actions run. After completion, run `capture.py` and `score.py` before
seeking approval for the other 20 cases. The full golden set is capped at 2,100 AIC ($21); all
planned extra cancellation/limit/no-skill/burst tests have a conservative combined round cap of
3,400 AIC ($34) and require separately scoped approval.
