"""EXP-0002: controlled comparison of mathematical LLMs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.metrics.metrics import summarize
from tools.math_verifier import verify_answer
from tools.model_runtime import generate

PROTOCOL_VERSION = "0.1"
DATASET_VERSION = "0.1"
EXPERIMENT_VERSION = "0.1"


def load_dataset(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True, check=True,
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def verify(item: dict[str, Any], candidate: str) -> dict[str, Any]:
    result = verify_answer(
        candidate, item.get("verification_reference"), item.get("verification_spec")
    )
    return {
        "ok": result.ok,
        "method": result.method,
        "details": result.details,
        "metadata": result.metadata,
    }


def timed_verify(item: dict[str, Any], candidate: str) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    result = verify(item, candidate)
    return result, round((time.perf_counter() - started) * 1000, 3)


def ask(item: dict[str, Any], *, model: str, endpoint: str, temperature: float,
        max_tokens: int, timeout: float | None, seed: int | None) -> tuple[str, float, dict[str, Any]]:
    prompt = (
        "Resuelve el siguiente problema matemático. "
        "Devuelve ÚNICAMENTE la respuesta final, sin explicación.\n\n"
        f"Problema: {item['prompt']}\n"
    )
    started = time.perf_counter()
    response = generate(
        prompt, endpoint=endpoint, model=model, temperature=temperature,
        max_tokens=max_tokens, timeout=timeout, think=False, seed=seed,
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    raw = response.raw
    runtime = {
        "total_duration_ns": raw.get("total_duration"),
        "load_duration_ns": raw.get("load_duration"),
        "prompt_eval_count": raw.get("prompt_eval_count"),
        "eval_count": raw.get("eval_count"),
        "eval_duration_ns": raw.get("eval_duration"),
    }
    if isinstance(runtime["eval_count"], (int, float)) and isinstance(runtime["eval_duration_ns"], (int, float)) and runtime["eval_duration_ns"] > 0:
        runtime["tokens_per_second"] = round(
            runtime["eval_count"] / (runtime["eval_duration_ns"] / 1_000_000_000), 3
        )
    return response.text.strip(), latency_ms, runtime


def make_row(item: dict[str, Any], model: str, response: str, latency_ms: float,
             runtime: dict[str, Any], verification: dict[str, Any],
             verification_latency_ms: float) -> dict[str, Any]:
    return {
        "id": item["id"],
        "model": model,
        "category": item["category"],
        "difficulty": item["difficulty"],
        "response": response,
        "expected": item["answer"],
        "contains_expected": item["answer"] in response,
        "exact_match": response.strip() == item["answer"].strip(),
        "semantic_correct": bool(verification["ok"]),
        "verification_success": bool(verification["ok"]),
        "first_verification_success": bool(verification["ok"]),
        "initial_semantic_correct": bool(verification["ok"]),
        "repair_attempted": False,
        "verification": verification,
        "oracle_verification": verification,
        "generation_latency_ms": latency_ms,
        "verification_latency_ms": verification_latency_ms,
        "latency_ms": round(latency_ms + verification_latency_ms, 3),
        "observed_latency_ms": round(latency_ms + verification_latency_ms, 3),
        "runtime": runtime,
        "generation_reused": False,
        "error": None,
    }


def protocol(args: argparse.Namespace, run_id: str, models: list[str]) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "run_id": run_id,
        "git_commit": git_commit(),
        "dataset_version": DATASET_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "models": models,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "max_tokens_mode": "unlimited" if args.max_tokens == -1 else "bounded",
        "seed": args.seed,
        "timeout_seconds": None if args.timeout <= 0 else args.timeout,
        "timeout_mode": "unlimited" if args.timeout <= 0 else "bounded",
        "same_prompt": True,
        "same_generation_parameters": True,
        "deterministic_verification": True,
        "repair": False,
    }


def save(path: Path, model_rows: dict[str, list[dict[str, Any]]], proto: dict[str, Any],
         status: str = "in_progress") -> None:
    data = {
        "experiment": "exp-0002",
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": proto,
        "models": {
            model: {"summary": summarize(rows), "results": rows}
            for model, rows in model_rows.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", required=True, help="Comma-separated Ollama model names.")
    parser.add_argument("--dataset", default="experiments/exp-0001-math-verification/dataset.jsonl")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ids", default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=-1)
    parser.add_argument("--timeout", type=float, default=0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", default="experiments/exp-0002-model-comparison/results/run.json")
    args = parser.parse_args()

    models = list(dict.fromkeys(m.strip() for m in args.models.split(",") if m.strip()))
    if not models:
        parser.error("--models no puede estar vacío.")

    dataset = load_dataset(Path(args.dataset))
    if args.ids:
        requested = [x.strip() for x in args.ids.split(",") if x.strip()]
        by_id = {item["id"]: item for item in dataset}
        missing = [x for x in requested if x not in by_id]
        if missing:
            parser.error("Task IDs no encontrados: " + ", ".join(missing))
        dataset = [by_id[x] for x in requested]
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit debe ser >= 1")
        dataset = dataset[:args.limit]
    if not dataset:
        parser.error("El conjunto de tareas seleccionado está vacío.")

    timeout = None if args.timeout <= 0 else args.timeout
    output = Path(args.output)
    run_id = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    proto = protocol(args, run_id, models)
    rows = {model: [] for model in models}

    print("=" * 68)
    print("EXP-0002 — Comparación controlada de modelos")
    print("=" * 68)
    print(f"Modelos: {', '.join(models)}")
    print(f"Problemas: {len(dataset)}")
    print(f"Temperatura: {args.temperature}")
    print(f"Máximo de tokens: {args.max_tokens}")
    print("Reparación: no")
    print("=" * 68)

    total = len(models) * len(dataset)
    completed = 0

    for model in models:
        for item in dataset:
            completed += 1
            print(f"\n[{completed}/{total}] {model} — {item['id']}")
            started = time.perf_counter()
            try:
                response, generation_latency, runtime = ask(
                    item, model=model, endpoint=args.endpoint,
                    temperature=args.temperature, max_tokens=args.max_tokens,
                    timeout=timeout, seed=args.seed,
                )
                verification, verification_latency = timed_verify(item, response)
                row = make_row(
                    item, model, response, generation_latency, runtime,
                    verification, verification_latency,
                )
            except Exception as exc:
                elapsed = round((time.perf_counter() - started) * 1000, 3)
                row = {
                    "id": item["id"], "model": model, "category": item["category"],
                    "difficulty": item["difficulty"], "response": None,
                    "expected": item["answer"], "contains_expected": False,
                    "exact_match": False, "semantic_correct": False,
                    "verification_success": False, "verification": None,
                    "oracle_verification": None, "generation_latency_ms": elapsed,
                    "verification_latency_ms": 0.0, "latency_ms": elapsed,
                    "observed_latency_ms": elapsed, "runtime": {},
                    "generation_reused": False,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
                print(f"  ERROR: {row['error']['type']}: {row['error']['message']}")
            rows[model].append(row)
            save(output, rows, proto)

    save(output, rows, proto, status="completed")
    print("\nEXPERIMENTO FINALIZADO")
    print(json.dumps({model: summarize(values) for model, values in rows.items()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
