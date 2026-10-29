# Workflow recommendation: Airflow issue triage

## Recommendation

Choose **first-pass issue triage**. The agent should propose at most three allowlisted labels and
at most one fixed-template clarification or routing comment. It must never close, convert, lock,
delete, transfer, assign a milestone, mention people, merge, or push. This workflow needs model
judgement because an issue's prose—not a changed file path—determines its `kind:`, `area:`, and
provider routing; deterministic scripts can still validate labels, search dated prior issues, and
render the comment. Airflow's [`ISSUE_TRIAGE_PROCESS.rst`](https://github.com/apache/airflow/blob/270b2abfc258c512a0b931af425904321360d043/ISSUE_TRIAGE_PROCESS.rst)
provides a written standard, while issue templates pre-apply `needs-triage`.

Scores are 0 (poor) to 3 (strong). Columns: **J** model judgement, **H** historical/no-action
cases, **R** leakage-safe replay, **S** safe bounded outputs, **N** measurable need, **B** student
budget, **W** written standard.

| Candidate | J | H | R | S | N | B | W | Total / 21 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Issue triage | 3 | 3 | 3 | 3 | 3 | 3 | 3 | **21** |
| Duplicate detection | 2 | 3 | 2 | 3 | 2 | 3 | 1 | **16** |
| First-pass newcomer PR review | 3 | 3 | 2 | 2 | 3 | 1 | 2 | **16** |
| CI-failure analysis | 3 | 3 | 1 | 3 | 2 | 2 | 1 | **15** |

## Rejected alternative

The runner-up tie is resolved in favour of **duplicate detection** as the rejected alternative:
it has cheap, bounded outputs and plentiful non-duplicates, but historical replay requires a
strictly dated prior-issue corpus and Airflow has no equally precise duplicate threshold standard.
Issue triage absorbs duplicate search as one deterministic step while retaining a clearer oracle.
PR review also scored 16, but reconstructing review-time repository state is harder and large diffs
make the free-credit budget less predictable.

## Need metric

Using read-only `gh api --paginate`, I collected every non-PR issue opened **1 July–30 September
2026 UTC** on 29 October 2026 UTC. Authors whose GitHub type was `Bot` or whose login matched the
recorded bot pattern were excluded: 0 of 477, leaving **n=477**. The metric is creation to the first
timeline comment, label change, close, or conversion by a non-author human; removal of
`needs-triage` counts. See the raw [population](../analysis/need_metric/raw/population_pages.json),
exact [commands](../analysis/need_metric/commands.md), [metadata](../analysis/need_metric/metadata.json),
and independent [verification](../analysis/need_metric/verification.md).

The whole-population Kaplan–Meier estimate (**n=477; 378 signals; 99 right-censored at collection**)
leads: Q1 **4.85 h**, median **54.88 h**, and Q3 **1178.73 h**. Here Qp is the earliest event time
where cumulative incidence `1-S(t)` reaches p=.25, .50, or .75; all three were reached. The median
is consistent with `S(48 h)=0.524109` and `S(168 h)=0.396226`: **250/477 (52.4%)** remained
untriaged after two days and **189/477 (39.6%)** after seven. See the saved [KM summary](../analysis/need_metric/km_summary.json)
and [curve](../analysis/need_metric/km_curve.csv).

For clarity, the earlier median **18.12 h**, IQR **2.31–146.65 h**, and range
**0.06–2534.09 h** describe only the **n=378 observed-signal subset**, not all 477 issues. In the
full **n=477** population, **99/477 (20.8%)** had no signal by collection. Outcomes were 204 open,
273 closed, and 0 observed conversions. Full results are in [`summary.json`](../analysis/need_metric/summary.json).

Signals exclude the issue author, null actors, bots, and thus automatic/template/bot labels: the
human/non-author predicate is at script [lines 37–46](../analysis/need_metric/collect_need_metric.ps1#L37-L46)
and is applied before event classification at [lines 78–103](../analysis/need_metric/collect_need_metric.ps1#L78-L103).
All 477 authors were checked in [`issue_author_bot_check.csv`](../analysis/need_metric/raw/issue_author_bot_check.csv);
the exact GitHub `type == Bot` [list](../analysis/need_metric/raw/bot_type_issue_authors.json) is empty,
and the population filters/output are at script [lines 146–162](../analysis/need_metric/collect_need_metric.ps1#L146-L162).

Required limitations: Slack/mailing-list triage is invisible; issue bodies may have been edited;
bot detection can misclassify unusual accounts. Converted issues can leave Issues search and
deleted spam is absent, so the 477-search-result population can undercount both and zero observed
conversions is not evidence of none. The n=378 descriptive quartiles omit censored cases; KM does not.

## Private sandbox plan (do not create yet)

- Create a **private** repository only after Jasmine approves this recommendation.
- Copy the pinned `ISSUE_TRIAGE_PROCESS.rst`, `.github/SECURITY.md`, the four issue templates and
  `.github/ISSUE_TEMPLATE/config.yml`; add only the representative project files needed by cases.
- In the private sandbox, clone the label catalogue with `gh label clone apache/airflow`, then
  restrict the workflow's safe-output allowlist to the evaluated triage labels.
- Keep upstream source URLs only in committed evaluation JSON. Neutralise `@` and strip upstream
  cross-references before any replay text is posted as a sandbox issue.
- Do not run the workflow against Apache Airflow. Use `github-actions[bot]` or an app in the sandbox.

Do not switch workflows later unless a Marker identifies marks that are structurally unreachable
with issue triage rather than fixable execution; a switch requires a new golden set.
