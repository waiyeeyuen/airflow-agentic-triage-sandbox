"""Fixed-path runtime for the no-argument triage command wrappers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from render_comment import render  # noqa: E402
from search_duplicates import rank, resolve_corpus  # noqa: E402
from validate_labels import validate  # noqa: E402

CASE = Path("/tmp/gh-aw/agent/case.json")
DUPLICATES = Path("/tmp/gh-aw/agent/duplicates.json")
VALIDATED = Path("/tmp/gh-aw/agent/validated.json")
COMMENT = Path("/tmp/gh-aw/agent/comment.json")
CORPUS_ROOT = ROOT / "evals" / "golden" / "cases"

LABEL_COMMANDS = {
    "triage-label-security": "security",
    "triage-label-kind-bug": "kind:bug",
    "triage-label-kind-feature": "kind:feature",
    "triage-label-kind-task": "kind:task",
    "triage-label-kind-documentation": "kind:documentation",
    "triage-label-kind-meta": "kind:meta",
    "triage-label-area-core": "area:core",
    "triage-label-area-providers": "area:providers",
    "triage-label-area-api": "area:API",
    "triage-label-area-ui": "area:UI",
    "triage-label-area-kubernetes": "area:kubernetes",
    "triage-label-area-scheduler": "area:scheduler",
    "triage-label-area-dev-env": "area:dev-env",
    "triage-label-area-airflow-ctl": "area:airflow-ctl",
    "triage-label-provider-amazon": "provider:amazon",
    "triage-label-provider-fab": "provider:fab",
    "triage-label-provider-google": "provider:google",
    "triage-label-provider-openlineage": "provider:openlineage",
    "triage-label-provider-standard": "provider:standard",
}

COMMENT_COMMANDS = {
    "triage-comment-none": ("none", None),
    "triage-comment-security-route": ("security_route", None),
    "triage-comment-clarification-version": ("clarification", "version"),
    "triage-comment-clarification-reproduction": ("clarification", "reproduction"),
    "triage-comment-clarification-expected": ("clarification", "expected"),
}


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value):
    with path.open("w", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, indent=2) + "\n")


def run(command: str, *, case=CASE, duplicates=DUPLICATES, validated=VALIDATED,
        comment=COMMENT, corpus_root=CORPUS_ROOT):
    """Execute one finite command using only fixed inputs and outputs."""
    case_data = _read(case)
    if command == "triage-search-duplicates":
        try:
            corpus_path = resolve_corpus(case_data, corpus_root)
        except ValueError as error:
            if str(error) != "expected one frozen case title match, found 0":
                raise
            _write(duplicates, {"method": "tf-idf-cosine-v1", "candidates": []})
            return
        prior = _read(corpus_path)
        query = f"{(case_data.get('title', '') + ' ') * 5}{case_data.get('body', '')}"
        _write(duplicates, {"method": "tf-idf-cosine-v1", "candidates": rank(query, prior, 5)})
        return

    if command == "triage-label-none":
        proposed = []
    elif command in LABEL_COMMANDS:
        if not validated.exists():
            raise ValueError("triage-label-none must run before label selection")
        proposed = _read(validated).get("labels", []) + [LABEL_COMMANDS[command]]
    else:
        proposed = None
    if proposed is not None:
        current = case_data.get("current_labels", case_data.get("labels_at_creation", []))
        result = validate(proposed, current)
        _write(validated, result)
        if not result["valid"]:
            raise SystemExit(2)
        return

    if command.startswith("triage-comment-duplicate-"):
        rank_number = int(command.rsplit("-", 1)[1])
        candidates = _read(duplicates).get("candidates", [])
        if rank_number < 1 or rank_number > len(candidates):
            raise ValueError("duplicate rank is unavailable")
        kind, value = "duplicate_notice", candidates[rank_number - 1]["number"]
        body = render(kind, duplicate_number=value)
    elif command in COMMENT_COMMANDS:
        kind, value = COMMENT_COMMANDS[command]
        body = render(kind, question=value)
    else:
        raise ValueError(f"unknown wrapper command: {command}")
    if not isinstance(case_data.get("title"), str):
        raise ValueError("prepared case must contain a title")
    _write(comment, {"comment_type": kind, "body": body})


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) != 1:
        raise SystemExit("triage wrappers accept no arguments")
    run(Path(argv[0]).name)
