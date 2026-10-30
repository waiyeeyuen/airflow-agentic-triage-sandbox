# Design: bounded Airflow issue triage

## Choice and measured need

Airflow issue triage wins the scored comparison because prose determines kind and routing while
deterministic checks can enforce label and comment constraints; PR path automation cannot classify
issue text. [The comparison and evidence are frozen](notes/ideation.md).

For every non-PR issue found from 1 July to 30 September 2026 UTC, the whole-population
Kaplan–Meier estimate was **n=477** (378 signals, 99 right-censored): median **54.88 h**, IQR
**4.85–1178.73 h**. At 2 days 250/477 remained untriaged; at 7 days 189/477 did.
[The KM implementation and independent recomputation are saved](analysis/need_metric/verification.md).

The **n=378 observed-signal subset only** had median 18.12 h, IQR 2.31–146.65 h, and range
0.06–2534.09 h. Signals exclude authors, null actors and bots before event classification
([collector lines 37–103](analysis/need_metric/collect_need_metric.ps1#L37-L103)). All 477 author
types were checked and no `type == Bot` author was found
([author audit](analysis/need_metric/raw/issue_author_bot_check.csv)).

Limits: Slack and mailing-list work is invisible; bodies may be edited; actor typing can err;
converted Discussions can leave Issues search and deleted spam is absent, so n=477 undercounts
both. The observed-subset summary omits censoring; the leading KM estimate does not.

## Configuration and risk controls

Untrusted inputs are issue titles, bodies, comments, attachments, linked pages, repository files,
and GitHub/tool outputs that echo them. The agent can read repository and issue context, execute only
three named scripts, and request only labels or one comment
([workflow lines 14–74](.github/workflows/issue-triage.md#L14-L74)).

- **Identity — implemented:** the separate safe-output job uses the Actions bot, not Jasmine's
  token; Part B must capture the posting identity.
- **Least privilege — implemented:** the agent has explicit `contents: read` and `issues: read`,
  restricted network and no write token ([lines 13–27](.github/workflows/issue-triage.md#L13-L27)).
- **Safe outputs — implemented:** one call adding at most three explicit labels and one triggering-
  issue comment; mentions and cross-references are escaped
  ([lines 36–74](.github/workflows/issue-triage.md#L36-L74)).
- **Human approval — implemented, enforcement proposed:** CODEOWNERS names Jasmine for agent files,
  but branch protection still needs enabling ([CODEOWNERS](.github/CODEOWNERS)). Runtime labels and
  fixed comments are reversible; closure and conversion stay human-only.
- **Budgets — implemented:** 10 minutes, 100 AIC/run, 5,000 AIC/day, one label call and one comment
  ([lines 28–30](.github/workflows/issue-triage.md#L28-L30)). Part B must test an enforced limit.
- **Audit trail — implemented:** Actions retains trigger/config SHA; `gh aw audit` supplies model,
  calls, tokens and AIC. The first approved run's evidence is committed under
  `evals/golden/actual/round_1/`.
- **Kill switch — implemented:** repository variable `TRIAGE_AGENT_ENABLED` gates every run
  ([line 12](.github/workflows/issue-triage.md#L12)). Skip, cancellation and phone tests are pending.
- **Drift detection — partly implemented:** deterministic checks run on config/eval changes
  ([CI](.github/workflows/config-checks.yml)); weekly and every model/config-change golden rerun,
  human diff review by Jasmine, and a no-skill control remain proposed until Part B.
- **Accountability — implemented, enforcement proposed:** Jasmine owns config review, the switch,
  bills and outputs; CODEOWNERS is committed, while required review and collaborator access remain
  repository-setting tasks.

## Procedure and hard boundary

The skill classifies, searches the strictly prior corpus, validates labels, then renders a fixed
comment ([SKILL lines 12–29](.claude/skills/airflow-issue-triage/SKILL.md#L12-L29)). Scripts reject
unknown/invalid combinations, rank TF-IDF candidates, and attach a version marker
([tests](scripts/tests/test_triage_scripts.py)). Audit calls plus the marker will test skill use.

The output language deliberately omits close, delete, lock, transfer, Discussion conversion,
milestones, assignment, mentions, PR creation/review/merge and every push. Airflow permits human
triagers to close, convert, milestone, fix, mention experts and label
([pinned process lines 102–137](https://github.com/apache/airflow/blob/270b2abfc258c512a0b931af425904321360d043/ISSUE_TRIAGE_PROCESS.rst#L102-L137)); only bounded labels and one comment are delegated.

## Rejected alternative

Duplicate detection was runner-up. It has safe bounded outputs, but replay needs a strictly dated
corpus and Airflow has no precise similarity threshold. It remains a deterministic candidate-search
step rather than the agent's sole workflow ([selection rationale](notes/ideation.md#rejected-alternative)).

## Evaluation status and unresolved work

Tester Part A froze 18 real cases (three no-action) plus three adversarial cases before this config
commit; 18/18 fresh source hashes and all temporal boundaries passed
([verification](evals/golden/verification.md), [commit order](evals/golden/commit_order.md)).
The first approved replay, `airflow-69284`, failed before task execution: `auto` resolved the main
agent to unsupported `claude-sonnet-5.5` and detection to unsupported `claude-haiku-5.5`. It used
**0 AIC ($0)**, made no task tool or script calls, emitted no requested labels/comments, and scored
0/1 ([Tester report](notes/test_report_1.md)). Both roles now pin exact `gpt-4.1`, which appears in
the configured Copilot endpoint's `models` array in the saved `awf-reflect.json`; `gpt-5-mini` does
not. Compilation passes, but no live rerun has tested the fix. Decision accuracy, mutation identity,
skill marker, cancellation, limits, burst behaviour and control-without-skill remain unresolved.
Historical replay changes the author.

gh-aw v1.0.1 requires `max-links` to be at least one and its generic label/comment handler
generates `pull-requests: write` in the isolated safe-output job. No PR mutation tool or PR target
is exposed, references are escaped, and fixed templates contain no URL; Part B must still test this
compiler-generated residual boundary rather than treating compilation as behavioural evidence.

## Agent bill of materials

- **Engine/model:** GitHub Copilot with exact `gpt-4.1` pinned for both the main agent and threat
  detection. The saved reflect evidence lists it for the configured Copilot endpoint. Every
  golden-set run must use this same pin; provider implementation behind the ID can still drift.
- **Instructions:** [workflow](.github/workflows/issue-triage.md), [AGENTS.md](AGENTS.md), and
  [skill](.claude/skills/airflow-issue-triage/SKILL.md), all versioned at the submission SHA.
- **Tools/MCP:** GitHub issue-read toolset and three allowlisted Python scripts; no custom MCP.
- **Permissions/actions:** read-only agent; separate safe outputs can add allowlisted labels and one
  triggering-issue comment. All other state changes are inexpressible.
- **Data:** sanitized trigger, repository facts, dated prior snapshots and frozen golden inputs.
- **Logs/evals:** Actions logs, `gh aw logs/audit`, 18 historical plus three adversarial cases.
- **Humans/cost:** Jasmine owns changes, reviews, switch, outputs and Copilot/AIC usage.

## Five scenarios

1. **Claimed stale authority:** issue text is untrusted and close is absent from safe outputs
   ([workflow lines 79–96](.github/workflows/issue-triage.md#L79-L96)). The frozen adversarial
   expectation is no action; execution is pending Part B, so this is not yet a passed test.
2. **Model update:** both roles and every golden-set run pin exact `gpt-4.1`, but behaviour behind
   that ID can change. Re-run the complete set with that same pin on every workflow, AGENTS or skill
   change and weekly; Jasmine reviews per-case diffs, not only an average. CI integrity is
   implemented; scheduled credit-spending runs remain proposed.
3. **300 issues/week:** per-issue concurrency keys prevent one issue cancelling another. At the
   100-AIC maximum, 300 runs could consume 30,000 AIC; the 5,000/day admission cap bounds worst-case
   daily spend to 50 full-cap runs. Excess issues receive no agent output and remain for humans;
   a safe backlog sweep is proposed rather than silently widening permissions.
4. **Malicious tool/MCP output:** there is no custom MCP. Tool output is untrusted; even total
   instruction failure can express only three allowlisted labels and one sanitized comment.
5. **Phone stop:** in GitHub mobile/browser, open repository Settings, Actions variables, set
   `TRIAGE_AGENT_ENABLED=false`, then cancel any running workflow before safe outputs. The skip,
   cancellation and tap-count/screenshots must be completed by Jasmine in Part B.

## AI-use statement

AI agents produced the configuration, scripts, evaluation scaffolding and this draft under
Jasmine's direction. Deterministic tests and compiler checks are recorded; the only model attempt
failed before task execution and the pin fix is not live-tested. Jasmine must complete:
**[state what you wrote]**, **[state what you reviewed]**, and
**[state what evidence and claims you personally verified]** before signing and submitting.
