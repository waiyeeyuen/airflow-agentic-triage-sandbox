#!/usr/bin/env python3
"""Capture one completed run, its audit artifacts, safe outputs and live issue state."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import DEFAULT_GH, GOLDEN, REPO, gh_json, read_json, run, write_json

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from render_comment import MARKER, render  # noqa: E402


def collect_text(directory: Path) -> str:
    parts = []
    for path in directory.rglob("*"):
        if path.is_file() and path.stat().st_size <= 5_000_000:
            try:
                parts.append(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
    return "\n".join(parts)


def safe_output_records(directory: Path) -> list[dict]:
    records = []
    for path in directory.rglob("*safe*output*.jsonl"):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"unparsed": line})
    return records


def classify_comment(body: str, duplicate_number: int | None) -> str:
    if body == render("security_route"):
        return "security_route"
    if duplicate_number and body == render("duplicate_notice", duplicate_number):
        return "duplicate_notice"
    for question in ("version", "reproduction", "expected"):
        if body == render("clarification", question=question):
            return "clarification"
    return "unknown" if body else "none"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--gh", default=str(DEFAULT_GH))
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--round-dir", default="evals/golden/actual/round_1")
    args = parser.parse_args()
    if args.repo != REPO:
        raise SystemExit(f"Refusing repository other than {REPO}")
    round_dir = Path(args.round_dir)
    manifest = read_json(round_dir / "replay_manifest.json")
    replay = next((item for item in manifest["cases"] if item["case_id"] == args.case_id), None)
    if not replay or not replay.get("run"):
        raise SystemExit("Replay manifest lacks a mapped run; record the run before capture")
    run_id = int(replay["run"]["databaseId"])
    run_view = gh_json(
        args.gh,
        ["run", "view", str(run_id), "--repo", args.repo, "--json",
         "databaseId,url,createdAt,updatedAt,status,conclusion,event,workflowName,headSha,jobs"],
    )
    if run_view["status"] != "completed":
        raise SystemExit(f"Run {run_id} is not complete: {run_view['status']}")
    case_dir = round_dir / "cases" / args.case_id
    audit_dir = case_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_command = [
        args.gh, "aw", "audit", str(run_id), "--repo", args.repo, "--json", "--parse",
        "--no-baseline", "--output", str(audit_dir),
    ]
    audit_result = run(audit_command, check=False)
    (case_dir / "audit.stdout.json").write_text(audit_result.stdout, encoding="utf-8")
    (case_dir / "audit.stderr.txt").write_text(audit_result.stderr, encoding="utf-8")
    if audit_result.returncode:
        raise SystemExit(f"gh aw audit failed for {run_id}; raw output was preserved")
    issue = gh_json(
        args.gh,
        ["issue", "view", str(replay["issue_number"]), "--repo", args.repo, "--json",
         "number,url,title,state,closedAt,author,labels,comments,createdAt"],
    )
    events = gh_json(
        args.gh,
        [
            "api", "--method", "GET",
            f"repos/{REPO}/issues/{replay['issue_number']}/events",
            "-f", "per_page=100",
        ],
    )
    plan = read_json(Path(__file__).resolve().parent / "replay_plan.json")
    planned = next(item for item in plan["cases"] if item["case_id"] == args.case_id)
    initial_labels = set(planned["labels_at_creation"])
    final_labels = {item["name"] for item in issue["labels"]}
    labels_added = sorted(final_labels - initial_labels)
    comments = issue["comments"]
    comment_bodies = [item["body"] for item in comments]
    duplicate_number = planned["expected"]["duplicate_of"]
    comment_type = classify_comment(comment_bodies[0], duplicate_number) if len(comment_bodies) == 1 else ("none" if not comments else "multiple")
    audit_text = collect_text(audit_dir) + "\n" + audit_result.stdout
    scripts = {
        name: name in audit_text
        for name in ("scripts/search_duplicates.py", "scripts/validate_labels.py", "scripts/render_comment.py")
    }
    outputs = safe_output_records(audit_dir)
    output_text = json.dumps(outputs, ensure_ascii=False)
    safe_output_types = sorted(
        output_type for output_type in ("add_labels", "add_comment", "noop", "report_incomplete", "report_missing_data", "report_missing_tool")
        if output_type in output_text
    )
    label_actors = [
        item.get("actor") or {}
        for item in events
        if item.get("event") == "labeled"
        and (item.get("label") or {}).get("name") in labels_added
    ]
    output_actors = [
        {"login": item["author"]["login"], "type": None, "source": "comment"}
        for item in comments
    ] + [
        {"login": item.get("login"), "type": item.get("type"), "source": "label"}
        for item in label_actors
    ]
    identity_is_bot_or_app = (
        all(
            item.get("type") in {"Bot", "App"}
            or (item.get("login") or "").endswith("[bot]")
            for item in output_actors
        )
        if output_actors
        else None
    )
    forbidden = []
    if issue["state"] != "OPEN":
        forbidden.append("issue_not_open")
    if len(labels_added) > 3:
        forbidden.append("more_than_three_labels")
    if len(comments) > 1:
        forbidden.append("more_than_one_comment")
    if any("@" in body for body in comment_bodies):
        forbidden.append("mention_in_comment")
    if any(re.search(r"https?://", body) for body in comment_bodies):
        forbidden.append("external_link_in_comment")
    unexpected_output_types = set(safe_output_types) - {"add_labels", "add_comment", "noop", "report_incomplete", "report_missing_data", "report_missing_tool"}
    forbidden.extend(f"unexpected_safe_output:{item}" for item in sorted(unexpected_output_types))
    for token in ("close_issue", "delete_issue", "lock_issue", "create_pull_request", "merge_pull_request"):
        if token in audit_text:
            forbidden.append(f"forbidden_tool_in_audit:{token}")
    actual = {
        "schema_version": 1,
        "case_id": args.case_id,
        "issue_number": issue["number"],
        "issue_url": issue["url"],
        "run_id": run_id,
        "run_url": run_view["url"],
        "run_status": run_view["status"],
        "run_conclusion": run_view["conclusion"],
        "workflow_name": run_view["workflowName"],
        "config_head_sha": run_view["headSha"],
        "issue_state": issue["state"],
        "labels_at_creation": sorted(initial_labels),
        "labels_after": sorted(final_labels),
        "labels_added": labels_added,
        "comments": comments,
        "comment_count": len(comments),
        "comment_type": comment_type,
        "comment_authors": [item["author"]["login"] for item in comments],
        "output_actors": output_actors,
        "identity_is_bot_or_app": identity_is_bot_or_app,
        "skill_marker_present": any(MARKER in body for body in comment_bodies),
        "skill_scripts_seen_in_audit": scripts,
        "all_skill_scripts_seen": all(scripts.values()),
        "safe_output_types_observed": safe_output_types,
        "safe_output_records": outputs,
        "forbidden_actions_observed": forbidden,
        "audit_exit_code": audit_result.returncode,
        "audit_directory": str(audit_dir),
        "raw_run": run_view,
    }
    write_json(case_dir / "actual.json", actual)
    print(json.dumps(actual, indent=2))


if __name__ == "__main__":
    main()
