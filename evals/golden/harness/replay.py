#!/usr/bin/env python3
"""Open one approved sandbox replay issue and map its new workflow run."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from common import (
    BUILDER_COMMIT,
    DEFAULT_GH,
    DEFAULT_ROUND_DIR,
    EXPECTED_COMMIT,
    GOLDEN,
    HARNESS,
    REPO,
    ROUND_ONE_DIR,
    ROOT,
    gh_json,
    read_json,
    run,
    sha256_file,
    validate_replay_text,
    write_json,
)


def validate_approval(path: Path, case_id: str) -> dict:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("The real approval file must remain outside the repository")
    approval = read_json(path)
    if approval.get("approved_by") != "Jasmine":
        raise ValueError("Approval must be recorded as directly provided by Jasmine")
    if approval.get("approved_at_utc") in (None, "", "REPLACE_AFTER_DIRECT_APPROVAL"):
        raise ValueError("Approval timestamp is missing")
    if case_id not in approval.get("scope", []):
        raise ValueError(f"Approval scope does not include {case_id}")
    if approval.get("builder_commit") != BUILDER_COMMIT or approval.get("expected_commit") != EXPECTED_COMMIT:
        raise ValueError("Approval is not pinned to the tested Builder/oracle commits")
    if int(approval.get("maximum_ai_credits_approved", 0)) != 100:
        raise ValueError("Approval must be scoped to exactly the configured 100-AIC per-run cap")
    return approval


def validate_round_directory(path: Path) -> Path:
    """Reject historical/stale output before any remote preflight or issue write."""
    resolved = path.resolve()
    round_one = ROUND_ONE_DIR.resolve()
    if resolved == round_one or round_one in resolved.parents:
        raise ValueError("Round 2 cannot write to or reuse the Round 1 evidence directory")
    manifest_path = resolved / "replay_manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        if manifest.get("builder_commit") != BUILDER_COMMIT:
            raise ValueError("Replay manifest is not pinned to the approved Round 2 Builder commit")
    return resolved


def recent_runs(gh: str) -> list[dict]:
    return gh_json(
        gh,
        [
            "run", "list", "--repo", REPO, "--workflow", "issue-triage.lock.yml",
            "--event", "issues", "--limit", "50", "--json",
            "databaseId,url,createdAt,status,conclusion,displayTitle,headSha",
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--gh", default=str(DEFAULT_GH))
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--round-dir", default=str(DEFAULT_ROUND_DIR))
    parser.add_argument("--approval-file")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.repo != REPO:
        raise SystemExit(f"Refusing repository other than private sandbox {REPO}")
    plan = read_json(HARNESS / "replay_plan.json")
    planned = next((item for item in plan["cases"] if item["case_id"] == args.case_id), None)
    if not planned:
        raise SystemExit(f"Case is not in frozen plan: {args.case_id}")
    case_path = GOLDEN.parent.parent / planned["input_path"]
    data = read_json(case_path)
    validate_replay_text(data)
    preview = {
        "mode": "execute" if args.execute else "plan-only",
        "case_id": args.case_id,
        "repository": args.repo,
        "title": data["title"],
        "labels_at_creation": data.get("labels_at_creation", []),
        "maximum_ai_credits": 100,
    }
    if not args.execute:
        print(json.dumps(preview, indent=2))
        return
    if not args.approval_file:
        raise SystemExit("--execute requires --approval-file created only after Jasmine's direct approval")
    approval = validate_approval(Path(args.approval_file), args.case_id)
    try:
        round_dir = validate_round_directory(Path(args.round_dir))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    if sha256_file(GOLDEN / "expected.json") != plan["expected_sha256"]:
        raise SystemExit("Frozen expected.json hash changed")
    run(["git", "merge-base", "--is-ancestor", BUILDER_COMMIT, "HEAD"])
    run([args.gh, "auth", "status"])
    repository = gh_json(args.gh, ["repo", "view", args.repo, "--json", "nameWithOwner,visibility"])
    if repository != {"nameWithOwner": REPO, "visibility": "PRIVATE"}:
        raise SystemExit(f"Repository preflight failed: {repository}")
    variable = run([args.gh, "variable", "get", "TRIAGE_AGENT_ENABLED", "--repo", args.repo]).stdout.strip()
    if variable.lower() != "true":
        raise SystemExit("TRIAGE_AGENT_ENABLED must be exactly true for an approved AI run")
    secrets = gh_json(args.gh, ["secret", "list", "--repo", args.repo, "--json", "name"])
    if "COPILOT_GITHUB_TOKEN" not in {item["name"] for item in secrets}:
        raise SystemExit("Required COPILOT_GITHUB_TOKEN secret is absent")
    labels = gh_json(args.gh, ["label", "list", "--repo", args.repo, "--limit", "1000", "--json", "name"])
    missing = set(data.get("labels_at_creation", [])) - {item["name"] for item in labels}
    if missing:
        raise SystemExit(f"Sandbox labels missing: {sorted(missing)}")
    manifest_path = round_dir / "replay_manifest.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {
        "schema_version": 1,
        "builder_commit": BUILDER_COMMIT,
        "expected_commit": EXPECTED_COMMIT,
        "cases": [],
    }
    existing_ids = {item["case_id"] for item in manifest["cases"]}
    if args.case_id in existing_ids:
        raise SystemExit("Case already replayed in this round")
    previous = [item["case_id"] for item in plan["cases"] if item["order"] < planned["order"]]
    if any(case_id not in existing_ids for case_id in previous):
        raise SystemExit("Historical/adversarial cases must be replayed in frozen plan order")
    known_runs = {item["databaseId"] for item in recent_runs(args.gh)}
    started = datetime.now(timezone.utc).isoformat()
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as handle:
        handle.write(data.get("body") or "")
        body_path = Path(handle.name)
    try:
        command = [args.gh, "issue", "create", "--repo", args.repo, "--title", data["title"], "--body-file", str(body_path)]
        for label in data.get("labels_at_creation", []):
            command.extend(["--label", label])
        issue_url = run(command).stdout.strip().splitlines()[-1]
    finally:
        body_path.unlink(missing_ok=True)
    issue_number = int(issue_url.rstrip("/").split("/")[-1])
    mapped_run = None
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        candidates = [item for item in recent_runs(args.gh) if item["databaseId"] not in known_runs]
        if candidates:
            mapped_run = sorted(candidates, key=lambda item: item["createdAt"])[0]
            break
        time.sleep(5)
    record = {
        "case_id": args.case_id,
        "plan_order": planned["order"],
        "input_path": planned["input_path"],
        "issue_number": issue_number,
        "issue_url": issue_url,
        "opened_at_utc": started,
        "run": mapped_run,
        "approval": approval,
    }
    manifest["builder_commit"] = BUILDER_COMMIT
    manifest["expected_commit"] = EXPECTED_COMMIT
    manifest["cases"].append(record)
    write_json(manifest_path, manifest)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
