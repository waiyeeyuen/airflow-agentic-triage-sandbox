#!/usr/bin/env python3
"""Build a reproducible, stratified golden-case draw from saved read-only data."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evals" / "golden"
RAW = OUT / "raw"
CASES = OUT / "cases"
NEED = ROOT / "analysis" / "need_metric"
SEED = "cs467-airflow-triage-2026-10-29-v1"
WINDOW_START = datetime(2026, 7, 1, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
QUOTAS = {
    "core_bug": 3,
    "provider_bug": 3,
    "feature_request": 2,
    "documentation": 2,
    "duplicate": 1,
    "security_sounding": 1,
    "no_action_needed": 3,
    "meta_or_task": 3,
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def flatten_dicts(value, predicate):
    found = []
    if isinstance(value, list):
        for child in value:
            found.extend(flatten_dicts(child, predicate))
    elif isinstance(value, dict):
        if predicate(value):
            found.append(value)
        else:
            for child in value.values():
                found.extend(flatten_dicts(child, predicate))
    return found


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def event_kind(event: dict) -> str:
    if event.get("event"):
        return event["event"]
    if "body" in event and event.get("user"):
        return "commented"
    return "unknown"


def actor(event: dict) -> dict | None:
    return event.get("actor") or event.get("user")


def is_bot(user: dict | None) -> bool:
    if not user:
        return False
    login = user.get("login") or ""
    return user.get("type") == "Bot" or bool(re.search(r"(?i)(\[bot\]|-bot$|^bot-)", login))


def is_human_non_author(event: dict, author_login: str) -> bool:
    user = actor(event)
    return bool(user and user.get("login") and user["login"] != author_login and not is_bot(user))


def initial_labels(issue: dict, events: list[dict]) -> list[str]:
    """Labels applied automatically at creation, before human triage.

    GitHub records issue-template labels as label events attributed to the issue
    author within seconds. We replay only author/bot label events in the first 60
    seconds. A non-author human event ends the automatic-creation interval.
    """
    created = parse_time(issue["created_at"])
    cutoff = created + timedelta(seconds=60)
    labels: set[str] = set()
    for event in sorted(events, key=lambda e: e.get("created_at") or ""):
        if not event.get("created_at") or parse_time(event["created_at"]) > cutoff:
            break
        kind = event_kind(event)
        who = actor(event)
        if is_human_non_author(event, issue["user"]["login"]):
            break
        if not who or not (who.get("login") == issue["user"]["login"] or is_bot(who)):
            continue
        label = (event.get("label") or {}).get("name")
        if kind == "labeled" and label:
            labels.add(label)
        elif kind == "unlabeled" and label:
            labels.discard(label)
    return sorted(labels)


def template_name(labels: list[str]) -> str:
    values = set(labels)
    if {"kind:bug", "area:airflow-ctl", "needs-triage"}.issubset(values):
        return "airflow_ctl_issue_template.yml"
    if {"kind:bug", "needs-triage"}.issubset(values):
        return "1-airflow_bug_report.yml"
    if {"kind:feature", "needs-triage"}.issubset(values):
        return "2-feature_request.yml"
    if "kind:meta" in values:
        return "3-free_form.yml"
    return "unknown"


def human_events_within(issue: dict, events: list[dict], hours: int) -> list[dict]:
    deadline = parse_time(issue["created_at"]) + timedelta(hours=hours)
    allowed = {"commented", "labeled", "unlabeled", "closed", "converted_to_discussion"}
    result = []
    for event in events:
        if not event.get("created_at") or parse_time(event["created_at"]) > deadline:
            continue
        kind = event_kind(event)
        if kind not in allowed or not is_human_non_author(event, issue["user"]["login"]):
            continue
        result.append(
            {
                "event": kind,
                "created_at": event["created_at"],
                "actor": actor(event)["login"],
                "label": (event.get("label") or {}).get("name"),
                "body": event.get("body") if kind == "commented" else None,
            }
        )
    return sorted(result, key=lambda e: e["created_at"])


def labels_at(events: list[dict], cutoff: datetime) -> list[str]:
    labels: set[str] = set()
    for event in sorted(events, key=lambda e: e.get("created_at") or ""):
        if not event.get("created_at") or parse_time(event["created_at"]) >= cutoff:
            continue
        label = (event.get("label") or {}).get("name")
        if event_kind(event) == "labeled" and label:
            labels.add(label)
        elif event_kind(event) == "unlabeled" and label:
            labels.discard(label)
    return sorted(labels)


def title_at(issue: dict, events: list[dict], cutoff: datetime) -> str:
    title = issue["title"]
    renames = [
        event
        for event in events
        if event_kind(event) == "renamed" and event.get("created_at") and event.get("rename")
    ]
    for event in sorted(renames, key=lambda e: e["created_at"], reverse=True):
        if parse_time(event["created_at"]) >= cutoff:
            title = event["rename"].get("from") or title
    return title


def all_human_comment_text(issue: dict, events: list[dict]) -> str:
    return "\n".join(
        event.get("body") or ""
        for event in events
        if event_kind(event) == "commented" and is_human_non_author(event, issue["user"]["login"])
    )


def classify(issue: dict, events: list[dict], at_creation: list[str], first48: list[dict]) -> str:
    labels = {label["name"] for label in issue.get("labels", [])}
    comments = all_human_comment_text(issue, events)
    text = f"{issue.get('title', '')}\n{(issue.get('body') or '')[:4000]}"
    if "security" in labels or re.search(
        r"(?i)(security vulnerability|\bvulnerabilit|\bCVE-|credential (?:leak|exposure)|secret (?:leak|exposure))",
        text,
    ):
        return "security_sounding"
    if re.search(
        r"(?im)(^\s*closed as (?:a )?duplicate\b|^\s*duplicate of\s+(?:#|https))",
        comments,
    ):
        return "duplicate"
    has_kind = any(label.startswith("kind:") for label in at_creation)
    has_specific = any(label.startswith(("area:", "provider:")) for label in at_creation) or "kind:meta" in at_creation
    if has_kind and has_specific and not first48 and set(at_creation) == labels:
        return "no_action_needed"
    if "kind:documentation" in labels:
        return "documentation"
    if "kind:feature" in labels:
        return "feature_request"
    if "kind:meta" in labels or "kind:task" in labels:
        return "meta_or_task"
    if "kind:bug" in labels and any(label.startswith("provider:") for label in labels):
        return "provider_bug"
    if "kind:bug" in labels:
        return "core_bug"
    return "other"


def rank(group: str, number: int) -> str:
    return hashlib.sha256(f"{SEED}|{group}|{number}".encode()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    CASES.mkdir(parents=True, exist_ok=True)
    source_population = NEED / "raw" / "population_pages.json"
    shutil.copyfile(source_population, RAW / "population_pages.json")
    population = flatten_dicts(read_json(source_population), lambda d: "number" in d and "created_at" in d and "pull_request" not in d)
    population.sort(key=lambda i: (i["created_at"], i["number"]))
    if len(population) != 477 or len({i["number"] for i in population}) != 477:
        raise RuntimeError("Expected 477 unique issues in the saved population")

    rows = []
    event_cache: dict[int, list[dict]] = {}
    for issue in population:
        events = flatten_dicts(
            read_json(NEED / "raw" / "timelines" / f"{issue['number']}.json"),
            lambda d: "created_at" in d and ("event" in d or ("body" in d and "user" in d)),
        )
        event_cache[issue["number"]] = events
        at_creation = initial_labels(issue, events)
        first48 = human_events_within(issue, events, 48)
        group = classify(issue, events, at_creation, first48)
        rows.append(
            {
                "number": issue["number"],
                "created_at": issue["created_at"],
                "title": issue["title"],
                "group": group,
                "initial_labels": at_creation,
                "template": template_name(at_creation),
                "final_labels_at_collection": sorted(label["name"] for label in issue.get("labels", [])),
                "first_48h_human_event_count": len(first48),
            }
        )

    counts = Counter(row["group"] for row in rows)
    selected = []
    for group, quota in QUOTAS.items():
        candidates = sorted((row for row in rows if row["group"] == group), key=lambda row: rank(group, row["number"]))
        if len(candidates) < quota:
            raise RuntimeError(f"Group {group} has {len(candidates)} candidates, needs {quota}")
        selected.extend(candidates[:quota])
    selected.sort(key=lambda row: (row["created_at"], row["number"]))
    if len(selected) != 18 or len({row["number"] for row in selected}) != 18:
        raise RuntimeError("Selection must contain 18 unique historical cases")

    write_json(RAW / "population_normalized.json", population)
    write_json(OUT / "population_groups.json", {"seed": SEED, "counts": dict(sorted(counts.items())), "issues": rows})
    write_json(OUT / "selection.json", {"seed": SEED, "quotas": QUOTAS, "selected": selected})
    (OUT / "seed.txt").write_text(SEED + "\n", encoding="utf-8")

    issue_by_number = {issue["number"]: issue for issue in population}
    for row in selected:
        number = row["number"]
        issue = issue_by_number[number]
        events = event_cache[number]
        snapshot_cutoff = parse_time(issue["created_at"])
        prior = [
            {
                "number": candidate["number"],
                "created_at": candidate["created_at"],
                "title_as_of_cutoff": title_at(candidate, event_cache[candidate["number"]], snapshot_cutoff),
                "labels_as_of_cutoff": labels_at(event_cache[candidate["number"]], snapshot_cutoff),
            }
            for candidate in population
            if parse_time(candidate["created_at"]) < snapshot_cutoff
        ]
        case_dir = CASES / str(number)
        write_json(case_dir / "prior_issues.json", prior)
        write_json(
            RAW / "case_skeletons" / f"{number}.json",
            {
                "case_id": f"airflow-{number}",
                "group": row["group"],
                "number": number,
                "created_at": issue["created_at"],
                "author_login": issue["user"]["login"],
                "initial_labels": row["initial_labels"],
                "template": row["template"],
                "first_48h_maintainer_outcome": human_events_within(issue, events, 48),
                "final_labels_at_collection": row["final_labels_at_collection"],
                "prior_snapshot_cutoff_exclusive": issue["created_at"],
                "prior_snapshot_count": len(prior),
            },
        )

    print(json.dumps({"population": len(population), "counts": counts, "selected": selected}, indent=2, default=dict))


if __name__ == "__main__":
    main()
