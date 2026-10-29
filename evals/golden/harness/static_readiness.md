# Part B static readiness

Static contract: PASS. Live execution: **NOT READY / NOT AUTHORIZED**.

| Check | Result |
|---|---|
| expected_commit_precedes_builder | pass |
| compiled_strict_v1_0_1 | pass |
| issue_opened_and_dispatch_triggers | pass |
| kill_switch_in_source_and_lock | pass |
| explicit_agent_read_permissions | pass |
| network_defaults_firewall | pass |
| per_issue_concurrency | pass |
| budget_caps | pass |
| github_mcp_is_read_only | pass |
| safe_output_tools_only | pass |
| three_script_bash_allowlist | pass |
| label_and_comment_limits | pass |
| mentions_domains_references_blocked | pass |
| compiled_has_only_label_comment_mutations | pass |
| skill_marker_required | pass |
| all_21_expected_label_sets_pass_validator | pass |
| expected_duplicate_is_in_top_five | pass |

The duplicate target is present but ranks fourth in the deterministic top five; model judgement must still select it.

## Live blockers

- Jasmine has not approved the first credit-spending run.
- GitHub CLI authentication must be valid before remote preflight.
- COPILOT_GITHUB_TOKEN secret presence and validity must be confirmed.
- TRIAGE_AGENT_ENABLED must remain false/unset until approval, then be set true for an approved run.
- A Builder-owned no-skill control variant does not exist.
