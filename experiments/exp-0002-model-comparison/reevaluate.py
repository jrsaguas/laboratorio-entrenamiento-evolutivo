"""Re-evaluate stored EXP-0002 responses with the current deterministic verifier.

This tool never regenerates model responses and never overwrites the source artifact.
It produces a new immutable audit artifact so verifier improvements can be separated
from the original model-generation measurements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.math_verifier import verify_answer

REEVALUATION_VERSION = "0.1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_dataset(path: Path) -> dict[str, dict[str, Any]]:
    return {
        item["id"]: item
        for item in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reevaluate_row(row: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    response = row.get("response")
    if response is None:
        verification = {
            "ok": False,
            "method": "reevaluation",
            "details": "stored response is null",
            "metadata": {"status": "missing_response"},
        }
    else:
        result = verify_answer(
            response,
            item.get("verification_reference"),
            item.get("verification_spec"),
        )
        verification = {
            "ok": result.ok,
            "method": result.method,
            "details": result.details,
            "metadata": result.metadata,
        }

    status = (verification.get("metadata") or {}).get("status")
    original_accepts = row.get("verification_success")
    new_accepts = bool(verification["ok"])

    return {
        "id": row.get("id"),
        "model": row.get("model"),
        "original_verification_success": original_accepts,
        "verifier_accepts": new_accepts,
        "verification_status": status,
        "verification_method": verification.get("method"),
        "verification_details": verification.get("details"),
        "verification": verification,
        "verdict_changed": (
            isinstance(original_accepts, bool) and original_accepts != new_accepts
        ),
    }


def summarize_reevaluation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    changed = 0
    original_accepted = 0
    reaccepted = 0
    valid = 0

    for row in rows:
        if row.get("verifier_accepts") is True:
            reaccepted += 1
        if row.get("original_verification_success") is True:
            original_accepted += 1
        if row.get("verdict_changed"):
            changed += 1
        if row.get("verification_status"):
            status = row["verification_status"]
            statuses[status] = statuses.get(status, 0) + 1
        valid += 1

    return {
        "total": len(rows),
        "original_verifier_accepts": original_accepted,
        "reevaluated_verifier_accepts": reaccepted,
        "verdict_changed": changed,
        "reevaluated_verification_acceptance_rate": (
            reaccepted / valid if valid else None
        ),
        "statuses": statuses,
    }


def default_output_path(source: Path, verifier_commit: str | None) -> Path:
    short = (verifier_commit or "unknown")[:12]
    return (
        source.parent
        / "reevaluated"
        / f"{source.stem}--verifier-{short}.json"
    )


def reevaluate(
    source: Path,
    dataset_path: Path,
    output: Path,
) -> dict[str, Any]:
    artifact = load_json(source)
    dataset = load_dataset(dataset_path)
    verifier_commit = git_commit()

    models: dict[str, Any] = {}
    all_rows: list[dict[str, Any]] = []

    for model, model_data in artifact.get("models", {}).items():
        rows = []
        for row in model_data.get("results", []):
            task_id = row.get("id")
            if task_id not in dataset:
                raise ValueError(f"Task ID no encontrado en dataset: {task_id}")
            result = reevaluate_row(row, dataset[task_id])
            rows.append(result)
            all_rows.append(result)
        models[model] = {
            "summary": summarize_reevaluation(rows),
            "results": rows,
        }

    data = {
        "experiment": artifact.get("experiment", "exp-0002"),
        "artifact_type": "verifier_reevaluation",
        "reevaluation_version": REEVALUATION_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_artifact": {
            "path": str(source),
            "sha256": file_sha256(source),
            "run_id": (artifact.get("protocol") or {}).get("run_id"),
        },
        "dataset": {
            "path": str(dataset_path),
            "version": (artifact.get("protocol") or {}).get("dataset_version"),
        },
        "verifier": {
            "git_commit": verifier_commit,
            "tool": "tools/math_verifier.py",
        },
        "models": models,
        "summary": summarize_reevaluation(all_rows),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-evalúa respuestas almacenadas de EXP-0002 sin regenerar modelos."
    )
    parser.add_argument("artifact", type=Path, help="Artefacto JSON original de EXP-0002.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "experiments" / "exp-0001-math-verification" / "dataset.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta del nuevo artefacto. Por defecto se genera bajo results/reevaluated/.",
    )
    args = parser.parse_args()

    source = args.artifact.resolve()
    dataset = args.dataset.resolve()
    verifier_commit = git_commit()
    output = (
        args.output.resolve()
        if args.output
        else default_output_path(source, verifier_commit).resolve()
    )

    data = reevaluate(source, dataset, output)
    print(json.dumps(data["summary"], ensure_ascii=False, indent=2))
    print(f"\nArtefacto de reevaluación: {output}")


if __name__ == "__main__":
    main()
