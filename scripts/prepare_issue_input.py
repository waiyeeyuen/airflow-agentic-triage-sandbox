#!/usr/bin/env python3
"""Prepare one immutable issue input for the agent without model-authored shell writes."""
import argparse
import json
from pathlib import Path


def labels_from_issue(issue):
    labels = []
    for item in issue.get("labels", []):
        value = item.get("name") if isinstance(item, dict) else item
        if isinstance(value, str):
            labels.append(value)
    return labels


def from_event(path):
    event = json.loads(Path(path).read_text(encoding="utf-8"))
    issue = event.get("issue")
    if not isinstance(issue, dict):
        raise ValueError("event does not contain an issue")
    return {
        "issue_number": issue.get("number"),
        "title": issue.get("title", ""),
        "body": issue.get("body") or "",
        "current_labels": labels_from_issue(issue),
    }


def from_case(path):
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("case path must be repository-relative")
    data = json.loads(candidate.read_text(encoding="utf-8"))
    return {
        "issue_number": data.get("issue_number", data.get("number")),
        "title": data.get("title", ""),
        "body": data.get("body") or "",
        "current_labels": data.get("current_labels", data.get("labels_at_creation", [])),
    }


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--event")
    source.add_argument("--case")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prepared = from_event(args.event) if args.event else from_case(args.case)
    if not isinstance(prepared["title"], str) or not isinstance(prepared["body"], str):
        raise ValueError("title and body must be strings")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(prepared, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
