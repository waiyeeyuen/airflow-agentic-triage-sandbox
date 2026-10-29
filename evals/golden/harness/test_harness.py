import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from capture import classify_comment
from common import GOLDEN, HARNESS, read_json, sha256_file, validate_replay_text
from replay import validate_approval


class PlanTests(unittest.TestCase):
    def test_plan_is_complete_ordered_and_pinned(self):
        plan = read_json(HARNESS / "replay_plan.json")
        self.assertEqual(21, len(plan["cases"]))
        self.assertEqual(list(range(1, 22)), [item["order"] for item in plan["cases"]])
        self.assertEqual("airflow-69284", plan["cases"][0]["case_id"])
        self.assertEqual("adversarial-mention-link", plan["cases"][-1]["case_id"])
        self.assertEqual(sha256_file(GOLDEN / "expected.json"), plan["expected_sha256"])

    def test_every_planned_input_is_neutralised(self):
        plan = read_json(HARNESS / "replay_plan.json")
        root = GOLDEN.parent.parent
        for item in plan["cases"]:
            validate_replay_text(read_json(root / item["input_path"]))

    def test_example_is_not_accepted_as_approval(self):
        with self.assertRaises(ValueError):
            validate_approval(HARNESS / "approval.example.json", "airflow-69284")

    def test_real_approval_cannot_live_in_repository(self):
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            validate_approval(HARNESS / "approval.example.json", "airflow-69284")


class CaptureTests(unittest.TestCase):
    def test_comment_classifier(self):
        from render_comment import render

        self.assertEqual("security_route", classify_comment(render("security_route"), None))
        self.assertEqual("duplicate_notice", classify_comment(render("duplicate_notice", 69699), 69699))
        self.assertEqual("none", classify_comment("", None))


if __name__ == "__main__":
    unittest.main()
