from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from orchestrator import Orchestrator

EXP = ROOT / "experiments" / "exp-0003-multi-agent-execution"
RESULTS = EXP / "results"
ARTIFACT_DIR = RESULTS / "artifacts"
TASK = json.loads((EXP / "task.json").read_text(encoding="utf-8"))


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def build_request() -> dict:
    return {
        "task_id": TASK["task_id"],
        "objective": TASK["objective"],
        "input": TASK["input"],
        "constraints": {"artifact_dir": str(ARTIFACT_DIR.relative_to(ROOT))},
        "depth_profile": TASK["depth_profile"],
        "requested_artifacts": ["surface-z-x2-y2.svg"],
        "verification_requirements": {
            "required": True,
            "verifiers": ["sympy_symbolic", "svg_integrity"],
            "on_failure": "fail",
            "max_retries": 0,
            "require_provenance": True,
        },
        "context_refs": [],
        "budget": {"max_iterations": 1},
    }


def build_graph() -> dict:
    policy = {
        "required": True,
        "verifiers": ["sympy_symbolic", "svg_integrity"],
        "on_failure": "fail",
        "max_retries": 0,
        "require_provenance": True,
    }
    retry = {"max_retries": 0, "retry_on": []}
    return {
        "graph_id": "exp0003-math-to-visualization-v1",
        "task_id": TASK["task_id"],
        "nodes": [
            {
                "node_id": "math", "capability": "solve_math",
                "agent": "math-reasoning", "inputs": [], "dependencies": [],
                "constraints": {}, "verification_policy": policy,
                "retry_policy": retry, "status": "pending", "artifacts": [],
            },
            {
                "node_id": "visualization",
                "capability": "visualize_math_python",
                "agent": "python-visualization", "inputs": ["math"],
                "dependencies": ["math"], "constraints": {},
                "verification_policy": policy, "retry_policy": retry,
                "status": "pending", "artifacts": ["surface-z-x2-y2.svg"],
            },
        ],
        "entry_nodes": ["math"],
        "terminal_nodes": ["visualization"],
    }


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    orchestration = Orchestrator().execute_auto(build_request())
    ended = datetime.now(timezone.utc)

    artifact = ARTIFACT_DIR / "surface-z-x2-y2.svg"
    artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    output = {
        "protocol_version": TASK["protocol_version"],
        "experiment": TASK["experiment"],
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "git_commit": git_commit(),
        "request": build_request(),
        "graph": build_graph(),
        "orchestration": orchestration,
        "artifact": {
            "path": str(artifact.relative_to(ROOT)),
            "sha256": artifact_hash,
            "bytes": artifact.stat().st_size,
        },
        "reproducibility": {
            "deterministic_agents": True,
            "verification_is_explicit": True,
            "artifact_content_hash_recorded": True,
            "environment_commit_recorded": True,
        },
    }
    output_path = RESULTS / "run.json"
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({
        "status": orchestration["status"],
        "trace": orchestration["trace"],
        "artifact": output["artifact"],
        "result_file": str(output_path.relative_to(ROOT)),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

