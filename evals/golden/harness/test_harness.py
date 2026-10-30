import sys
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from capture import classify_comment
from common import BUILDER_COMMIT, EXPECTED_COMMIT, GOLDEN, HARNESS, ROOT, read_json, sha256_file, validate_replay_text
from replay import validate_approval, validate_round_directory


class PlanTests(unittest.TestCase):
    def test_plan_is_complete_ordered_and_pinned(self):
        plan = read_json(HARNESS / "replay_plan.json")
        self.assertEqual(21, len(plan["cases"]))
        self.assertEqual(list(range(1, 22)), [item["order"] for item in plan["cases"]])
        self.assertEqual("airflow-69284", plan["cases"][0]["case_id"])
        self.assertEqual("adversarial-mention-link", plan["cases"][-1]["case_id"])
        self.assertEqual(sha256_file(GOLDEN / "expected.json"), plan["expected_sha256"])
        self.assertEqual(BUILDER_COMMIT, plan["builder_commit"])

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

    def test_approval_requires_exact_current_builder_commit(self):
        approval = {
            "approved_by": "Jasmine",
            "approved_at_utc": "2026-10-30T00:00:00Z",
            "scope": ["airflow-69284"],
            "builder_commit": BUILDER_COMMIT,
            "expected_commit": EXPECTED_COMMIT,
            "maximum_ai_credits_approved": 25,
        }
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as directory:
            path = Path(directory) / "approval.json"
            path.write_text(json.dumps(approval), encoding="utf-8")
            self.assertEqual(BUILDER_COMMIT, validate_approval(path, "airflow-69284")["builder_commit"])
            approval["builder_commit"] = "a881dd73f1f8314b6908b5e415180f027e0c2b3a"
            path.write_text(json.dumps(approval), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "tested Builder/oracle commits"):
                validate_approval(path, "airflow-69284")

    def test_current_round_cannot_reuse_round_one_directory(self):
        with self.assertRaisesRegex(ValueError, "Round 1 evidence"):
            validate_round_directory(GOLDEN / "actual" / "round_1")

    def test_stale_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=GOLDEN / "actual") as directory:
            path = Path(directory)
            (path / "replay_manifest.json").write_text(
                json.dumps({"builder_commit": "6251faf", "cases": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "Round 2 Builder commit"):
                validate_round_directory(path)


class CaptureTests(unittest.TestCase):
    def test_comment_classifier(self):
        from render_comment import render

        self.assertEqual("security_route", classify_comment(render("security_route"), None))
        self.assertEqual("duplicate_notice", classify_comment(render("duplicate_notice", 69699), 69699))
        self.assertEqual("none", classify_comment("", None))


if __name__ == "__main__":
    unittest.main()
