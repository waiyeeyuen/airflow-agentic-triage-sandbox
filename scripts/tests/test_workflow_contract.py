import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".github" / "workflows" / "issue-triage.md"
LOCK = ROOT / ".github" / "workflows" / "issue-triage.lock.yml"
SKILL = ROOT / ".claude" / "skills" / "airflow-issue-triage" / "SKILL.md"


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.skill = SKILL.read_text(encoding="utf-8")
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
            "max-turns: 20",
            "max-ai-credits: 25",
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

    def test_skill_commands_match_source_allowlist_and_ubuntu_python(self):
        commands = (
            "python3 scripts/search_duplicates.py --case /tmp/gh-aw/agent/case.json --corpus-root evals/golden/cases --output /tmp/gh-aw/agent/duplicates.json",
            "python3 scripts/validate_labels.py --case /tmp/gh-aw/agent/case.json --output /tmp/gh-aw/agent/validated.json",
            "python3 scripts/render_comment.py --case /tmp/gh-aw/agent/case.json --output /tmp/gh-aw/agent/comment.json --type none",
        )
        for command in commands:
            self.assertIn(f'"{command}"', self.frontmatter)
            self.assertIn(command, self.skill)
        self.assertNotIn('"python scripts/', self.frontmatter)
        self.assertIn("pre-agent-steps:", self.frontmatter)
        self.assertIn("scripts/prepare_issue_input.py", self.frontmatter)
        self.assertIn("Never\n   create or edit a file", self.skill)
        self.assertIn("If any command is denied, stop immediately and propose no outputs.", self.skill)

    def test_threat_detection_is_deterministic_and_fails_closed(self):
        required = (
            "continue-on-error: false",
            "engine: false",
            "scripts/validate_safe_outputs.py",
        )
        for value in required:
            self.assertIn(value, self.frontmatter)
        self.assertNotIn("model: gpt-4.1\n      max-turns", self.frontmatter)
        lock = "\n".join(self.lock_lines)
        self.assertIn("GH_AW_DETECTION_CONTINUE_ON_ERROR: \"false\"", lock)
        self.assertIn("needs.detection.result == 'success'", lock)
        step = lock.split("- name: Deterministically validate proposed labels and comment", 1)[1].split("- name:", 1)[0]
        self.assertNotIn("continue-on-error: true", step)

    def test_daily_credit_guard_is_an_admission_control(self):
        lock = "\n".join(self.lock_lines)
        self.assertIn('GH_AW_MAX_DAILY_AI_CREDITS: "5000"', lock)
        self.assertIn("check_daily_aic_workflow_guardrail.cjs", lock)
        self.assertIn("if: needs.activation.outputs.daily_ai_credits_exceeded != 'true'", lock)

    def test_model_has_no_generic_github_or_file_write_tool(self):
        self.assertIn("edit: false", self.frontmatter)
        self.assertIn("github: false", self.frontmatter)
        self.assertIn("cli-proxy: false", self.frontmatter)

    def test_compiled_copilot_denies_injected_generic_shell_commands(self):
        lock = "\n".join(self.lock_lines)
        for command in ("cat", "date", "echo", "grep", "head", "ls", "printf", "pwd",
                        "sort", "tail", "uniq", "wc", "yq", "safeoutputs:*"):
            self.assertIn(f"--deny-tool '\\''shell({command})'\\''", lock)

    def test_compiled_safeoutput_tools_have_no_pr_or_destructive_action(self):
        safe = next(server for server in self.manifest["mcp_servers"] if server["name"] == "safeoutputs")
        mutating = {tool for tool in safe["tools"] if tool not in {
            "noop", "report_incomplete", "report_missing_data", "report_missing_tool"
        }}
        self.assertEqual({"add_comment", "add_labels"}, mutating)


if __name__ == "__main__":
    unittest.main()
