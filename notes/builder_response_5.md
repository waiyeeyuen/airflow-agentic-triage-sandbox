# Builder response 5: no-credit execution-path repair

No model workflow was triggered and no AIC was spent in this repair round.

## Runtime repair

The model bash allowlist now contains only individually enumerated, no-argument executable wrappers.
It grants no generic `python`, `python3`, shell prefix, wildcard, or argument-bearing command. The
wrappers reject arguments, never read stdin, and use fixed repository and `/tmp/gh-aw/agent` paths.
They preserve the dated TF-IDF duplicate search, incremental label-policy validation, and exact
comment templates. Duplicate comment wrappers select only ranks 1–5 from the fixed search output.
Every executable wrapper is committed with Linux mode `100755`.

The deterministic detection steps now begin with pinned
`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` and
`persist-credentials: false`, before `scripts/validate_safe_outputs.py`. Detection remains
`continue-on-error: false`, and safe outputs still require detection success.

## Provenance corrections

- Workflow 40905907762 was invoked once before approval, but all six jobs were skipped; it invoked
  no model and spent 0 AIC. There was no unapproved model run.
- Approved attempt 40911954325 had a 100-AIC cap and spent 0 AIC.
- Approved attempt 40993175316 had a 100-AIC cap and spent 70.303 AIC total: 10.166 main-agent
  AIC plus 60.137 detection AIC. The 5.083 figure is a partial failed-tool friction attribution
  within the 10.166 total, not the run total or an additional charge.
- Approved attempt 41021983690 had a 25-AIC cap and spent 6.4246 AIC total. The 1.60615 figure is
  a partial failed-tool attribution within that total, not an additional charge.
- The frozen `airflow-69284` expectation remains `kind:bug`, `area:providers`, and
  `provider:openlineage`; `evals/golden/expected.json` was not modified.
