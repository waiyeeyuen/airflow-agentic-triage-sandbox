#!/usr/bin/env python3
"""Validate every frozen oracle against deterministic boundaries without inference."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import GOLDEN, ROOT, adversarial_path, input_path, read_json, write_json

sys.path.insert(0, str(ROOT / "scripts"))
from render_comment import render  # noqa: E402
from validate_labels import validate  # noqa: E402
from validate_safe_outputs import check  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="evals/golden/actual/policy_validation_expected_outputs",
    )
    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    expected = read_json(GOLDEN / "expected.json")
    cases = expected["historical_cases"] + expected["adversarial_cases"]
    rows = []
    for oracle in cases:
        case_id = oracle["case_id"]
        path = input_path(case_id)
        case = read_json(path)
        labels = oracle["labels_to_add"]
        current = case.get("current_labels", case.get("labels_at_creation", []))
        label_result = validate(labels, current)

        comment_type = oracle["comment_type"]
        if comment_type == "duplicate_notice":
            body = render(comment_type, duplicate_number=oracle["duplicate_of"])
        else:
            body = render(comment_type)
        items = []
        if labels:
            items.append({"type": "add_labels", "arguments": {"labels": labels}})
        if body:
            items.append({"type": "add_comment", "arguments": {"body": body}})
        safe_result = check({"items": items})
        passed = bool(label_result["valid"] and safe_result["valid"])
        rows.append({
            "case_id": case_id,
            "mode": "deterministic_oracle_validation",
            "input_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "labels": labels,
            "comment_type": comment_type,
            "label_policy_valid": label_result["valid"],
            "safe_output_policy_valid": safe_result["valid"],
            "status": "policy_valid" if passed else "policy_invalid",
            "model_output": "not_run",
        })

    result = {
        "schema_version": 1,
        "mode": "deterministic_oracle_validation",
        "warning": "This validates frozen expected outputs against deterministic policy; it is not a model dry run or decision-accuracy evidence.",
        "total_cases": len(rows),
        "valid_cases": sum(row["status"] == "policy_valid" for row in rows),
        "invalid_cases": sum(row["status"] != "policy_valid" for row in rows),
        "rows": rows,
    }
    write_json(output_dir / "results.json", result)
    lines = [
        "# Policy validation of expected outputs",
        "",
        result["warning"],
        "",
        f"Valid {result['valid_cases']}/{result['total_cases']}; invalid {result['invalid_cases']}.",
        "",
        "| Case | Status | Labels | Comment |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['status']} | {', '.join(row['labels']) or 'none'} | {row['comment_type']} |"
        )
    (output_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("total_cases", "valid_cases", "invalid_cases")}, indent=2))


if __name__ == "__main__":
    main()
