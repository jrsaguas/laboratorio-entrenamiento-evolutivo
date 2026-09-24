"""Run EXP-0001 with paired initial generations and explicit intervention stages."""

from __future__ import annotations

import argparse
import json
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


def load_dataset(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ask(item: dict[str, Any], *, endpoint: str, model: str, temperature: float,
        max_tokens: int, timeout: float | None, seed: int | None = None,
        feedback: str | None = None) -> tuple[str, float, dict[str, Any]]:
    prompt = (
        "Resuelve el siguiente problema matemático. "
        "Devuelve ÚNICAMENTE la respuesta final, sin explicación.\n\n"
        f"Problema: {item['prompt']}\n"
    )
    if feedback:
        prompt += (
            "\nEl verificador encontró un problema con la respuesta anterior. "
            "Corrígela y devuelve únicamente la respuesta final.\n"
            f"Retroalimentación: {feedback}\n"
        )

    started = time.perf_counter()
    response = generate(
        prompt, endpoint=endpoint, model=model, temperature=temperature,
        max_tokens=max_tokens, timeout=timeout, think=False, seed=seed,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    raw = response.raw
    eval_count = raw.get("eval_count")
    eval_duration_ns = raw.get("eval_duration")
    tokens_per_second = None
    if isinstance(eval_count, (int, float)) and isinstance(eval_duration_ns, (int, float)) and eval_duration_ns > 0:
        tokens_per_second = round(eval_count / (eval_duration_ns / 1_000_000_000), 3)
    runtime = {
        "total_duration_ns": raw.get("total_duration"),
        "load_duration_ns": raw.get("load_duration"),
        "prompt_eval_count": raw.get("prompt_eval_count"),
        "eval_count": eval_count,
        "eval_duration_ns": eval_duration_ns,
        "tokens_per_second": tokens_per_second,
    }
    return response.text.strip(), elapsed_ms, runtime


def verify(item: dict[str, Any], candidate: str) -> dict[str, Any]:
    if item.get("verification_reference") is None and item.get("verification_spec") is None:
        return {"ok": False, "method": None, "details": "no verification reference or specification",
                "metadata": {"status": "missing_reference"}}
    result = verify_answer(candidate, item.get("verification_reference"), item.get("verification_spec"))
    return {"ok": result.ok, "method": result.method, "details": result.details, "metadata": result.metadata}


def timed_verify(item: dict[str, Any], candidate: str) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    result = verify(item, candidate)
    return result, round((time.perf_counter() - started) * 1000, 3)


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "n/d"
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"


def estimate(rows: list[dict[str, Any]], remaining: int) -> str:
    samples = [r["latency_ms"] / 1000 for r in rows
               if isinstance(r.get("latency_ms"), (int, float)) and not r.get("error")]
    if not samples or remaining <= 0:
        return "n/d"
    return format_duration((sum(samples) / len(samples)) * remaining)


def protocol(args: argparse.Namespace, timeout: float | None) -> dict[str, Any]:
    return {
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "max_tokens_mode": "unlimited" if args.max_tokens == -1 else "bounded",
        "seed": args.seed,
        "timeout_seconds": timeout,
        "timeout_mode": "unlimited" if timeout is None else "bounded",
        "same_generation_protocol": True,
        "paired_initial_generation": True,
        "resumable": True,
        "repair_is_separate_condition": True,
    }


def save_state(path: Path, model: str, rows: dict[str, list[dict[str, Any]]],
               proto: dict[str, Any], status: str = "in_progress") -> None:
    data = {
        "experiment": "exp-0001", "model": model, "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "conditions": {
            name: {"summary": summarize(values), "results": values}
            for name, values in rows.items()
        },
        "protocol": proto,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert(rows: list[dict[str, Any]], row: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("id") != row.get("id")] + [row]


def run_condition(dataset: list[dict[str, Any]], condition: str, *, endpoint: str,
                  model: str, temperature: float, max_tokens: int, timeout: float | None,
                  seed: int | None, rows: dict[str, list[dict[str, Any]]],
                  existing: dict[str, dict[str, Any]], initial_cache: dict[str, dict[str, Any]],
                  output: Path, proto: dict[str, Any], repair: bool = False) -> None:
    completed = {key for key, value in existing.items() if not value.get("error")}

    for item in dataset:
        task_id = item["id"]
        if task_id in completed:
            continue

        total_tasks = len(dataset) * (3 if repair else 2)
        done = sum(len(v) for v in rows.values())
        print(f"\n[{done + 1}/{total_tasks}] {condition} — {task_id}")
        print(f"  Estimación restante: {estimate(rows[condition], max(0, total_tasks - done))}")

        started = time.perf_counter()
        try:
            cached = initial_cache.get(task_id)
            generation_reused = cached is not None and condition != "baseline"

            if generation_reused:
                initial_response = cached["response"]
                initial_latency = float(cached["initial_latency_ms"])
                initial_runtime = cached.get("runtime", {})
            else:
                initial_response, initial_latency, initial_runtime = ask(
                    item, endpoint=endpoint, model=model, temperature=temperature,
                    max_tokens=max_tokens, timeout=timeout, seed=seed,
                )
                if condition == "baseline":
                    initial_cache[task_id] = {
                        "response": initial_response,
                        "initial_latency_ms": initial_latency,
                        "runtime": initial_runtime,
                    }

            initial_verification = None
            verification_latency = 0.0
            if condition != "baseline":
                initial_verification, verification_latency = timed_verify(item, initial_response)

            final_response = initial_response
            final_verification = initial_verification
            repair_attempted = False
            repair_latency = 0.0
            repair_runtime = None

            if (condition == "verified_repair" and repair and initial_verification
                    and not initial_verification["ok"]):
                repair_attempted = True
                final_response, repair_latency, repair_runtime = ask(
                    item, endpoint=endpoint, model=model, temperature=temperature,
                    max_tokens=max_tokens, timeout=timeout, seed=seed,
                    feedback=initial_verification["details"],
                )
                final_verification, repair_verify_latency = timed_verify(item, final_response)
                verification_latency = round(verification_latency + repair_verify_latency, 3)

            oracle_verification, oracle_latency = timed_verify(item, final_response)
            verification_latency = round(verification_latency + oracle_latency, 3)

            row = {
                "id": task_id,
                "category": item["category"],
                "condition": condition,
                "attempt": int(existing.get(task_id, {}).get("attempt", 0)) + 1,
                "response": final_response,
                "initial_response": initial_response,
                "repair_response": final_response if repair_attempted else None,
                "expected": item["answer"],
                "contains_expected": item["answer"] in final_response,
                "exact_match": final_response == item["answer"],
                "semantic_correct": bool(oracle_verification["ok"]),
                "verification_success": bool(final_verification and final_verification["ok"]),
                "first_verification_success": bool(initial_verification and initial_verification["ok"]),
                "repair_attempted": repair_attempted,
                "verification": final_verification,
                "initial_verification": initial_verification,
                "oracle_verification": oracle_verification,
                "verification_latency_ms": verification_latency,
                "initial_latency_ms": initial_latency,
                "repair_latency_ms": repair_latency,
                "latency_ms": round(initial_latency + verification_latency + repair_latency, 3),
                "runtime": {"initial": initial_runtime, "repair": repair_runtime},
                "generation_reused": generation_reused,
                "error": None,
            }
        except Exception as exc:
            elapsed = round((time.perf_counter() - started) * 1000, 3)
            row = {
                "id": task_id, "category": item["category"], "condition": condition,
                "attempt": int(existing.get(task_id, {}).get("attempt", 0)) + 1,
                "response": None, "initial_response": None, "repair_response": None,
                "expected": item["answer"], "contains_expected": False, "exact_match": False,
                "semantic_correct": False, "verification_success": False,
                "first_verification_success": False, "repair_attempted": False,
                "verification": None, "initial_verification": None, "oracle_verification": None,
                "verification_latency_ms": 0.0, "initial_latency_ms": elapsed,
                "repair_latency_ms": 0.0, "latency_ms": elapsed, "runtime": {},
                "generation_reused": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
            print(f"  ERROR: {row['error']['type']}: {row['error']['message']}")

        rows[condition] = upsert(rows[condition], row)
        save_state(output, model, rows, proto)
        print(f"  Tiempo: {format_duration(row['latency_ms'] / 1000)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="experiments/exp-0001-math-verification/dataset.jsonl")
    parser.add_argument("--ids", default=None, help="Comma-separated task IDs to run, e.g. math-001,math-019.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N tasks after --ids filtering.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=-1,
                        help="Maximum generated tokens; -1 means unlimited generation.")
    parser.add_argument("--timeout", type=float, default=0,
                        help="Seconds; 0 disables the client-side timeout.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--repair", action="store_true",
                        help="Run the separate verified_repair condition.")
    parser.add_argument("--output", default="experiments/exp-0001-math-verification/results/run.json")
    parser.add_argument("--new-run", action="store_true")
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))
    if args.ids:
        requested_ids = [value.strip() for value in args.ids.split(",") if value.strip()]
        by_id = {item["id"]: item for item in dataset}
        missing = [task_id for task_id in requested_ids if task_id not in by_id]
        if missing:
            parser.error("Task IDs no encontrados: " + ", ".join(missing))
        dataset = [by_id[task_id] for task_id in requested_ids]
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit debe ser >= 1")
        dataset = dataset[:args.limit]
    if not dataset:
        parser.error("El conjunto de tareas seleccionado está vacío.")

    timeout = None if args.timeout <= 0 else args.timeout
    output = Path(args.output)
    if args.new_run and args.output.endswith("results/run.json"):
        output = output.with_name(f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")

    rows = {"baseline": [], "verified": [], "verified_repair": []}
    existing = {name: {} for name in rows}

    if output.exists() and not args.new_run:
        try:
            previous = json.loads(output.read_text(encoding="utf-8"))
            compatible = (
                previous.get("model") == args.model
                and previous.get("protocol", {}).get("paired_initial_generation") is True
            )
            if compatible:
                for name in rows:
                    old = previous.get("conditions", {}).get(name, {}).get("results", [])
                    existing[name] = {r.get("id"): r for r in old if r.get("id")}
                    rows[name] = list(existing[name].values())
        except (OSError, json.JSONDecodeError):
            pass

    proto = protocol(args, timeout)
    initial_cache = {
        r["id"]: {
            "response": r.get("initial_response") or r.get("response"),
            "initial_latency_ms": r.get("initial_latency_ms", 0),
            "runtime": (r.get("runtime") or {}).get("initial", {}),
        }
        for r in rows["baseline"] if r.get("id") and not r.get("error")
    }

    print("=" * 68)
    print("EXP-0001 — Verificación matemática determinista")
    print("=" * 68)
    print(f"Modelo: {args.model}")
    print(f"Problemas: {len(dataset)}")
    if args.ids:
        print(f"Tareas seleccionadas: {args.ids}")
    if args.limit is not None:
        print(f"Límite de tareas: {args.limit}")
    print("Condiciones: baseline + verified" + (" + verified_repair" if args.repair else ""))
    print(f"Temperatura: {args.temperature}")
    print(f"Máximo de tokens: {args.max_tokens}")
    print(f"Timeout: {'sin límite' if timeout is None else format_duration(timeout)}")
    print(f"Seed: {args.seed if args.seed is not None else 'no fijada'}")
    print("Generación inicial emparejada: sí")
    print("=" * 68)

    run_condition(dataset, "baseline", endpoint=args.endpoint, model=args.model,
                  temperature=args.temperature, max_tokens=args.max_tokens, timeout=timeout,
                  seed=args.seed, rows=rows, existing=existing["baseline"],
                  initial_cache=initial_cache, output=output, proto=proto)

    run_condition(dataset, "verified", endpoint=args.endpoint, model=args.model,
                  temperature=args.temperature, max_tokens=args.max_tokens, timeout=timeout,
                  seed=args.seed, rows=rows, existing=existing["verified"],
                  initial_cache=initial_cache, output=output, proto=proto)

    if args.repair:
        run_condition(dataset, "verified_repair", endpoint=args.endpoint, model=args.model,
                      temperature=args.temperature, max_tokens=args.max_tokens, timeout=timeout,
                      seed=args.seed, rows=rows, existing=existing["verified_repair"],
                      initial_cache=initial_cache, output=output, proto=proto, repair=True)

    save_state(output, args.model, rows, proto, status="completed")
    print("\nEXPERIMENTO FINALIZADO")
    print(json.dumps({name: summarize(values) for name, values in rows.items()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
