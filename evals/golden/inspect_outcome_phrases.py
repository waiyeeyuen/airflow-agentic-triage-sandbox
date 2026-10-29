#!/usr/bin/env python3
"""Inspect human-maintainer wording used to define outcome strata."""

import json
import re
from pathlib import Path

import select_cases as sc

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = {
    "duplicate": re.compile(
        r"(?i)((?:closing|closed|marking|this (?:is|looks like)|seems like).{0,80}duplicate|duplicate of\s+(?:#|https))"
    ),
    "support_question": re.compile(
        r"(?i)((?:please|kindly).{0,60}(?:github discussions|stack overflow)|(?:support|usage) question.{0,80}(?:discussion|stack overflow)|not a bug.{0,80}(?:discussion|stack overflow))"
    ),
    "invalid_or_spam": re.compile(
        r"(?i)((?:closing|closed|marking).{0,80}(?:invalid|spam)|(?:invalid|spam).{0,80}(?:closing|closed))"
    ),
    "discussion_mention": re.compile(r"(?i)(.{0,50}(?:github discussions|stack overflow|support question).{0,100})"),
    "invalid_mention": re.compile(r"(?i)(.{0,50}(?:\binvalid\b|\bspam\b|not a bug).{0,100})"),
}


def main():
    source = sc.read_json(ROOT / "analysis" / "need_metric" / "raw" / "population_pages.json")
    issues = sc.flatten_dicts(source, lambda d: "number" in d and "created_at" in d and "pull_request" not in d)
    matches = []
    for issue in issues:
        events = sc.flatten_dicts(
            sc.read_json(ROOT / "analysis" / "need_metric" / "raw" / "timelines" / f"{issue['number']}.json"),
            lambda d: "created_at" in d and ("event" in d or ("body" in d and "user" in d)),
        )
        for event in events:
            if sc.event_kind(event) != "commented" or not sc.is_human_non_author(event, issue["user"]["login"]):
                continue
            body = event.get("body") or ""
            for group, pattern in PATTERNS.items():
                hit = pattern.search(body)
                if hit:
                    matches.append(
                        {
                            "group": group,
                            "number": issue["number"],
                            "title": issue["title"],
                            "created_at": issue["created_at"],
                            "comment_created_at": event["created_at"],
                            "match": hit.group(1),
                        }
                    )
    print(json.dumps(matches, indent=2))


if __name__ == "__main__":
    main()
