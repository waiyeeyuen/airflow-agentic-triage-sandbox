# HEAD deliverable check — 2026-10-31

- `AGENTS.md`: present. It covers project structure, compile/test commands, conventions, ownership,
  and forbidden changes, including the frozen-expectation rule.
- `CONTRIBUTING.md`: present. It requires disclosure and human verification of AI contributions and
  forbids posting sandbox content to Apache Airflow.
- `evals/golden/`: present. Its README indexes rounds 1–6, identifies each compact `actual.json` as
  the run/audit record, links manifests and scores, and gives collection and scoring instructions.
- Workflow lock: exact. Strict `gh aw compile` succeeded; the only compiler output was the existing
  unknown-step warning, and `git diff --exit-code` found no lock-file change. All 31 unit/contract
  tests passed.
- CODEOWNERS: present for workflow, skill and `AGENTS.md`. Requiring CODEOWNERS review could not be
  enabled: GitHub's branch-protection API returned HTTP 403 because this private repository needs a
  higher plan. DESIGN therefore records enforcement as proposed.

No required file is missing. The remaining external limitation is branch-protection enforcement.
