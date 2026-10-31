# Proposed-decision score

Exact decisions: 3/8 (37.5%) among decided cases; 2/10 not evaluated: 120-AIC hard-cap admission check left less than the 25-AIC per-run reserve.

Per-field exactness among decided cases (correct absence counts correct): kind 7/8 (87.5%); area 4/8 (50.0%); provider 7/8 (87.5%); comment 7/8 (87.5%).

| Case | Expected labels | Proposed labels | Expected comment | Proposed comment | Must-not proposal | Result | Explanation | Run |
|---|---|---|---|---|---|---|---|---|
| airflow-69262 | area:core | none | none | none | none | fail | labels expected ['area:core'], proposed [] | [41189325042](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41189325042) |
| airflow-70164 | security | none | security_route | none | none | fail | labels expected ['security'], proposed []; comment expected security_route, proposed none | [41190831283](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41190831283) |
| airflow-70232 | area:airflow-ctl | none | none | none | none | fail | labels expected ['area:airflow-ctl'], proposed [] | [41190371870](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41190371870) |
| airflow-70355 | area:providers | none | none | none | none | fail | labels expected ['area:providers'], proposed [] | [41206754817](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41206754817) |
| airflow-70503 | none | none | none | none | none | pass | exact frozen decision | [41207336799](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41207336799) |
| airflow-70631 | kind:feature, area:providers, provider:google | none | none | none | none | fail | labels expected ['kind:feature', 'area:providers', 'provider:google'], proposed [] | [41207830672](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41207830672) |
| airflow-71747 | none | none | none | none | none | pass | exact frozen decision | [41208422149](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41208422149) |
| airflow-72284 | none | none | none | none | none | pass | exact frozen decision | [41208931217](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions/runs/41208931217) |
| airflow-72612 | none | none | none | none | none | not evaluated | no model proposal | [not-run](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions) |
| airflow-73941 | area:providers, provider:fab | none | none | none | none | not evaluated | no model proposal; labels expected ['area:providers', 'provider:fab'], proposed [] | [not-run](https://github.com/waiyeeyuen/airflow-agentic-triage-sandbox/actions) |

Total AIC across all attempts: 101.0540.
