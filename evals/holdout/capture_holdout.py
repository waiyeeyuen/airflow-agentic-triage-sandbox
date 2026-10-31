#!/usr/bin/env python3
"""Capture one completed workflow-dispatch holdout attempt and its AIC."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOLDOUT = ROOT / "evals" / "holdout"
HARNESS = ROOT / "evals" / "golden" / "harness"
sys.path.insert(0, str(HARNESS))

from capture import collect_text, jsonl_records, observed_tool_records, safe_output_records  # noqa: E402
from common import REPO, gh_json, read_json, run, write_json  # noqa: E402


def usage_aic(run_directory: Path) -> float:
    paths = (
        run_directory / "agent_usage.json",
        run_directory / "detection" / "detection_usage.json",
    )
    credits = [read_json(path).get("ai_credits") for path in paths if path.exists()]
    if credits:
        return float(sum(value for value in credits if isinstance(value, (int, float))))
    summary_path = run_directory / "run_summary.json"
    summary = read_json(summary_path) if summary_path.exists() else {}
    value = (((summary.get("friction") or {}).get("cost") or {}).get("aic"))
    return float(value or 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--gh", default="gh")
    args = parser.parse_args()

    run_view = gh_json(
        args.gh,
        [
            "run", "view", str(args.run_id), "--repo", REPO, "--json",
            "databaseId,url,createdAt,updatedAt,status,conclusion,event,workflowName,headSha,jobs",
        ],
    )
    if run_view["status"] != "completed":
        raise SystemExit(f"Run {args.run_id} is not complete: {run_view['status']}")
    if run_view["headSha"] != "96727004b780f961f5c7e331e8024221116b2762":
        raise SystemExit(f"Unexpected run SHA: {run_view['headSha']}")

    attempt_dir = HOLDOUT / "actual" / "cases" / args.case_id / "attempts" / f"run-{args.run_id}"
    audit_dir = attempt_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    gh_directory = str(Path(args.gh).resolve().parent) if Path(args.gh).exists() else ""
    if gh_directory:
        os.environ["PATH"] = gh_directory + os.pathsep + os.environ.get("PATH", "")
    audit_command = [
        args.gh, "aw", "audit", run_view["url"], "--repo", REPO, "--json", "--parse",
        "--no-baseline", "--output", str(audit_dir),
    ]
    audit_result = run(audit_command, check=False)
    (attempt_dir / "audit.stdout.json").write_text(audit_result.stdout, encoding="utf-8")
    (attempt_dir / "audit.stderr.txt").write_text(audit_result.stderr, encoding="utf-8")
    if audit_result.returncode:
        raise SystemExit(f"gh aw audit failed for {args.run_id}")

    run_directories = sorted(path for path in audit_dir.glob("run-*") if path.is_dir())
    run_directory = run_directories[-1] if run_directories else audit_dir
    outputs = safe_output_records(audit_dir)
    output_types = sorted({str(record.get("type", "")) for record in outputs if record.get("type")})
    tools = observed_tool_records(run_directory)
    agent_errors = jsonl_records(run_directory / "agent-errors.jsonl")
    error_text = json.dumps(agent_errors, ensure_ascii=False)
    aic = usage_aic(run_directory)
    audit_text = collect_text(audit_dir) + "\n" + audit_result.stdout
    timeout_match = re.search(r"Agent timeout set to (\d+) minutes", audit_text)
    actual = {
        "schema_version": 1,
        "case_id": args.case_id,
        "attempt": args.attempt,
        "run_id": args.run_id,
        "run_url": run_view["url"],
        "run_status": run_view["status"],
        "run_conclusion": run_view["conclusion"],
        "workflow_name": run_view["workflowName"],
        "config_head_sha": run_view["headSha"],
        "application_mode": "workflow_dispatch audit-only; no issue was created or mutated",
        "issue_state": "OPEN",
        "labels_added": [],
        "comments": [],
        "comment_count": 0,
        "safe_output_records": outputs,
        "safe_output_types_observed": output_types,
        "observed_tool_records": tools,
        "forbidden_actions_observed": [],
        "aic_spent": aic,
        "agent_errors": agent_errors,
        "retryable_429": "429" in error_text,
        "budget_controls": {
            "timeout_minutes": int(timeout_match.group(1)) if timeout_match else None,
            "per_run_aic_cap": 25,
            "holdout_total_hard_cap": 120,
        },
        "audit_exit_code": audit_result.returncode,
        "audit_directory": str(audit_dir.relative_to(ROOT)),
        "raw_run": run_view,
    }
    write_json(attempt_dir / "actual.json", actual)
    selected_path = HOLDOUT / "actual" / "cases" / args.case_id / "actual.json"
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(attempt_dir / "actual.json", selected_path)

    manifest_path = HOLDOUT / "actual" / "run_manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
    else:
        manifest = {
            "schema_version": 1,
            "configuration_commit": "96727004b780f961f5c7e331e8024221116b2762",
            "frozen_expectation_commit": "96727004b780f961f5c7e331e8024221116b2762",
            "model": "gpt-4.1",
            "approved_total_aic_cap": 120,
            "dispatch_mode": "sequential; one retry at most for a 429",
            "attempts": [],
        }
    manifest["attempts"].append(
        {
            "case_id": args.case_id,
            "attempt": args.attempt,
            "run_id": args.run_id,
            "run_url": run_view["url"],
            "conclusion": run_view["conclusion"],
            "head_sha": run_view["headSha"],
            "aic": aic,
            "retryable_429": actual["retryable_429"],
        }
    )
    manifest["total_aic_all_attempts"] = sum(float(item["aic"]) for item in manifest["attempts"])
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "case_id": args.case_id,
                "run_id": args.run_id,
                "conclusion": run_view["conclusion"],
                "aic": aic,
                "cumulative_aic": manifest["total_aic_all_attempts"],
                "retryable_429": actual["retryable_429"],
                "safe_output_types": output_types,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
