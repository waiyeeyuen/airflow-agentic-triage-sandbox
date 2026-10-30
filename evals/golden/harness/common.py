"""Shared helpers for the Tester-owned Part B harness."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = ROOT / "evals" / "golden"
HARNESS = GOLDEN / "harness"
DEFAULT_GH = ROOT.parent / ".tools" / "gh" / "bin" / "gh.exe"
REPO = "waiyeeyuen/airflow-agentic-triage-sandbox"
BUILDER_COMMIT = "2a5e692b9066cb0cf54d98d5d9ead75525afeeb3"
EXPECTED_COMMIT = "dd295091c8a89bd7ccb06662d996f6a5ba960e5c"
DEFAULT_ROUND_DIR = Path("evals/golden/actual/round_3")
ROUND_ONE_DIR = ROOT / "evals" / "golden" / "actual" / "round_1"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def adversarial_path(case_id: str) -> Path:
    slug = case_id.removeprefix("adversarial-").replace("-", "_")
    return GOLDEN / "adversarial" / f"{slug}.json"


def input_path(case_id: str) -> Path:
    if case_id.startswith("airflow-"):
        return GOLDEN / "cases" / case_id.split("-")[-1] / "input.json"
    return adversarial_path(case_id)


def validate_replay_text(data: dict) -> None:
    text = (data.get("title") or "") + "\n" + (data.get("body") or "")
    if "@" in text:
        raise ValueError("Replay text contains an @ mention")
    if re.search(r"(?i)github\.com/apache/airflow/(?:issues|pull)/\d+|apache/airflow#\d+", text):
        raise ValueError("Replay text contains an upstream cross-reference")


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, capture_output=True, text=True, encoding="utf-8")


def gh_json(gh: str, arguments: list[str]):
    completed = run([gh, *arguments])
    return json.loads(completed.stdout or "null")
