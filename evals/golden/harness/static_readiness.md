# Part B static readiness

Static contract: PASS. Live execution: **NOT READY / NOT AUTHORIZED**.

| Check | Result |
|---|---|
| expected_commit_precedes_builder | pass |
| compiled_strict_v1_0_1 | pass |
| exact_gpt_4_1_main_model | pass |
| deterministic_detection_has_no_model | pass |
| issue_opened_and_dispatch_triggers | pass |
| kill_switch_in_source_and_lock | pass |
| explicit_agent_read_permissions | pass |
| network_defaults_firewall | pass |
| per_issue_concurrency | pass |
| budget_caps | pass |
| generic_github_mcp_is_disabled | pass |
| safe_output_tools_only | pass |
| safe_output_admission_default_false | pass |
| exact_no_argument_wrapper_allowlist | pass |
| pinned_credentialless_detection_checkout_precedes_validator | pass |
| label_and_comment_limits | pass |
| mentions_domains_references_blocked | pass |
| compiled_has_only_label_comment_mutations | pass |
| skill_marker_required | pass |
| all_21_expected_label_sets_pass_validator | pass |
| expected_duplicate_is_in_top_five | pass |

The duplicate target is present but ranks fourth in the deterministic top five; model judgement must still select it.

## Live blockers

- This no-credit repair round authorizes no workflow dispatch or issue replay; no model run may be triggered.
- GitHub CLI authentication must be valid before remote preflight.
- COPILOT_GITHUB_TOKEN secret presence and validity must be confirmed.
- TRIAGE_AGENT_ENABLED must remain false until that approval, then be set true only for the single approved run.
- A Builder-owned no-skill control variant does not exist.
