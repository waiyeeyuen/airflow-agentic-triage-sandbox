#!/usr/bin/env python3
"""Render the only comment bodies the triage workflow may request."""
import argparse
import json
from pathlib import Path

MARKER = "<!-- airflow-triage-skill:v1 -->"


def render(kind, duplicate_number=None, question=None):
    if kind == "none":
        return ""
    if kind == "security_route":
        text = ("This report may contain security-sensitive information. Please use the "
                "private process described in `.github/SECURITY.md`; no exploitability "
                "assessment was made here.")
    elif kind == "duplicate_notice":
        if not isinstance(duplicate_number, int) or duplicate_number <= 0:
            raise ValueError("duplicate_notice requires a positive duplicate number")
        text = f"A strictly prior issue snapshot suggests issue {duplicate_number} may cover this request. A maintainer should verify before taking any further action."
    elif kind == "clarification":
        allowed = {"version": "Please provide the affected Airflow version.",
                   "reproduction": "Please provide a minimal reproduction and the relevant logs.",
                   "expected": "Please describe the expected and actual behaviour."}
        if question not in allowed:
            raise ValueError("clarification question is not allowlisted")
        text = allowed[question]
    else:
        raise ValueError("unknown comment type")
    return f"{text}\n\n{MARKER}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, help="Prepared case JSON")
    parser.add_argument("--type", required=True, choices=("none", "security_route", "duplicate_notice", "clarification"))
    parser.add_argument("--duplicate-number", type=int)
    parser.add_argument("--question")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    if not isinstance(case.get("title"), str):
        parser.error("prepared case must contain a title")
    body = render(args.type, args.duplicate_number, args.question)
    Path(args.output).write_text(json.dumps({"comment_type": args.type, "body": body}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
