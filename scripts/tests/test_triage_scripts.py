import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from render_comment import MARKER, render
from search_duplicates import rank
from validate_labels import validate


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


if __name__ == "__main__":
    unittest.main()
