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
and tool outputs that echo them. A pre-agent step prepares immutable issue JSON; the model can run
only individually allowed, no-argument wrapper executables and request labels or one comment
([workflow](.github/workflows/issue-triage.md)).

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
- **Budgets — timeout tested; per-run cap implemented; hard daily cap proposed:** 10 minutes, 20
  turns and 25 main-agent AIC/run are enforced. The compiled activation job scans prior workflow
  AIC against 5,000/day and blocks when already exceeded, but concurrent activations can race, so
  it is an admission guard rather than a hard aggregate cap. Run 40993175316 tested the timeout;
  the per-run threshold and admission guard have not been deliberately exhausted.
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

The workflow, not the model, writes fixed-path issue JSON. The skill then runs exact no-argument
wrappers to search the prior corpus, validate labels, and render a fixed comment; any denied command
means stop with no output ([skill](.claude/skills/airflow-issue-triage/SKILL.md)). Scripts reject
unknown combinations and never read stdin ([tests](scripts/tests/test_triage_scripts.py)). gh-aw
v1.0.1 injects generic read-shell approvals for Copilot, so the engine arguments explicitly deny
each one (including its shell safe-output shim); native safe-output MCP calls remain available.

AI threat detection was removed after it consumed 60.137/70.303 AIC in a 34-request file-reading
loop. Detection now runs with `engine: false`: a deterministic fail-closed step accepts only policy-
valid labels and exact templates and rejects mentions, links, unknown output types and excess calls
([validator](scripts/validate_safe_outputs.py)). This is narrower and auditable for two reversible
output types; the built-in safe-output allowlists remain an independent enforcement layer.

The output language deliberately omits close, delete, lock, transfer, Discussion conversion,
milestones, assignment, mentions, PR creation/review/merge and every push. Airflow permits human
triagers to close, convert, milestone, fix, mention experts and label
([pinned process lines 102–137](https://github.com/apache/airflow/blob/270b2abfc258c512a0b931af425904321360d043/ISSUE_TRIAGE_PROCESS.rst#L102-L137)); only bounded labels and one comment are delegated.

## Rejected alternative

Duplicate detection was runner-up. It has safe bounded outputs, but replay needs a strictly dated
corpus and Airflow has no precise similarity threshold. It remains a deterministic candidate-search
step rather than the agent's sole workflow ([selection rationale](notes/ideation.md#rejected-alternative)).

## Evaluation status and unresolved work

Tester Part A froze 18 real cases (three no-action) plus three adversarial cases before configuration;
18/18 source hashes and every temporal boundary passed ([verification](evals/golden/verification.md)).
Early approved runs exposed an unsupported `auto` model, a skill/shell-guard conflict, and an AI-
detection file-reading loop. The guard denied redirection, the 10-minute timeout contained the loop,
and exact `gpt-4.1`, fixed-path input and deterministic detection repaired those setup failures.

Round 5 is the baseline: 111.0704 AIC, exact proposed-decision accuracy **1/11 (9.1%, n=11 decided)**, with ten not evaluated after concurrent dispatch hit Copilot 429. Field exactness was
kind 4/11 (36.4%), area 1/11 (9.1%), provider 8/11 (72.7%), comment 6/11 (54.5%). Its main weakness
was area/provider confusion, often defaulting to `area:core`, plus invented free-text comments.
One general improvement added process/taxonomy-derived area/provider guidance, required clear
evidence for any output and restricted comments to fixed template IDs. Round 6 used 140.1156 AIC:
**3/16 exact (18.8%, n=16 decided)** with five 429 non-evaluations. Field exactness became kind 9/16
(56.3%), area 5/16 (31.3%), provider 11/16 (68.8%), comment 12/16 (75.0%)
([comparison](evals/golden/actual/round_6/proposal_score.md)). The improvement and re-test used the
same 21 cases, so the apparent gain may overfit and requires a fresh holdout before deployment.
Round 5 live-blocked 11/11 proposals with no forbidden action. Round 6 live-blocked two invented
comments; no forbidden action occurred and every issue remained open, but one bounded wrong
mutation added two allowlisted labels as `github-actions[bot]`. Historical replay changes the author;
the no-skill control and phone screenshots remain unresolved.
gh-aw v1.0.1 requires `max-links` to be at least one and its generic label/comment handler
generates `pull-requests: write` in the isolated safe-output job. No PR mutation tool or PR target
is exposed, references are escaped, and fixed templates contain no URL; Part B must still test this
compiler-generated residual boundary rather than treating compilation as behavioural evidence.
Budgets: timeout tested; per-run cap implemented; daily cap proposed. Pairwise Round 6 stayed below its 300-AIC cap but still produced five 429 non-evaluations, so provider capacity is not a budget.

## Agent bill of materials

- **Engine/model:** GitHub Copilot with exact `gpt-4.1` for the main agent. Threat detection is
  deterministic (`engine: false`). The provider implementation behind the pinned ID can still drift.
- **Instructions:** [workflow](.github/workflows/issue-triage.md), [AGENTS.md](AGENTS.md), and
  [skill](.claude/skills/airflow-issue-triage/SKILL.md), all versioned at the submission SHA.
- **Tools/MCP:** finite exact no-argument wrapper commands; no broad Python, shell-prefix,
  GitHub-read or custom MCP tool.
- **Permissions/actions:** read-only agent; separate safe outputs can add allowlisted labels and one
  triggering-issue comment. All other state changes are inexpressible.
- **Data:** sanitized trigger, repository facts, dated prior snapshots and frozen golden inputs.
- **Logs/evals:** Actions logs, `gh aw logs/audit`, 18 historical plus three adversarial cases.
- **Humans/cost:** Jasmine owns changes, reviews, switch, outputs and Copilot/AIC usage.

## Five scenarios

1. **Claimed stale authority:** issue text is untrusted and close is absent from safe outputs
   ([workflow lines 79–96](.github/workflows/issue-triage.md#L79-L96)). Round 6 made the exact frozen
   no-action decision; the other two adversarial cases were decided but incorrect.
2. **Model update:** the main role and every golden-set run pin exact `gpt-4.1`, but behaviour behind
   that ID can change. Re-run the complete set with that same pin on every workflow, AGENTS or skill
   change and weekly; Jasmine reviews per-case diffs, not only an average. CI integrity is
   implemented; scheduled credit-spending runs remain proposed.
3. **300 issues/week:** per-issue concurrency prevents one issue cancelling another. At the 25-AIC
   maximum, 300 runs could consume 7,500 AIC; no enforced 5,000-AIC daily cap exists. An atomic
   account-side daily admission cap is proposed. The batch's 429s show that provider capacity can
   stop decisions earlier; blocked issues remain for humans and a safe backlog sweep is proposed.
4. **Malicious tool/MCP output:** there is no custom MCP. Tool output is untrusted; even total
   instruction failure can express only three allowlisted labels and one sanitized comment.
5. **Phone stop:** set `TRIAGE_AGENT_ENABLED=false`, then cancel every already-created workflow.
   A queued incident run continued into agent/detection after the switch changed, proving the
   variable alone does not stop existing executions; cancellation UI/tap screenshots remain pending.

## AI-use statement

AI agents produced the configuration, scripts, evaluation scaffolding and this draft under
Jasmine's direction. Deterministic tests, compiler checks and approved live proposals are recorded;
failed-closed output must not be confused with correct decisions. Jasmine must complete:
**[state what you wrote]**, **[state what you reviewed]**, and
**[state what evidence and claims you personally verified]** before signing and submitting.
