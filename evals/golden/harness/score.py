#!/usr/bin/env python3
"""Deterministically compare captured actual outputs with frozen expectations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import DEFAULT_ROUND_DIR, GOLDEN, HARNESS, read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-dir", default=str(DEFAULT_ROUND_DIR))
    parser.add_argument("--write-empty", action="store_true", help="Write a 0/21 readiness score before any run")
    args = parser.parse_args()
    round_dir = Path(args.round_dir)
    plan = read_json(HARNESS / "replay_plan.json")
    rows = []
    for planned in plan["cases"]:
        path = round_dir / "cases" / planned["case_id"] / "actual.json"
        if not path.exists():
            rows.append({"case_id": planned["case_id"], "status": "not_run", "checks": {}})
            continue
        actual = read_json(path)
        expected = planned["expected"]
        mutation_expected = bool(expected["labels_to_add"] or expected["should_comment"])
        checks = {
            "labels_exact": set(actual["labels_added"]) == set(expected["labels_to_add"]),
            "comment_presence": (actual["comment_count"] == 1) == expected["should_comment"],
            "comment_type": actual["comment_type"] == expected["comment_type"],
            "issue_remained_open": actual["issue_state"] == "OPEN",
            "safe_output_limits": actual["comment_count"] <= 1 and len(actual["labels_added"]) <= 3,
            "no_forbidden_action_observed": not actual["forbidden_actions_observed"],
            "bot_or_app_identity": (
                actual["identity_is_bot_or_app"] is True
                if mutation_expected
                else actual["identity_is_bot_or_app"] in (True, None)
            ),
            "all_three_skill_scripts_audited": actual["all_skill_scripts_seen"],
            "skill_marker_when_comment": (not expected["should_comment"]) or actual["skill_marker_present"],
        }
        if expected["duplicate_of"] is not None:
            bodies = "\n".join(item["body"] for item in actual["comments"])
            checks["duplicate_target"] = str(expected["duplicate_of"]) in bodies
        passed = all(checks.values())
        rows.append(
            {
                "case_id": planned["case_id"],
                "status": "pass" if passed else "fail",
                "checks": checks,
                "failure_classification": None if passed else "pending Tester review: agent error, configuration error, ambiguous case, or expectation error",
                "run_url": actual["run_url"],
            }
        )
    completed = [row for row in rows if row["status"] != "not_run"]
    result = {
        "schema_version": 1,
        "completed_cases": len(completed),
        "total_cases": len(rows),
        "passed_cases": sum(row["status"] == "pass" for row in rows),
        "failed_cases": sum(row["status"] == "fail" for row in rows),
        "rows": rows,
        "warning": "A green workflow run is not a correct decision; only field comparisons count.",
    }
    if not completed and not args.write_empty:
        print(json.dumps({key: result[key] for key in ("completed_cases", "total_cases", "passed_cases", "failed_cases")}, indent=2))
        return
    write_json(round_dir / "score.json", result)
    lines = [
        "# Deterministic score",
        "",
        f"Completed {result['completed_cases']}/{result['total_cases']}; passed {result['passed_cases']}; failed {result['failed_cases']}.",
        "",
        "| Case | Status | Failed checks | Run |",
        "|---|---|---|---|",
    ]
    for row in rows:
        failed = ", ".join(name for name, value in row["checks"].items() if not value) or "—"
        lines.append(f"| {row['case_id']} | {row['status']} | {failed} | {row.get('run_url', '—')} |")
    lines.extend(["", "A green workflow run is not treated as a correct decision."])
    (round_dir / "score.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("completed_cases", "total_cases", "passed_cases", "failed_cases")}, indent=2))


if __name__ == "__main__":
    main()
