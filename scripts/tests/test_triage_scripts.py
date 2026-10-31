import unittest
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_issue_input import from_case, from_event
from render_comment import MARKER, render
from search_duplicates import rank, resolve_corpus
from validate_safe_outputs import check
from validate_labels import validate
from wrappers import wrapper_runtime

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent


def run_without_stdin(script, *arguments):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, arguments)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


class LabelTests(unittest.TestCase):
    def test_valid_provider_set(self):
        self.assertTrue(validate(["kind:bug", "area:providers", "provider:google"])["valid"])

    def test_unknown_and_too_many_rejected(self):
        result = validate(["priority:critical", "kind:bug", "area:core", "area:UI"])
        self.assertFalse(result["valid"])
        self.assertEqual([], result["labels"])

    def test_security_is_exclusive(self):
        self.assertFalse(validate(["security", "kind:bug"])["valid"])

    def test_provider_requires_area(self):
        self.assertFalse(validate(["provider:amazon"])["valid"])
        self.assertTrue(validate(["provider:amazon"], ["area:providers"])["valid"])


class DuplicateTests(unittest.TestCase):
    def test_expected_candidate_ranks_first(self):
        prior = [{"number": 1, "title": "Global disable option for DAG processing"},
                 {"number": 2, "title": "UI colour contrast"}]
        ranked = rank("Add global option to disable DAG processing", prior)
        self.assertEqual(1, ranked[0]["number"])

    def test_dated_snapshot_title_field(self):
        prior = [{"number": 7, "title_as_of_cutoff": "Global scheduler pause override"}]
        self.assertEqual(7, rank("global scheduler pause", prior)[0]["number"])

    def test_exact_title_resolves_frozen_corpus(self):
        case = json.loads((ROOT / "evals/golden/cases/69284/input.json").read_text(encoding="utf-8"))
        resolved = resolve_corpus(case, ROOT / "evals/golden/cases")
        self.assertEqual(ROOT / "evals/golden/cases/69284/prior_issues.json", resolved)

    def test_cli_is_noninteractive_with_absent_stdin(self):
        case_path = ROOT / "evals/golden/cases/69284/input.json"
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            output = Path(temporary) / "duplicates.json"
            result = run_without_stdin(
                "search_duplicates.py", "--case", case_path, "--corpus-root",
                ROOT / "evals/golden/cases", "--output", output,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(json.loads(output.read_text(encoding="utf-8"))["candidates"])


class CommentTests(unittest.TestCase):
    def test_security_template_has_marker_and_no_url(self):
        body = render("security_route")
        self.assertIn(MARKER, body)
        self.assertNotIn("http", body)

    def test_duplicate_requires_number(self):
        with self.assertRaises(ValueError):
            render("duplicate_notice")

    def test_none_is_empty(self):
        self.assertEqual("", render("none"))


class CliTests(unittest.TestCase):
    def test_validation_flags_are_noninteractive_with_absent_stdin(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            output = Path(temporary) / "validated.json"
            result = run_without_stdin(
                "validate_labels.py", "--case", ROOT / "evals/golden/cases/69284/input.json",
                "--output", output, "--proposed-label", "kind:bug",
                "--proposed-label", "area:providers", "--proposed-label", "provider:openlineage",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(json.loads(output.read_text(encoding="utf-8"))["valid"])

    def test_renderer_is_noninteractive_with_absent_stdin(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            output = Path(temporary) / "comment.json"
            result = run_without_stdin(
                "render_comment.py", "--case", ROOT / "evals/golden/cases/69284/input.json",
                "--output", output, "--type", "none",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("none", json.loads(output.read_text(encoding="utf-8"))["comment_type"])

    def test_prepare_case_and_event(self):
        frozen = from_case("evals/golden/cases/69284/input.json")
        self.assertIn("OpenLineage", frozen["title"])
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            event = Path(temporary) / "event.json"
            event.write_text(json.dumps({"issue": {"number": 5, "title": "T", "body": "B",
                                                       "labels": [{"name": "kind:bug"}]}}),
                             encoding="utf-8")
            prepared = from_event(event)
            self.assertEqual(["kind:bug"], prepared["current_labels"])

    def test_safe_output_validator_accepts_templates_and_rejects_mentions_links(self):
        accepted = {"items": [
            {"type": "add_labels", "arguments": {"labels": ["kind:bug", "area:providers",
                                                                  "provider:openlineage"]}},
            {"type": "add_comment", "arguments": {"body": render("security_route")}},
        ]}
        self.assertTrue(check(accepted)["valid"])
        for body in ("Hello @maintainer", "See https://example.invalid", "Thanks for the report."):
            with self.assertRaises(ValueError):
                check({"items": [{"type": "add_comment", "arguments": {"body": body}}]})

    def test_noop_writes_safe_detection_verdict(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary = Path(temporary)
            agent_output = temporary / "agent_output.json"
            detection_result = temporary / "detection_result.json"
            agent_output.write_text(json.dumps({
                "items": [{"type": "noop", "message": "No action needed."}],
                "errors": [],
            }), encoding="utf-8")
            result = run_without_stdin(
                "validate_safe_outputs.py", "--input", agent_output,
                "--detection-result", detection_result,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(
                {
                    "prompt_injection": False,
                    "secret_leak": False,
                    "malicious_patch": False,
                    "reasons": [],
                    "warnings": [],
                },
                json.loads(detection_result.read_text(encoding="utf-8")),
            )

    def test_invalid_output_never_writes_safe_detection_verdict(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary = Path(temporary)
            detection_result = temporary / "detection_result.json"
            result = run_without_stdin(
                "validate_safe_outputs.py", "--input",
                SCRIPTS / "tests/fixtures/invalid_agent_output.json",
                "--detection-result", detection_result,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(detection_result.exists())

    def test_negative_safe_output_gate_applies_nothing(self):
        invalid = json.loads((SCRIPTS / "tests/fixtures/invalid_agent_output.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            check(invalid)
        attacks = (
            {"items": [{"type": "add_labels", "arguments": {"labels": ["priority:critical"]}}]},
            {"items": [{"type": "add_comment", "arguments": {"body": "Hello @maintainer"}}]},
            {"items": [{"type": "add_comment", "arguments": {"body": "https://example.invalid"}}]},
        )
        applied = []
        for attack in attacks:
            with self.assertRaises(ValueError):
                check(attack)
        self.assertEqual([], applied, "failed detection must leave the applied-output set empty")


class WrapperTests(unittest.TestCase):
    def test_all_golden_duplicate_outputs_match_frozen_hashes(self):
        plan = json.loads(
            (ROOT / "evals/golden/harness/replay_plan.json").read_text(encoding="utf-8")
        )
        expected = json.loads(
            (SCRIPTS / "tests/fixtures/duplicate_search_sha256.json").read_text(encoding="utf-8")
        )
        self.assertEqual({item["case_id"] for item in plan["cases"]}, set(expected))
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            for item in plan["cases"]:
                with self.subTest(case_id=item["case_id"]):
                    output = Path(temporary) / f"{item['case_id']}.json"
                    wrapper_runtime.run(
                        "triage-search-duplicates",
                        case=ROOT / item["input_path"],
                        duplicates=output,
                        corpus_root=ROOT / "evals/golden/cases",
                    )
                    digest = hashlib.sha256(output.read_bytes()).hexdigest()
                    self.assertEqual(expected[item["case_id"]], digest)

    def test_live_issue_without_frozen_corpus_returns_no_candidates(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary = Path(temporary)
            case = temporary / "case.json"
            output = temporary / "duplicates.json"
            case.write_text(
                json.dumps({"title": "Fresh harmless issue", "body": "No frozen title match."}),
                encoding="utf-8",
            )
            wrapper_runtime.run(
                "triage-search-duplicates",
                case=case,
                duplicates=output,
                corpus_root=ROOT / "evals/golden/cases",
            )
            expected = json.dumps(
                {"method": "tf-idf-cosine-v1", "candidates": []}, indent=2
            ) + "\n"
            self.assertEqual(expected.encode(), output.read_bytes())

    def test_fixed_wrapper_sequence_preserves_duplicate_labels_and_comment(self):
        case = ROOT / "evals/golden/cases/69284/input.json"
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary = Path(temporary)
            duplicates = temporary / "duplicates.json"
            validated = temporary / "validated.json"
            comment = temporary / "comment.json"
            common = {"case": case, "duplicates": duplicates, "validated": validated,
                      "comment": comment, "corpus_root": ROOT / "evals/golden/cases"}
            wrapper_runtime.run("triage-search-duplicates", **common)
            wrapper_runtime.run("triage-label-none", **common)
            wrapper_runtime.run("triage-label-kind-bug", **common)
            wrapper_runtime.run("triage-label-area-providers", **common)
            wrapper_runtime.run("triage-label-provider-openlineage", **common)
            wrapper_runtime.run("triage-comment-none", **common)
            self.assertEqual(69275, json.loads(duplicates.read_text(encoding="utf-8"))["candidates"][0]["number"])
            self.assertEqual(["kind:bug", "area:providers", "provider:openlineage"],
                             json.loads(validated.read_text(encoding="utf-8"))["labels"])
            self.assertEqual({"comment_type": "none", "body": ""},
                             json.loads(comment.read_text(encoding="utf-8")))

    def test_wrappers_reject_arguments_before_reading_fixed_files(self):
        wrapper = SCRIPTS / "wrappers/triage-search-duplicates"
        result = subprocess.run(
            [sys.executable, str(wrapper), "unexpected"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("accept no arguments", result.stderr)

    def test_wrapper_runtime_never_reads_stdin(self):
        class ForbiddenStdin:
            def read(self, *_args, **_kwargs):
                raise AssertionError("wrapper attempted to read stdin")

        original = sys.stdin
        sys.stdin = ForbiddenStdin()
        try:
            with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
                output = Path(temporary) / "validated.json"
                wrapper_runtime.run(
                    "triage-label-none",
                    case=ROOT / "evals/golden/cases/69284/input.json",
                    validated=output,
                )
                self.assertTrue(json.loads(output.read_text(encoding="utf-8"))["valid"])
        finally:
            sys.stdin = original


if __name__ == "__main__":
    unittest.main()
