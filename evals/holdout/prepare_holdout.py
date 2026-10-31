#!/usr/bin/env python3
"""Select and freeze an independent Airflow issue-triage holdout set."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden"
HOLDOUT = ROOT / "evals" / "holdout"
TIMELINES = ROOT / "analysis" / "need_metric" / "raw" / "timelines"
sys.path.insert(0, str(GOLDEN))

import assemble_cases as ac  # noqa: E402
import select_cases as sc  # noqa: E402

SEED = "cs467-airflow-triage-holdout-2026-10-31-v1"
QUOTAS = {
    "core_bug": 2,
    "provider_bug": 1,
    "feature_request": 1,
    "documentation": 1,
    "security_sounding": 1,
    "no_action_needed": 2,
    "meta_or_task": 2,
}
QUERY = r"""
query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){
    issue(number:$number){
      number title body createdAt url author{login}
      labels(first:100){nodes{name} pageInfo{hasNextPage}}
      userContentEdits(first:100){
        nodes{createdAt editedAt updatedAt editor{login} diff}
        pageInfo{hasNextPage endCursor}
      }
    }
  }
}
"""


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rank(group: str, number: int) -> str:
    return hashlib.sha256(f"{SEED}|{group}|{number}".encode()).hexdigest()


def fetch_graphql(gh: str, number: int, path: Path) -> dict:
    command = [
        gh,
        "api",
        "graphql",
        "-f",
        f"query={QUERY}",
        "-F",
        "owner=apache",
        "-F",
        "name=airflow",
        "-F",
        f"number={number}",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(completed.stdout, encoding="utf-8")
    payload = json.loads(completed.stdout)
    issue = payload["data"]["repository"]["issue"]
    if issue is None or issue["number"] != number:
        raise RuntimeError(f"GraphQL did not return issue {number}")
    if issue["userContentEdits"]["pageInfo"]["hasNextPage"]:
        raise RuntimeError(f"Issue {number} has more than 100 edits")
    return issue


def select(rows: list[dict], excluded: set[int]) -> list[dict]:
    selected = []
    for group, quota in QUOTAS.items():
        candidates = sorted(
            (row for row in rows if row["group"] == group and row["number"] not in excluded),
            key=lambda row: rank(group, row["number"]),
        )
        if len(candidates) < quota:
            raise RuntimeError(f"Group {group} has {len(candidates)} eligible cases, needs {quota}")
        selected.extend(candidates[:quota])
    selected.sort(key=lambda row: (row["created_at"], row["number"]))
    if len(selected) != 10 or len({row["number"] for row in selected}) != 10:
        raise RuntimeError("Holdout selection must contain 10 unique cases")
    return selected


def original_body(issue: dict) -> tuple[str, str, int]:
    edits = issue["userContentEdits"]["nodes"]
    if edits:
        if edits[0]["diff"] != issue["body"]:
            raise RuntimeError(f"Newest edit does not match current body for {issue['number']}")
        if edits[-1]["editedAt"] != issue["createdAt"]:
            raise RuntimeError(f"Oldest edit is not the creation version for {issue['number']}")
        return edits[-1]["diff"], "oldest GraphQL userContentEdits.diff; editedAt equals issue createdAt", len(edits)
    return issue["body"] or "", "GraphQL current body; userContentEdits is empty", 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gh", default="gh")
    args = parser.parse_args()

    population = read_json(GOLDEN / "raw" / "population_normalized.json")
    rows = read_json(GOLDEN / "population_groups.json")["issues"]
    golden = read_json(GOLDEN / "selection.json")["selected"]
    excluded = {int(row["number"]) for row in golden}
    selected = select(rows, excluded)
    write_json(
        HOLDOUT / "selection.json",
        {
            "seed": SEED,
            "method": "SHA-256 rank of seed|group|issue_number within each original stratum",
            "excluded_golden_case_ids": sorted(excluded),
            "duplicate_stratum": "exhausted: its sole population case is in the golden set",
            "quotas": QUOTAS,
            "selected": selected,
        },
    )
    (HOLDOUT / "seed.txt").write_text(SEED + "\n", encoding="utf-8")

    event_cache = {
        int(issue["number"]): sc.flatten_dicts(
            read_json(TIMELINES / f"{issue['number']}.json"),
            lambda value: "created_at" in value and ("event" in value or ("body" in value and "user" in value)),
        )
        for issue in population
    }
    issue_by_number = {int(issue["number"]): issue for issue in population}
    manifest = []
    for row in selected:
        number = int(row["number"])
        population_issue = issue_by_number[number]
        events = event_cache[number]
        creation_labels = sc.initial_labels(population_issue, events)
        first48 = sc.human_events_within(population_issue, events, 48)
        group = sc.classify(population_issue, events, creation_labels, first48)
        if group != row["group"]:
            raise RuntimeError(f"Classification drift for {number}: {group} != {row['group']}")

        cutoff = sc.parse_time(population_issue["created_at"])
        prior = [
            {
                "number": int(candidate["number"]),
                "created_at": candidate["created_at"],
                "title_as_of_cutoff": sc.title_at(candidate, event_cache[int(candidate["number"])], cutoff),
                "labels_as_of_cutoff": sc.labels_at(event_cache[int(candidate["number"])], cutoff),
            }
            for candidate in population
            if sc.parse_time(candidate["created_at"]) < cutoff
        ]
        case_dir = HOLDOUT / "cases" / str(number)
        write_json(case_dir / "prior_issues.json", prior)
        write_json(
            HOLDOUT / "raw" / "case_skeletons" / f"{number}.json",
            {
                "case_id": f"airflow-{number}",
                "group": group,
                "number": number,
                "created_at": population_issue["created_at"],
                "author_login": population_issue["user"]["login"],
                "initial_labels": creation_labels,
                "template": sc.template_name(creation_labels),
                "first_48h_maintainer_outcome": first48,
                "final_labels_at_collection": sorted(label["name"] for label in population_issue.get("labels", [])),
                "prior_snapshot_cutoff_exclusive": population_issue["created_at"],
                "prior_snapshot_count": len(prior),
            },
        )

        issue = fetch_graphql(args.gh, number, HOLDOUT / "raw" / "graphql" / f"{number}.json")
        fetch_graphql(args.gh, number, HOLDOUT / "raw" / "verification_graphql" / f"{number}.json")
        body, method, edit_count = original_body(issue)
        original_title = ac.first_title(issue["title"], events)
        replay_title = ac.sanitize_for_replay(original_title)
        replay_body = ac.sanitize_for_replay(body)
        if "@" in replay_title or "@" in replay_body:
            raise RuntimeError(f"Replay input still contains @ for {number}")
        if re.search(r"(?i)github\.com/apache/airflow/(?:issues|pull)/\d+|apache/airflow#\d+", replay_title + "\n" + replay_body):
            raise RuntimeError(f"Replay input still contains an upstream reference for {number}")

        skeleton = read_json(HOLDOUT / "raw" / "case_skeletons" / f"{number}.json")
        original_hash = ac.sha256(original_title + "\n\n" + body)
        replay_hash = ac.sha256(replay_title + "\n\n" + replay_body)
        write_json(
            case_dir / "source.json",
            {
                "case_id": f"airflow-{number}",
                "group": group,
                "source_url": issue["url"],
                "number": number,
                "created_at": issue["createdAt"],
                "author_login": issue["author"]["login"] if issue.get("author") else None,
                "original_title": original_title,
                "original_body": body,
                "original_body_sha256": ac.sha256(body),
                "original_text_sha256": original_hash,
                "first_version_method": method,
                "graphql_edit_count": edit_count,
                "graphql_raw_file": f"../../raw/graphql/{number}.json",
            },
        )
        write_json(
            case_dir / "input.json",
            {
                "case_id": f"airflow-{number}",
                "group": group,
                "event_time": issue["createdAt"],
                "title": replay_title,
                "body": replay_body,
                "labels_at_creation": skeleton["initial_labels"],
                "template": skeleton["template"],
                "duplicate_snapshot": "prior_issues.json",
                "duplicate_snapshot_cutoff_exclusive": issue["createdAt"],
                "duplicate_snapshot_count": skeleton["prior_snapshot_count"],
                "replay_text_sha256": replay_hash,
                "author_replay_limitation": "Sandbox replay is authored by Wai Yee, not the historical reporter.",
            },
        )
        write_json(
            case_dir / "reference.json",
            {
                "case_id": f"airflow-{number}",
                "not_agent_input": True,
                "first_48h_maintainer_outcome": skeleton["first_48h_maintainer_outcome"],
                "labels_at_collection": skeleton["final_labels_at_collection"],
                "explanation": "Post-event fields are reference-only and must never be supplied to the agent.",
            },
        )
        manifest.append(
            {
                "number": number,
                "group": group,
                "created_at": issue["createdAt"],
                "original_text_sha256": original_hash,
                "replay_text_sha256": replay_hash,
                "edit_count": edit_count,
            }
        )
        print(f"frozen airflow-{number} ({group}), edits={edit_count}, prior={len(prior)}")
    write_json(HOLDOUT / "case_manifest.json", manifest)
    print(json.dumps({"seed": SEED, "selected": selected}, indent=2))


if __name__ == "__main__":
    main()
