#!/usr/bin/env python3
"""Run the submitted golden scorer against holdout captures without modifying it."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOLDOUT = ROOT / "evals" / "holdout"
HARNESS = ROOT / "evals" / "golden" / "harness"
sys.path.insert(0, str(HARNESS))

import score_proposals  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    selection = read_json(HOLDOUT / "selection.json")["selected"]
    expected = read_json(HOLDOUT / "expected.json")["historical_cases"]
    expected_by_id = {row["case_id"]: row for row in expected}
    plan = {
        "schema_version": 1,
        "cases": [
            {"case_id": f"airflow-{row['number']}", "expected": expected_by_id[f"airflow-{row['number']}"]}
            for row in selection
        ],
    }
    (HOLDOUT / "replay_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    score_proposals.HARNESS = HOLDOUT
    sys.argv = ["score_proposals.py", "--round-dir", str(HOLDOUT / "actual")]
    score_proposals.main()


if __name__ == "__main__":
    main()
