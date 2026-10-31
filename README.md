# Airflow agentic issue triage (CS467 Assignment 3)

A sandbox that configures and governs a GitHub Agentic Workflow for first-pass triage of
Apache Airflow issues. All testing happened in this repository only; nothing was written to
apache/airflow.

**Start here: [DESIGN.md](DESIGN.md)**: the justification, controls, test results, bill of
materials, five scenarios and AI-use statement.

| Deliverable | Location |
|---|---|
| Workflow source and compiled lock file | [.github/workflows/issue-triage.md](.github/workflows/issue-triage.md), [issue-triage.lock.yml](.github/workflows/issue-triage.lock.yml) |
| Repository facts for the agent | [AGENTS.md](AGENTS.md) |
| Triage skill and scripts | [.claude/skills/airflow-issue-triage/SKILL.md](.claude/skills/airflow-issue-triage/SKILL.md), [scripts/](scripts/) |
| Contributor guidance | [CONTRIBUTING.md](CONTRIBUTING.md), [.github/CODEOWNERS](.github/CODEOWNERS), [.github/SECURITY.md](.github/SECURITY.md) |
| Need measurement | [analysis/need_metric/](analysis/need_metric/) |
| Golden set: inputs, expected outcomes, actual outputs, logs | [evals/golden/](evals/golden/) |
| Final comparison | [evals/golden/actual/round_6_retry_429/proposal_score.md](evals/golden/actual/round_6_retry_429/proposal_score.md) |
| Reproduction instructions | [evals/golden/README.md](evals/golden/README.md) |
| Governance evidence | [evidence/](evidence/) |
| Agent role reports | [notes/](notes/) |
