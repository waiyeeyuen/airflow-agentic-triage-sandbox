# Phone kill-switch test — 2026-10-31

Wai Yee used a phone browser to change `TRIAGE_AGENT_ENABLED` from `true` to `false` and cancel
[run 41166022897](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41166022897).
The observed procedure took five taps and 1 minute 37 seconds.

The post-test API check found the variable `false`, the run `cancelled`, and
[issue 57](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/issues/57) open with no labels
or comments. The run had already reached `safe_outputs`; that job was cancelled. This confirms that
changing the variable does not terminate an existing execution and that explicit cancellation is
required.

- `switch-false.png`: phone screenshot of the variable value.
- `run-cancelled.png`: phone screenshot showing cancellation by `@waiyeeyuen`.
- `verification.json`: timestamps, hashes and the compact post-test API result.
