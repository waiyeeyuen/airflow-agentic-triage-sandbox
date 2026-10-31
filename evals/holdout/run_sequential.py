#!/usr/bin/env python3
"""Dispatch holdout cases sequentially with a strict aggregate AIC admission check."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOLDOUT = ROOT / "evals" / "holdout"
REPO = "waiyeeyuen/airflow-agentic-triage-sandbox"
WORKFLOW = "400791846"
REF = "holdout-eval"
SHA = "96727004b780f961f5c7e331e8024221116b2762"
TOTAL_CAP = 120.0
PER_RUN_CAP = 25.0


def run(arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(arguments, cwd=ROOT, text=True, encoding="utf-8", capture_output=True)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(arguments)}\n{result.stderr}")
    return result


def gh_json(arguments: list[str]):
    return json.loads(run(["gh", *arguments]).stdout)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def cumulative() -> float:
    path = HOLDOUT / "actual" / "run_manifest.json"
    return float(read_json(path).get("total_aic_all_attempts", 0)) if path.exists() else 0.0


def completed_cases() -> set[str]:
    path = HOLDOUT / "actual" / "run_manifest.json"
    if not path.exists():
        return set()
    return {row["case_id"] for row in read_json(path)["attempts"] if not row.get("retryable_429")}


def dispatch(case_id: str, number: int, known_runs: set[int]) -> int:
    started = datetime.now(timezone.utc)
    run(["gh", "variable", "set", "TRIAGE_AGENT_ENABLED", "--body", "true", "--repo", REPO])
    try:
        run(
            [
                "gh", "workflow", "run", WORKFLOW, "--repo", REPO, "--ref", REF,
                "-f", f"case_path=evals/holdout/cases/{number}/input.json",
            ]
        )
        for _ in range(8):
            time.sleep(5)
            runs = gh_json(
                [
                    "run", "list", "--repo", REPO, "--workflow", WORKFLOW, "--branch", REF,
                    "--event", "workflow_dispatch", "--limit", "20", "--json",
                    "databaseId,url,createdAt,status,conclusion,headSha",
                ]
            )
            candidates = [
                row for row in runs
                if int(row["databaseId"]) not in known_runs
                and row["headSha"] == SHA
                and datetime.fromisoformat(row["createdAt"].replace("Z", "+00:00")) >= started - timedelta(seconds=5)
            ]
            if candidates:
                latest = sorted(candidates, key=lambda row: row["createdAt"], reverse=True)[0]
                run_id = int(latest["databaseId"])
                for _ in range(60):
                    state = gh_json(
                        [
                            "run", "view", str(run_id), "--repo", REPO, "--json",
                            "status,conclusion,jobs",
                        ]
                    )
                    pre_activation = next(
                        (job for job in state["jobs"] if job["name"] == "pre_activation"),
                        None,
                    )
                    if (
                        pre_activation
                        and pre_activation["status"] == "completed"
                        and pre_activation["conclusion"] == "success"
                    ):
                        print(f"DISPATCHED {case_id} run={run_id} passed pre_activation", flush=True)
                        return run_id
                    if state["status"] == "completed":
                        raise RuntimeError(f"Run {run_id} completed without passing pre_activation")
                    time.sleep(5)
                raise RuntimeError(f"Run {run_id} did not pass pre_activation while switch was true")
        raise RuntimeError(f"Could not identify dispatched run for {case_id}")
    finally:
        run(["gh", "variable", "set", "TRIAGE_AGENT_ENABLED", "--body", "false", "--repo", REPO])


def wait_complete(case_id: str, run_id: int) -> dict:
    for poll in range(60):
        view = gh_json(
            [
                "run", "view", str(run_id), "--repo", REPO, "--json",
                "databaseId,url,status,conclusion,headSha",
            ]
        )
        if view["headSha"] != SHA:
            raise RuntimeError(f"Run {run_id} used unexpected SHA {view['headSha']}")
        if view["status"] == "completed":
            print(f"COMPLETED {case_id} run={run_id} conclusion={view['conclusion']}", flush=True)
            return view
        if poll % 3 == 0:
            print(f"WAITING {case_id} run={run_id} status={view['status']}", flush=True)
        time.sleep(20)
    raise RuntimeError(f"Run {run_id} did not complete within 20 minutes")


def capture(case_id: str, run_id: int, attempt: int) -> dict:
    result = run(
        [
            sys.executable, str(HOLDOUT / "capture_holdout.py"), "--case-id", case_id,
            "--run-id", str(run_id), "--attempt", str(attempt), "--gh", "gh",
        ]
    )
    data = json.loads(result.stdout)
    print(
        f"AUDITED {case_id} run={run_id} aic={data['aic']:.4f} "
        f"cumulative={data['cumulative_aic']:.4f} retryable_429={data['retryable_429']}",
        flush=True,
    )
    return data


def main() -> None:
    selection = read_json(HOLDOUT / "selection.json")["selected"]
    known_runs = {
        int(row["run_id"])
        for row in read_json(HOLDOUT / "actual" / "run_manifest.json").get("attempts", [])
    }
    done = completed_cases()
    run(["gh", "variable", "set", "TRIAGE_AGENT_ENABLED", "--body", "false", "--repo", REPO])
    try:
        for selected in selection:
            case_id = f"airflow-{selected['number']}"
            if case_id in done:
                print(f"SKIP completed {case_id}", flush=True)
                continue
            attempt = 1
            while attempt <= 2:
                spent = cumulative()
                if spent + PER_RUN_CAP > TOTAL_CAP:
                    print(
                        f"HARD_CAP_STOP before {case_id}: cumulative={spent:.4f}, "
                        f"remaining={TOTAL_CAP - spent:.4f}, required_reserve={PER_RUN_CAP:.4f}",
                        flush=True,
                    )
                    return
                run_id = dispatch(case_id, int(selected["number"]), known_runs)
                known_runs.add(run_id)
                wait_complete(case_id, run_id)
                result = capture(case_id, run_id, attempt)
                if result["retryable_429"] and attempt == 1:
                    print(f"RETRY_429 {case_id} once", flush=True)
                    attempt += 1
                    continue
                break
    finally:
        run(["gh", "variable", "set", "TRIAGE_AGENT_ENABLED", "--body", "false", "--repo", REPO])
    print(f"SEQUENTIAL_RUNS_FINISHED cumulative={cumulative():.4f}", flush=True)


if __name__ == "__main__":
    main()
