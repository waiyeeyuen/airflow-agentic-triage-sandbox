#!/usr/bin/env python3
"""Fail closed unless proposed labels/comments match the deterministic triage policy."""
import argparse
import json
import re
from pathlib import Path

from render_comment import render
from validate_labels import validate

ALLOWED_NON_MUTATIONS = {"noop", "report_incomplete", "report_missing_tool",
                         "report_missing_data", "missing_tool", "missing_data"}
LINK = re.compile(r"https?://|www\.|\]\(", re.IGNORECASE)
MENTION = re.compile(r"(?<![A-Za-z0-9])@[A-Za-z0-9_-]+")


def payload(item):
    for key in ("arguments", "input", "data", "payload"):
        if isinstance(item.get(key), dict):
            return item[key]
    return item


def item_type(item):
    for key in ("type", "tool", "name", "tool_name"):
        value = item.get(key)
        if isinstance(value, str):
            return value.replace("-", "_")
    raise ValueError("safe-output item has no type")


def label_names(values):
    result = []
    for value in values:
        if isinstance(value, str):
            result.append(value)
        elif isinstance(value, dict) and isinstance(value.get("name"), str):
            result.append(value["name"])
        else:
            raise ValueError("invalid label value")
    return result


def valid_comment(body):
    if not isinstance(body, str) or MENTION.search(body) or LINK.search(body):
        return False
    fixed = {render("security_route"), render("clarification", question="version"),
             render("clarification", question="reproduction"),
             render("clarification", question="expected")}
    if body in fixed:
        return True
    match = re.fullmatch(r"A strictly prior issue snapshot suggests issue ([1-9][0-9]*) may cover "
                         r"this request\. A maintainer should verify before taking any further "
                         r"action\.\n\n<!-- airflow-triage-skill:v1 -->", body)
    return bool(match)


def check(document):
    items = document.get("items", [])
    if not isinstance(items, list):
        raise ValueError("agent output items must be a list")
    label_calls = comment_calls = 0
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("safe-output item must be an object")
        kind = item_type(item)
        data = payload(item)
        if kind == "add_labels":
            label_calls += 1
            labels = label_names(data.get("labels", []))
            result = validate(labels)
            if not result["valid"]:
                raise ValueError("invalid labels: " + "; ".join(result["errors"]))
        elif kind == "add_comment":
            comment_calls += 1
            if not valid_comment(data.get("body")):
                raise ValueError("comment is not an exact fixed template or contains a mention/link")
        elif kind not in ALLOWED_NON_MUTATIONS:
            raise ValueError(f"unsupported safe-output item: {kind}")
    if label_calls > 1 or comment_calls > 1:
        raise ValueError("safe-output call count exceeded")
    return {"valid": True, "items": len(items), "label_calls": label_calls,
            "comment_calls": comment_calls}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    result = check(json.loads(Path(args.input).read_text(encoding="utf-8")))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
