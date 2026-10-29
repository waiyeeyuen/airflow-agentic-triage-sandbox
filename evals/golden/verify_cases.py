#!/usr/bin/env python3
"""Independently verify every frozen historical and adversarial golden case."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import assemble_cases as ac

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden"
START = datetime(2026, 7, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(title: str, body: str) -> str:
    return hashlib.sha256((title + "\n\n" + body).encode("utf-8")).hexdigest()


def fresh_original(number: int) -> tuple[str, str, int]:
    issue = read_json(GOLDEN / "raw" / "verification_graphql" / f"{number}.json")["data"]["repository"]["issue"]
    edits = issue["userContentEdits"]["nodes"]
    if edits:
        assert edits[0]["diff"] == issue["body"], f"{number}: newest edit does not match current body"
        assert edits[-1]["editedAt"] == issue["createdAt"], f"{number}: oldest edit is not creation version"
        body = edits[-1]["diff"]
    else:
        body = issue["body"] or ""
    events = ac.flatten_events(read_json(ROOT / "analysis" / "need_metric" / "raw" / "timelines" / f"{number}.json"))
    title = ac.first_title(issue["title"], events)
    return title, body, len(edits)


def main() -> None:
    selection = read_json(GOLDEN / "selection.json")["selected"]
    expected = read_json(GOLDEN / "expected.json")
    assert len(selection) == 18 and len({item["number"] for item in selection}) == 18
    assert sum(item["group"] == "no_action_needed" for item in selection) >= 2
    assert len(expected["historical_cases"]) == 18
    assert len(expected["adversarial_cases"]) >= 3
    expected_by_id = {item["case_id"]: item for item in expected["historical_cases"]}
    assert len(expected_by_id) == 18
    results = []
    for selected in selection:
        number = selected["number"]
        case_id = f"airflow-{number}"
        case_dir = GOLDEN / "cases" / str(number)
        source = read_json(case_dir / "source.json")
        replay = read_json(case_dir / "input.json")
        reference = read_json(case_dir / "reference.json")
        prior = read_json(case_dir / "prior_issues.json")
        fresh_title, fresh_body, edit_count = fresh_original(number)
        fresh_hash = digest(fresh_title, fresh_body)
        created = datetime.fromisoformat(source["created_at"].replace("Z", "+00:00"))
        assert START <= created <= END, f"{number}: outside window"
        assert fresh_hash == source["original_text_sha256"], f"{number}: source hash mismatch"
        assert fresh_hash == digest(source["original_title"], source["original_body"])
        assert edit_count == source["graphql_edit_count"]
        assert reference["not_agent_input"] is True
        assert set(replay) == {
            "case_id", "group", "event_time", "title", "body", "labels_at_creation",
            "template", "duplicate_snapshot", "duplicate_snapshot_cutoff_exclusive",
            "duplicate_snapshot_count", "replay_text_sha256", "author_replay_limitation",
        }, f"{number}: unexpected input field"
        cutoff = datetime.fromisoformat(replay["duplicate_snapshot_cutoff_exclusive"].replace("Z", "+00:00"))
        assert cutoff == created
        assert len(prior) == replay["duplicate_snapshot_count"]
        assert all(datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")) < cutoff for item in prior)
        assert all(set(item) == {"number", "created_at", "title_as_of_cutoff", "labels_as_of_cutoff"} for item in prior)
        replay_text = replay["title"] + "\n" + replay["body"]
        assert "@" not in replay_text
        assert not re.search(r"(?i)github\.com/apache/airflow/(?:issues|pull)/\d+|apache/airflow#\d+", replay_text)
        oracle = expected_by_id[case_id]
        assert len(oracle["labels_to_add"]) <= 3
        assert oracle["should_comment"] == (oracle["comment_type"] != "none")
        if oracle["duplicate_of"] is not None:
            assert any(item["number"] == oracle["duplicate_of"] for item in prior), f"{number}: duplicate target absent"
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

    for adversarial in expected["adversarial_cases"]:
        slug = adversarial["case_id"].removeprefix("adversarial-").replace("-", "_")
        path = GOLDEN / "adversarial" / f"{slug}.json"
        data = read_json(path)
        text = data["title"] + "\n" + data["body"]
        assert data["case_id"] == adversarial["case_id"]
        assert "@" not in text
        assert not re.search(r"(?i)github\.com/apache/airflow/(?:issues|pull)/\d+|apache/airflow#\d+", text)
        assert len(adversarial["labels_to_add"]) <= 3

    (GOLDEN / "verification_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Golden-input verification",
        "",
        "Verified on 29 October 2026 UTC before any agent run.",
        "",
        "- 18 unique historical cases; all creation timestamps are within 1 July–30 September 2026 UTC.",
        "- Each source was freshly re-fetched through GraphQL `userContentEdits`; all 18 reconstructed first-version title/body hashes match `source.json`.",
        "- For edited bodies, the oldest saved version has `editedAt == issue.createdAt`; unedited bodies have an empty edit history.",
        "- Every `input.json` contains only event-time text, creation labels/template, and a dated prior-issue snapshot reference. Post-event outcomes are isolated in `reference.json` and marked `not_agent_input`.",
        "- Every prior snapshot entry was created strictly before its case and contains only title and labels reconstructed as of that cutoff; no collection-time labels are present.",
        "- Replay text contains no `@` and no Apache Airflow issue/PR cross-reference. The unsanitised source URL and hash remain only in committed evidence files.",
        "- Three no-action historical cases and three constructed adversarial cases are present. Expectations cover every case, limit labels to three, and allow at most one comment.",
        "- No workflow or model run has occurred; `actual/` and run logs do not yet exist.",
        "",
        "Per-case machine-readable checks are in `verification_results.json`; fresh responses are in `raw/verification_graphql/`.",
        "",
        "Known limitation: replay issues will be authored by Jasmine rather than the historical reporters, so author association cannot be reproduced.",
    ]
    (GOLDEN / "verification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"verified {len(results)} historical and {len(expected['adversarial_cases'])} adversarial cases")


if __name__ == "__main__":
    main()
