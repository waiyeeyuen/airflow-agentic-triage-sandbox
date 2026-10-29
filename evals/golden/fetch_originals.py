#!/usr/bin/env python3
"""Fetch selected issue edit histories through read-only `gh api graphql`."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden"
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gh", required=True, help="Path to gh.exe")
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--output-subdir", default="raw/graphql")
    args = parser.parse_args()
    selection = json.loads((GOLDEN / "selection.json").read_text(encoding="utf-8"))
    raw_dir = GOLDEN / args.output_subdir
    raw_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for selected in selection["selected"]:
        number = int(selected["number"])
        path = raw_dir / f"{number}.json"
        if not (args.reuse and path.exists()):
            command = [
                args.gh,
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
            path.write_text(completed.stdout, encoding="utf-8")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        issue = payload["data"]["repository"]["issue"]
        if issue is None or issue["number"] != number:
            raise RuntimeError(f"GraphQL did not return issue {number}")
        edits = issue["userContentEdits"]
        if edits["pageInfo"]["hasNextPage"]:
            raise RuntimeError(f"Issue {number} has more than 100 edits; pagination is required")
        summary.append({"number": number, "edit_count": len(edits["nodes"]), "created_at": issue["createdAt"]})
        print(f"saved {number}: {len(edits['nodes'])} edits")
    summary_name = "edit_history_summary.json" if args.output_subdir == "raw/graphql" else "verification_edit_history_summary.json"
    (GOLDEN / summary_name).write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
