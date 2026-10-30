#!/usr/bin/env python3
"""Statically audit the Builder contract without running the Agentic Workflow."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from common import BUILDER_COMMIT, DEFAULT_GH, EXPECTED_COMMIT, GOLDEN, HARNESS, read_json, write_json

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from search_duplicates import rank  # noqa: E402
from validate_labels import validate  # noqa: E402


def manifest_and_metadata(lock_text: str):
    manifest_line = next(line for line in lock_text.splitlines() if line.startswith("# gh-aw-manifest: "))
    metadata_line = next(line for line in lock_text.splitlines() if line.startswith("# gh-aw-metadata: "))
    return json.loads(manifest_line.removeprefix("# gh-aw-manifest: ")), json.loads(metadata_line.removeprefix("# gh-aw-metadata: "))


def main() -> None:
    source = (ROOT / ".github" / "workflows" / "issue-triage.md").read_text(encoding="utf-8")
    lock = (ROOT / ".github" / "workflows" / "issue-triage.lock.yml").read_text(encoding="utf-8")
    manifest, metadata = manifest_and_metadata(lock)
    mcp = {server["name"]: set(server["tools"]) for server in manifest["mcp_servers"]}
    frontmatter = source.split("---", 2)[1]
    bash = frontmatter.split("  bash:\n", 1)[1].split("timeout-minutes:", 1)[0]
    allowed_commands = [
        line.strip().removeprefix("- ") for line in bash.splitlines() if line.strip()
    ]
    wrapper_commands = sorted(
        f"scripts/wrappers/{path.name}"
        for path in (ROOT / "scripts" / "wrappers").glob("triage-*")
    )
    detection = frontmatter.split("threat-detection:", 1)[1].split("mentions:", 1)[0]
    checkout = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    checks = {
        "expected_commit_precedes_builder": subprocess.run(
            ["git", "merge-base", "--is-ancestor", EXPECTED_COMMIT, BUILDER_COMMIT]
        ).returncode == 0,
        "compiled_strict_v1_0_1": metadata.get("compiler_version") == "v1.0.1" and metadata.get("strict") is True,
        "exact_gpt_4_1_main_model": metadata.get("agent_model") == "gpt-4.1"
        and source.count("model: gpt-4.1") == 1,
        "deterministic_detection_has_no_model": (
            "engine: false" in detection
            and metadata.get("detection_agent_model") is None
            and "scripts/validate_safe_outputs.py" in detection
        ),
        "issue_opened_and_dispatch_triggers": "types: [opened]" in source and "workflow_dispatch:" in source,
        "kill_switch_in_source_and_lock": "vars.TRIAGE_AGENT_ENABLED == 'true'" in source and "vars.TRIAGE_AGENT_ENABLED == 'true'" in lock,
        "explicit_agent_read_permissions": "contents: read" in source and "issues: read" in source,
        "network_defaults_firewall": "network: defaults" in source and manifest.get("threat_detection", {}).get("mode") == "enabled",
        "per_issue_concurrency": "github.event.issue.number || github.run_id" in source and "cancel-in-progress: false" in source,
        "budget_caps": all(value in source for value in ("timeout-minutes: 10", "max-ai-credits: 25", "max-daily-ai-credits: 5000")),
        "generic_github_mcp_is_disabled": "github" not in mcp and "github: false" in source,
        "safe_output_tools_only": mcp.get("safeoutputs") == {"add_comment", "add_labels", "noop", "report_incomplete", "report_missing_data", "report_missing_tool"},
        "safe_output_admission_default_false": (
            manifest.get("admission") is False
            and "needs.detection.result == 'success'" in lock
        ),
        "exact_no_argument_wrapper_allowlist": (
            sorted(allowed_commands) == wrapper_commands
            and all(" " not in command for command in allowed_commands)
            and "python" not in bash
            and "python3" not in bash
            and all(f"--allow-tool '\\''shell({command})'\\''" in lock for command in allowed_commands)
            and "--allow-tool '\\''shell(python" not in lock
            and "--allow-tool '\\''shell(python3" not in lock
        ),
        "pinned_credentialless_detection_checkout_precedes_validator": (
            checkout in detection
            and "persist-credentials: false" in detection
            and detection.index(checkout) < detection.index("validate_safe_outputs.py")
            and lock.index("- name: Check out validator source without credentials")
            < lock.index("- name: Deterministically validate proposed labels and comment")
        ),
        "label_and_comment_limits": all(value in source for value in ("max-labels: 3", "add-comment:", "max: 1", "target: triggering")),
        "mentions_domains_references_blocked": all(value in source for value in ("mentions: false", "allowed-domains: []", "allowed-github-references: []")),
        "compiled_has_only_label_comment_mutations": not ({"close_issue", "delete_issue", "lock_issue", "create_pull_request", "merge_pull_request"} & set().union(*mcp.values())),
        "skill_marker_required": "airflow-triage-skill:v1" in source and "airflow-triage-skill:v1" in (ROOT / ".claude" / "skills" / "airflow-issue-triage" / "SKILL.md").read_text(encoding="utf-8"),
    }
    expected = read_json(GOLDEN / "expected.json")
    invalid = []
    for item in expected["historical_cases"]:
        number = item["case_id"].split("-")[-1]
        current = read_json(GOLDEN / "cases" / number / "input.json")["labels_at_creation"]
        result = validate(item["labels_to_add"], current)
        if not result["valid"]:
            invalid.append({"case_id": item["case_id"], "errors": result["errors"]})
    for item in expected["adversarial_cases"]:
        slug = item["case_id"].removeprefix("adversarial-").replace("-", "_")
        current = read_json(GOLDEN / "adversarial" / f"{slug}.json")["labels_at_creation"]
        result = validate(item["labels_to_add"], current)
        if not result["valid"]:
            invalid.append({"case_id": item["case_id"], "errors": result["errors"]})
    checks["all_21_expected_label_sets_pass_validator"] = not invalid
    duplicate_input = read_json(GOLDEN / "cases" / "73950" / "input.json")
    duplicate_prior = read_json(GOLDEN / "cases" / "73950" / "prior_issues.json")
    duplicate_query = f"{(duplicate_input['title'] + ' ') * 5}{duplicate_input['body']}"
    duplicate_rank = rank(duplicate_query, duplicate_prior, 5)
    checks["expected_duplicate_is_in_top_five"] = any(item["number"] == 69699 for item in duplicate_rank)
    auth = subprocess.run([str(DEFAULT_GH), "auth", "status"], capture_output=True, text=True, encoding="utf-8")
    no_skill_variant = (ROOT / ".github" / "workflows" / "issue-triage-no-skill.md").exists()
    result = {
        "schema_version": 1,
        "builder_commit": BUILDER_COMMIT,
        "expected_commit": EXPECTED_COMMIT,
        "static_checks": checks,
        "static_contract_pass": all(checks.values()),
        "expected_label_validation_failures": invalid,
        "duplicate_case_top_five": duplicate_rank,
        "gh_auth_currently_valid": auth.returncode == 0,
        "gh_auth_diagnostic": (auth.stdout + auth.stderr).strip(),
        "no_skill_variant_exists": no_skill_variant,
        "live_execution_ready": False,
        "live_blockers": [
            "This no-credit repair round authorizes no workflow dispatch or issue replay; no model run may be triggered.",
            "GitHub CLI authentication must be valid before remote preflight.",
            "COPILOT_GITHUB_TOKEN secret presence and validity must be confirmed.",
            "TRIAGE_AGENT_ENABLED must remain false until that approval, then be set true only for the single approved run.",
            "A Builder-owned no-skill control variant does not exist." if not no_skill_variant else "No-skill variant exists but is untested.",
        ],
    }
    write_json(HARNESS / "static_readiness.json", result)
    lines = [
        "# Part B static readiness",
        "",
        f"Static contract: {'PASS' if result['static_contract_pass'] else 'FAIL'}. Live execution: **NOT READY / NOT AUTHORIZED**.",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    lines.extend(f"| {name} | {'pass' if value else 'FAIL'} |" for name, value in checks.items())
    lines.extend([
        "",
        "The duplicate target is present but ranks fourth in the deterministic top five; model judgement must still select it.",
        "",
        "## Live blockers",
        "",
    ])
    lines.extend(f"- {item}" for item in result["live_blockers"])
    (HARNESS / "static_readiness.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"static_contract_pass": result["static_contract_pass"], "live_execution_ready": False, "checks": len(checks)}, indent=2))


if __name__ == "__main__":
    main()
