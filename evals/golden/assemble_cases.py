#!/usr/bin/env python3
"""Freeze first-version case inputs and isolate post-event reference outcomes."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden"
NEED_TIMELINES = ROOT / "analysis" / "need_metric" / "raw" / "timelines"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def flatten_events(value):
    found = []
    if isinstance(value, list):
        for child in value:
            found.extend(flatten_events(child))
    elif isinstance(value, dict):
        if "created_at" in value and ("event" in value or ("body" in value and "user" in value)):
            found.append(value)
        else:
            for child in value.values():
                found.extend(flatten_events(child))
    return found


def first_title(current_title: str, events: list[dict]) -> str:
    renames = sorted(
        (event for event in events if event.get("event") == "renamed" and event.get("rename")),
        key=lambda event: event["created_at"],
    )
    return (renames[0]["rename"].get("from") if renames else None) or current_title


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_for_replay(text: str) -> str:
    text = re.sub(
        r"https?://github\.com/apache/airflow/(?:issues|pull)/\d+(?:#[^\s)>]*)?",
        "(upstream reference removed)",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"(?i)\bapache/airflow#\d+\b", "(upstream reference removed)", text)
    return text.replace("@", "(at)")


def main() -> None:
    selection = read_json(GOLDEN / "selection.json")["selected"]
    summary = []
    for selected in selection:
        number = selected["number"]
        case_dir = GOLDEN / "cases" / str(number)
        skeleton = read_json(GOLDEN / "raw" / "case_skeletons" / f"{number}.json")
        graphql_path = GOLDEN / "raw" / "graphql" / f"{number}.json"
        issue = read_json(graphql_path)["data"]["repository"]["issue"]
        edits = issue["userContentEdits"]["nodes"]
        if edits:
            if edits[0]["diff"] != issue["body"]:
                raise RuntimeError(f"Newest edit version does not match current body for {number}")
            if edits[-1]["editedAt"] != issue["createdAt"]:
                raise RuntimeError(f"Oldest edit version is not the creation version for {number}")
            original_body = edits[-1]["diff"]
            method = "oldest GraphQL userContentEdits.diff; editedAt equals issue createdAt"
        else:
            original_body = issue["body"] or ""
            method = "GraphQL current body; userContentEdits is empty"
        events = flatten_events(read_json(NEED_TIMELINES / f"{number}.json"))
        original_title = first_title(issue["title"], events)
        original_hash = sha256(original_title + "\n\n" + original_body)
        body_hash = sha256(original_body)
        replay_title = sanitize_for_replay(original_title)
        replay_body = sanitize_for_replay(original_body)
        replay_hash = sha256(replay_title + "\n\n" + replay_body)
        if "@" in replay_title or "@" in replay_body:
            raise RuntimeError(f"Replay input still contains @ for {number}")
        replay_text = replay_title + "\n" + replay_body
        if re.search(r"(?i)github\.com/apache/airflow/(?:issues|pull)/\d+|apache/airflow#\d+", replay_text):
            raise RuntimeError(f"Replay input still contains an upstream cross-reference for {number}")

        source = {
            "case_id": f"airflow-{number}",
            "group": selected["group"],
            "source_url": issue["url"],
            "number": number,
            "created_at": issue["createdAt"],
            "author_login": issue["author"]["login"] if issue.get("author") else None,
            "original_title": original_title,
            "original_body": original_body,
            "original_body_sha256": body_hash,
            "original_text_sha256": original_hash,
            "first_version_method": method,
            "graphql_edit_count": len(edits),
            "graphql_raw_file": f"../../raw/graphql/{number}.json",
        }
        replay_input = {
            "case_id": f"airflow-{number}",
            "group": selected["group"],
            "event_time": issue["createdAt"],
            "title": replay_title,
            "body": replay_body,
            "labels_at_creation": skeleton["initial_labels"],
            "template": skeleton["template"],
            "duplicate_snapshot": "prior_issues.json",
            "duplicate_snapshot_cutoff_exclusive": issue["createdAt"],
            "duplicate_snapshot_count": skeleton["prior_snapshot_count"],
            "replay_text_sha256": replay_hash,
            "author_replay_limitation": "Sandbox replay is authored by Jasmine, not the historical reporter.",
        }
        reference = {
            "case_id": f"airflow-{number}",
            "not_agent_input": True,
            "first_48h_maintainer_outcome": skeleton["first_48h_maintainer_outcome"],
            "labels_at_collection": skeleton["final_labels_at_collection"],
            "explanation": "Post-event fields are reference-only and must never be supplied to the agent.",
        }
        write_json(case_dir / "source.json", source)
        write_json(case_dir / "input.json", replay_input)
        write_json(case_dir / "reference.json", reference)
        summary.append(
            {
                "number": number,
                "group": selected["group"],
                "created_at": issue["createdAt"],
                "original_text_sha256": original_hash,
                "replay_text_sha256": replay_hash,
                "edit_count": len(edits),
            }
        )
    write_json(GOLDEN / "case_manifest.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
