#!/usr/bin/env python3
"""Build the deterministic chronological Part B replay plan without GitHub writes."""

from __future__ import annotations

from common import BUILDER_COMMIT, EXPECTED_COMMIT, GOLDEN, HARNESS, input_path, read_json, sha256_file, validate_replay_text, write_json


def main() -> None:
    expected = read_json(GOLDEN / "expected.json")
    expected_by_id = {
        item["case_id"]: item
        for item in expected["historical_cases"] + expected["adversarial_cases"]
    }
    selected = read_json(GOLDEN / "selection.json")["selected"]
    ordered_ids = [f"airflow-{item['number']}" for item in selected]
    ordered_ids.extend(item["case_id"] for item in expected["adversarial_cases"])
    cases = []
    for order, case_id in enumerate(ordered_ids, 1):
        path = input_path(case_id)
        data = read_json(path)
        validate_replay_text(data)
        oracle = expected_by_id[case_id]
        cases.append(
            {
                "order": order,
                "case_id": case_id,
                "kind": "historical" if case_id.startswith("airflow-") else "adversarial",
                "input_path": path.relative_to(GOLDEN.parent.parent).as_posix(),
                "event_time": data.get("event_time"),
                "title": data["title"],
                "labels_at_creation": data.get("labels_at_creation", []),
                "input_sha256": sha256_file(path),
                "expected": {
                    "labels_to_add": oracle["labels_to_add"],
                    "duplicate_of": oracle["duplicate_of"],
                    "should_comment": oracle["should_comment"],
                    "comment_type": oracle["comment_type"],
                },
            }
        )
    plan = {
        "schema_version": 1,
        "repository": "waiyeeyuen/airflow-agentic-triage-sandbox",
        "builder_commit": BUILDER_COMMIT,
        "expected_commit": EXPECTED_COMMIT,
        "expected_sha256": sha256_file(GOLDEN / "expected.json"),
        "historical_count": 18,
        "adversarial_count": 3,
        "maximum_ai_credits_for_plan": 525,
        "maximum_cost_usd_at_one_cent_per_aic": 21.0,
        "cases": cases,
    }
    write_json(HARNESS / "replay_plan.json", plan)
    print(f"planned {len(cases)} cases; first={cases[0]['case_id']}; no GitHub writes")


if __name__ == "__main__":
    main()
