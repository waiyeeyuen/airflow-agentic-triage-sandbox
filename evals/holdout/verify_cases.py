#!/usr/bin/env python3
"""Verify frozen holdout cases independently of their preparation fetch."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden"
HOLDOUT = ROOT / "evals" / "holdout"
TIMELINES = ROOT / "analysis" / "need_metric" / "raw" / "timelines"
sys.path.insert(0, str(GOLDEN))

import assemble_cases as ac  # noqa: E402

START = datetime(2026, 7, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(title: str, body: str) -> str:
    return hashlib.sha256((title + "\n\n" + body).encode()).hexdigest()


def fresh_original(number: int) -> tuple[str, str, int]:
    issue = read_json(HOLDOUT / "raw" / "verification_graphql" / f"{number}.json")["data"]["repository"]["issue"]
    edits = issue["userContentEdits"]["nodes"]
    if edits:
        assert edits[0]["diff"] == issue["body"], f"{number}: newest edit mismatch"
        assert edits[-1]["editedAt"] == issue["createdAt"], f"{number}: oldest edit is not creation version"
        body = edits[-1]["diff"]
    else:
        body = issue["body"] or ""
    events = ac.flatten_events(read_json(TIMELINES / f"{number}.json"))
    return ac.first_title(issue["title"], events), body, len(edits)


def main() -> None:
    selection = read_json(HOLDOUT / "selection.json")["selected"]
    expected = read_json(HOLDOUT / "expected.json")
    golden_ids = {int(row["number"]) for row in read_json(GOLDEN / "selection.json")["selected"]}
    assert len(selection) == 10 and len({row["number"] for row in selection}) == 10
    assert not ({int(row["number"]) for row in selection} & golden_ids)
    assert sum(row["group"] == "no_action_needed" for row in selection) >= 2
    assert len(expected["historical_cases"]) == 10
    expected_by_id = {row["case_id"]: row for row in expected["historical_cases"]}
    assert len(expected_by_id) == 10

    results = []
    for selected in selection:
        number = int(selected["number"])
        case_id = f"airflow-{number}"
        case_dir = HOLDOUT / "cases" / str(number)
        source = read_json(case_dir / "source.json")
        replay = read_json(case_dir / "input.json")
        reference = read_json(case_dir / "reference.json")
        prior = read_json(case_dir / "prior_issues.json")
        fresh_title, fresh_body, edit_count = fresh_original(number)
        fresh_hash = digest(fresh_title, fresh_body)
        created = datetime.fromisoformat(source["created_at"].replace("Z", "+00:00"))
        assert START <= created <= END, f"{number}: outside population window"
        assert fresh_hash == source["original_text_sha256"], f"{number}: source hash mismatch"
        assert fresh_hash == digest(source["original_title"], source["original_body"])
        assert edit_count == source["graphql_edit_count"]
        assert reference["not_agent_input"] is True
        assert set(replay) == {
            "case_id", "group", "event_time", "title", "body", "labels_at_creation",
            "template", "duplicate_snapshot", "duplicate_snapshot_cutoff_exclusive",
            "duplicate_snapshot_count", "replay_text_sha256", "author_replay_limitation",
        }
        cutoff = datetime.fromisoformat(replay["duplicate_snapshot_cutoff_exclusive"].replace("Z", "+00:00"))
        assert cutoff == created
        assert len(prior) == replay["duplicate_snapshot_count"]
        assert all(datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")) < cutoff for row in prior)
        assert all(set(row) == {"number", "created_at", "title_as_of_cutoff", "labels_as_of_cutoff"} for row in prior)
        replay_text = replay["title"] + "\n" + replay["body"]
        assert "@" not in replay_text
        assert not re.search(r"(?i)github\.com/apache/airflow/(?:issues|pull)/\d+|apache/airflow#\d+", replay_text)
        assert replay["replay_text_sha256"] == digest(replay["title"], replay["body"])
        oracle = expected_by_id[case_id]
        assert len(oracle["labels_to_add"]) <= 3
        assert oracle["should_comment"] == (oracle["comment_type"] != "none")
        if oracle["duplicate_of"] is not None:
            assert any(row["number"] == oracle["duplicate_of"] for row in prior)
        results.append(
            {
                "case_id": case_id,
                "created_in_window": True,
                "fresh_graphql_hash_matches": True,
                "first_version_edit_count": edit_count,
                "input_has_only_event_time_fields": True,
                "prior_snapshot_strictly_before_event": True,
                "mentions_and_upstream_crossrefs_neutralised": True,
                "expected_record_present": True,
            }
        )

    (HOLDOUT / "verification_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    output = f"verified {len(results)} independent historical holdout cases"
    (HOLDOUT / "verification_output.txt").write_text(output + "\n", encoding="utf-8")
    lines = [
        "# Holdout-input verification",
        "",
        "Verified before any holdout agent run.",
        "",
        "- 10 unique historical cases, disjoint from the 18 golden cases.",
        "- Two no-action controls are present.",
        "- Independent GraphQL re-fetches reproduce every first-version title/body SHA-256 hash.",
        "- Inputs contain only event-time text, creation labels/template and a dated prior snapshot.",
        "- Every prior-snapshot issue predates its case; post-event outcomes remain reference-only.",
        "- Replay text contains no @mention and no Apache Airflow issue/PR cross-reference.",
        "- Expectations cover all 10 cases and were recorded before any agent run.",
        "",
        "Machine-readable per-case checks are in `verification_results.json`.",
    ]
    (HOLDOUT / "verification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
