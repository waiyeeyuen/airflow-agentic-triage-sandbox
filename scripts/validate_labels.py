#!/usr/bin/env python3
"""Validate proposed triage labels against the hard policy."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def validate(proposed, current=()):
    policy = json.loads((ROOT / "label_policy.json").read_text(encoding="utf-8"))
    labels = list(dict.fromkeys(proposed))
    errors = []
    if len(labels) != len(proposed):
        errors.append("duplicate proposed labels")
    unknown = sorted(set(labels) - set(policy["allowed"]))
    if unknown:
        errors.append("labels outside allowlist: " + ", ".join(unknown))
    if len(labels) > policy["max_labels"]:
        errors.append(f"more than {policy['max_labels']} labels")
    for prefix in ("kind:", "area:", "provider:"):
        if sum(label.startswith(prefix) for label in labels) > 1:
            errors.append(f"more than one {prefix} label")
    if set(labels) & set(current):
        errors.append("proposed labels already present")
    if "security" in labels and labels != ["security"]:
        errors.append("security must be the only proposed label")
    has_provider_area = "area:providers" in labels or "area:providers" in current
    if any(label.startswith("provider:") for label in labels) and not has_provider_area:
        errors.append("provider label requires area:providers")
    return {"valid": not errors, "labels": labels if not errors else [], "errors": errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON with proposed_labels/current_labels")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = validate(data.get("proposed_labels", []), data.get("current_labels", []))
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not result["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
