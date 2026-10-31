#!/usr/bin/env python3
"""Seed a retry round with carried-forward non-retry manifest entries."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-round", required=True)
    parser.add_argument("--dest-round", required=True)
    parser.add_argument("--retry-case", action="append", required=True)
    args = parser.parse_args()
    source = read_json(Path(args.source_round) / "replay_manifest.json")
    retries = set(args.retry_case)
    known = {item["case_id"] for item in source["cases"]}
    missing = retries - known
    if missing:
        raise SystemExit(f"Retry cases absent from source manifest: {sorted(missing)}")
    destination = Path(args.dest_round) / "replay_manifest.json"
    if destination.exists():
        raise SystemExit(f"Destination manifest already exists: {destination}")
    seeded = {
        "schema_version": source["schema_version"],
        "builder_commit": source["builder_commit"],
        "expected_commit": source["expected_commit"],
        "cases": [item for item in source["cases"] if item["case_id"] not in retries],
        "retry_cases": sorted(retries),
        "source_round": str(Path(args.source_round)).replace("\\", "/"),
    }
    write_json(destination, seeded)
    print(f"Seeded {len(seeded['cases'])} carried entries; retrying {len(retries)} cases.")


if __name__ == "__main__":
    main()
