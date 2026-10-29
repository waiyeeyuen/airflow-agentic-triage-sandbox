import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".github" / "workflows" / "issue-triage.md"
LOCK = ROOT / ".github" / "workflows" / "issue-triage.lock.yml"


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.frontmatter = cls.source.split("---", 2)[1]
        cls.lock_lines = LOCK.read_text(encoding="utf-8").splitlines()
        manifest_line = next(
            line for line in cls.lock_lines if line.startswith("# gh-aw-manifest: ")
        )
        cls.manifest = json.loads(manifest_line.removeprefix("# gh-aw-manifest: "))

    def test_source_has_bounded_trigger_permissions_and_budget(self):
        required = (
            "types: [opened]",
            "if: vars.TRIAGE_AGENT_ENABLED == 'true'",
            "contents: read",
            "issues: read",
            "timeout-minutes: 10",
            "max-ai-credits: 100",
            "max-daily-ai-credits: 5000",
            "cancel-in-progress: false",
        )
        for value in required:
            self.assertIn(value, self.frontmatter)

    def test_safe_output_contract_is_labels_and_one_comment_only(self):
        required = (
            "mentions: false",
            "allowed-domains: []",
            "allowed-github-references: []",
            "max-labels: 3",
            "max-links: 1",
            "target: triggering",
        )
        for value in required:
            self.assertIn(value, self.frontmatter)
        for forbidden in (
            "close-issue:",
            "create-pull-request:",
            "merge-pull-request:",
            "push-to-pull-request-branch:",
            "remove-labels:",
            "lock-issue:",
        ):
            self.assertNotIn(forbidden, self.frontmatter)

    def test_compiled_safeoutput_tools_have_no_pr_or_destructive_action(self):
        safe = next(server for server in self.manifest["mcp_servers"] if server["name"] == "safeoutputs")
        mutating = {tool for tool in safe["tools"] if tool not in {
            "noop", "report_incomplete", "report_missing_data", "report_missing_tool"
        }}
        self.assertEqual({"add_comment", "add_labels"}, mutating)


if __name__ == "__main__":
    unittest.main()
