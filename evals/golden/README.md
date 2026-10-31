# Golden evaluation set

This Part A set froze expectations before any agent configuration or run. It contains 18 real
Apache Airflow issues from 1 July–30 September 2026 UTC, three no-action controls, and three
constructed adversarial cases. Part B then replayed all 21 cases in the private sandbox.

## Population and draw

`raw/population_pages.json` is the complete 477-result Issues Search API population used by the
need metric. `population_groups.json` records these mutually exclusive strata:

| Group | Population | Draw |
|---|---:|---:|
| Core bug | 177 | 3 |
| Provider bug | 67 | 3 |
| Feature request | 109 | 2 |
| Documentation | 16 | 2 |
| Meta or task | 25 | 3 |
| No action needed | 7 | 3 |
| Security-sounding | 9 | 1 |
| Duplicate | 1 | 1 |
| Other (not drawn) | 66 | 0 |

Classification uses final maintainer labels and outcome wording only to stratify the population;
these post-event facts are never agent inputs. A duplicate requires direct maintainer wording
`Duplicate of ...`; broad keyword matches are not accepted. A no-action case had complete creation
labels, no human triage event in 48 hours, and the same labels at collection. Converted support
questions and deleted spam can be absent from Issues Search, so no unsupported support/spam stratum
was invented.

Within each stratum, `select_cases.py` ranks candidates by SHA-256 of
`seed|group|issue_number`; the committed seed is in `seed.txt`. This seeded draw is used to show
that cases were not cherry-picked. Random selection is good practice, not an Assignment 3
requirement.

## Frozen inputs

Each `cases/<number>/` contains:

- `source.json`: source URL, creation time, exact first title/body, and SHA-256 hashes;
- `input.json`: neutralised replay text, creation labels/template, and the dated snapshot path;
- `prior_issues.json`: only issues created before the case, with title and labels reconstructed as
  of the case timestamp; and
- `reference.json`: the first-48-hour maintainer outcome, explicitly marked `not_agent_input`.

GraphQL `userContentEdits` is the source of the first body version. For edited issues, the oldest
`diff` is accepted only when its `editedAt` equals issue creation; for unedited issues the current
body is used only when the edit list is empty. Title rename events are reversed. Template labels
are label events attributed to the author/bot within 60 seconds of creation, before any non-author
human event.

Replay text replaces every `@` with `(at)` and strips Apache Airflow issue/PR links. Unsanitised
source URLs remain only in committed evidence. A sandbox replay will be authored by Jasmine, so
historical author association cannot be reproduced.

## Expectations and adversarial cases

`expected.json` fixes label additions, duplicate target, comment decision/type, and forbidden
actions before any run. Expectations may add at most three labels and one comment. The three
adversarial cases test claimed authority to close stale issues, hidden secret/label injection, and
an attempt to force mentions and external links. The last attack's mention is neutralised before
replay so it cannot notify a real user.

Only the Tester may change `expected.json`. Any correction requires a dated reason in
`CHANGELOG.md`; expectations must never be changed to match agent output.

## Reproduce Part A

From the repository root in PowerShell, with authenticated GitHub CLI read access:

```powershell
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) { $gh = '..\.tools\gh\bin\gh.exe' }

# Rebuild the complete read-only population and timelines.
& 'analysis/need_metric/collect_need_metric.ps1' -GhPath $gh

# Recreate the grouping, seed-ranked draw, dated snapshots and case skeletons.
python evals/golden/select_cases.py

# Fetch original versions and freeze sanitized inputs.
python evals/golden/fetch_originals.py --gh $gh
python evals/golden/assemble_cases.py

# Independently re-fetch all selected sources, then verify hashes and leakage boundaries.
python evals/golden/fetch_originals.py --gh $gh --output-subdir raw/verification_graphql
python evals/golden/verify_cases.py
```

The API commands are read-only. `fetch_originals.py` invokes only `gh api graphql`; the population
collector invokes only `gh api` GET requests. `verification.md` and
`verification_results.json` contain the results.

## Part B commands

The readiness harness and exact approval-gated commands are in [`harness/README.md`](harness/README.md).
Preparation (`build_replay_plan.py`, `static_audit.py`, plan-only `replay.py`) is inert. The first
credit-spending command remains blocked until Jasmine directly approves it, GitHub CLI is
authenticated, the Copilot secret is confirmed, and the kill-switch variable is enabled.

## Part B evidence index

Each case's `actual.json` is the compact audit record: it includes the run URL and status, model
outputs, output actors, tool records, safe-output ledger, AIC, errors, jobs and configuration SHA.
The round manifest records approval and dispatch details; each `proposal_score.json` records the
machine-readable comparison with the frozen expectations. Raw downloaded logs may be regenerated
with `python evals/golden/harness/capture_results.py --help` and `gh aw audit <run-id>`.

- [Round 1](actual/round_1/) and [Round 2](actual/round_2/): initial setup and guard failure.
- [Round 3](actual/round_3/) and [Round 4](actual/round_4/): corrected setup and first live block.
- [Round 5](actual/round_5_batch/): baseline batch, manifest, compact audit records and score.
- [Round 6 initial](actual/round_6/) and [completed score](actual/round_6_retry_429/): improved batch,
  sequential 429 retries, manifests, compact audit records and scores for all 21 cases.
- [Queued-run incident](actual/round_6_stale_incident/): kill-switch/cancellation evidence.

To reproduce scoring without credits, run:

```powershell
python evals/golden/harness/score_proposals.py `
  --actual-root evals/golden/actual/round_6 `
  --output evals/golden/actual/round_6/proposal_score.json
```
