# Expectation commit order

`expected.json`, all 18 historical cases and all three adversarial cases were first committed at
`dd295091c8a89bd7ccb06662d996f6a5ba960e5c`.

At that commit, the history contained no `.github/`, `AGENTS.md`, `.claude/`, `CONTRIBUTING.md`,
`DESIGN.md` or `scripts/` configuration commit. No workflow/model run had occurred. This records
the required ordering: expectations precede the Builder's first configuration commit.
