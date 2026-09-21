"""Run EXP-0001 with progress, ETA, resumability and structured records."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow direct execution from the repository root without requiring PYTHONPATH.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.metrics.metrics import summarize
from tools.math_verifier import verify_answer
from tools.model_runtime import generate


def load_dataset(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def ask(
    item: dict[str, Any],
    *,
    endpoint: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float | None,
    feedback: str | None = None,
) -> tuple[str, float, dict[str, Any]]:
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
        prompt,
        endpoint=endpoint,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        think=False,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    raw = response.raw
    runtime = {
        "total_duration_ns": raw.get("total_duration"),
        "load_duration_ns": raw.get("load_duration"),
        "prompt_eval_count": raw.get("prompt_eval_count"),
        "eval_count": raw.get("eval_count"),
        "eval_duration_ns": raw.get("eval_duration"),
    }
    return response.text.strip(), elapsed_ms, runtime


def verify(item: dict[str, Any], candidate: str) -> dict[str, Any]:
    reference = item.get("verification_reference")
    if not reference:
        return {
            "ok": False,
            "method": None,
            "details": "no verification reference",
            "metadata": {"status": "missing_reference"},
        }

    result = verify_answer(candidate, reference)
    return {
        "ok": result.ok,
        "method": result.method,
        "details": result.details,
        "metadata": result.metadata,
    }


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "n/d"
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


def estimate_from_rows(rows: list[dict[str, Any]], remaining: int) -> tuple[float | None, str]:
    samples = [
        r["latency_ms"] / 1000
        for r in rows
        if isinstance(r.get("latency_ms"), (int, float)) and not r.get("error")
    ]
    if not samples or remaining <= 0:
        return None, "n/d"
    avg = sum(samples) / len(samples)
    return avg * remaining, format_duration(avg * remaining)


def print_header(
    *,
    model: str,
    dataset_size: int,
    timeout: float | None,
    temperature: float,
    max_tokens: int,
    historical_seconds: float | None,
) -> None:
    calls = dataset_size * 2
    theoretical = calls * timeout if timeout is not None else None
    print("=" * 68)
    print("EXP-0001 — Verificación matemática determinista")
    print("=" * 68)
    print(f"Modelo:                 {model}")
    print(f"Problemas:              {dataset_size}")
    print("Condiciones:            2 (baseline + verified)")
    print(f"Generaciones previstas: {calls}")
    print(f"Temperatura:            {temperature}")
    print(f"Máximo de tokens:       {max_tokens}")
    print(f"Timeout por solicitud:  {'sin límite' if timeout is None else format_duration(timeout)}")
    if historical_seconds is not None:
        print(f"Estimación histórica:   {format_duration(historical_seconds)}")
    else:
        print("Estimación inicial:     se calculará dinámicamente con las primeras tareas")
    if theoretical is not None:
        print(f"Límite teórico:         {format_duration(theoretical)}")
    else:
        print("Límite teórico:         sin límite de cliente")
    print("El tiempo real depende del modelo, hardware y respuesta.")
    print("=" * 68)


def save_state(path: Path, *, experiment: str, model: str, baseline: list[dict[str, Any]], verified: list[dict[str, Any]], protocol: dict[str, Any]) -> None:
    result = {
        "experiment": experiment,
        "model": model,
        "status": "in_progress",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "conditions": {
            "baseline": {"summary": summarize(baseline), "results": baseline},
            "verified": {"summary": summarize(verified), "results": verified},
        },
        "protocol": protocol,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def run_condition(
    dataset: list[dict[str, Any]],
    *,
    condition: str,
    endpoint: str,
    model: str,
    temperature: float,
    max_tokens: int,
    repair: bool,
    timeout: float | None,
    existing: dict[str, dict[str, Any]],
    all_rows: dict[str, list[dict[str, Any]]],
    output: Path,
) -> list[dict[str, Any]]:
    rows = [existing[item["id"]] for item in dataset if item["id"] in existing]
    # Failed requests remain in the audit record but can be retried on resume.
    completed = {
        item_id for item_id, row in existing.items() if not row.get("error")
    }
    for item in dataset:
        if item["id"] in completed:
            continue

        total_calls = len(dataset) * 2
        done_before = len(all_rows["baseline"]) + len(all_rows["verified"])
        remaining_before = total_calls - done_before
        eta, eta_text = estimate_from_rows(all_rows[condition], remaining_before)
        print(f"\n[{done_before + 1}/{total_calls}] {condition} — {item['id']}")
        print(f"  Estimación restante (dinámica): {eta_text}")

        started_wall = time.perf_counter()
        try:
            response, latency, runtime = ask(
                item,
                endpoint=endpoint,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            first_verification = verify(item, response) if condition == "verified" else None
            repaired = False

            if condition == "verified" and repair and not first_verification["ok"]:
                response, repair_latency, repair_runtime = ask(
                    item,
                    endpoint=endpoint,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    feedback=first_verification["details"],
                )
                runtime["repair"] = repair_runtime
                latency += repair_latency
                repaired = True

            final_verification = verify(item, response) if condition == "verified" else None
            expected = item["answer"]
            row = {
                "id": item["id"],
                "category": item["category"],
                "condition": condition,
                "response": response,
                "expected": expected,
                "contains_expected": expected in response,
                "exact_match": response == expected,
                "verification_success": bool(final_verification and final_verification["ok"]),
                "first_verification_success": bool(first_verification and first_verification["ok"]),
                "repair_attempted": repaired,
                "verification": final_verification,
                "latency_ms": latency,
                "runtime": runtime,
                "error": None,
            }
        except Exception as exc:
            row = {
                "id": item["id"],
                "category": item["category"],
                "condition": condition,
                "response": None,
                "expected": item["answer"],
                "contains_expected": False,
                "exact_match": False,
                "verification_success": False,
                "first_verification_success": False,
                "repair_attempted": False,
                "verification": None,
                "latency_ms": round((time.perf_counter() - started_wall) * 1000, 3),
                "runtime": {},
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
            print(f"  ERROR: {row['error']['type']}: {row['error']['message']}")

        rows.append(row)
        all_rows[condition].append(row)

        done = len(all_rows["baseline"]) + len(all_rows["verified"])
        remaining = total_calls - done
        eta, eta_text = estimate_from_rows(all_rows[condition], remaining)
        print(f"  Tiempo: {format_duration(row['latency_ms'] / 1000)}")
        print(f"  Progreso: {done}/{total_calls} | Estimación restante: {eta_text}")

        save_state(
            output,
            experiment="exp-0001",
            model=model,
            baseline=all_rows["baseline"],
            verified=all_rows["verified"],
            protocol={
                "temperature": temperature,
                "max_tokens": max_tokens,
                "repair_enabled": repair,
                "timeout_seconds": timeout,
                "resumable": True,
            },
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="experiments/exp-0001-math-verification/dataset.jsonl")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--timeout", type=float, default=120, help="Seconds; 0 disables the client-side timeout.")
    parser.add_argument("--output", default="experiments/exp-0001-math-verification/results/run.json")
    parser.add_argument("--new-run", action="store_true", help="Create a timestamped run instead of resuming the default output.")
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))
    timeout = None if args.timeout <= 0 else args.timeout
    output = Path(args.output)
    if args.new_run and args.output == "experiments/exp-0001-math-verification/results/run.json":
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = output.with_name(f"run-{stamp}.json")

    baseline: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []
    existing = {}
    historical_seconds = None

    if output.exists() and not args.new_run:
        try:
            previous = json.loads(output.read_text(encoding="utf-8"))
            if previous.get("model") == args.model:
                baseline = previous.get("conditions", {}).get("baseline", {}).get("results", [])
                verified = previous.get("conditions", {}).get("verified", {}).get("results", [])
                existing = {
                    (r.get("condition"), r.get("id")): r
                    for r in baseline + verified
                }
                latencies = [
                    r.get("latency_ms", 0) / 1000
                    for r in baseline + verified
                    if isinstance(r.get("latency_ms"), (int, float))
                ]
                if latencies:
                    historical_seconds = sum(latencies) / len(latencies) * max(0, len(dataset) * 2 - len(baseline) - len(verified))
        except (OSError, json.JSONDecodeError):
            pass

    # Normalize saved rows into per-condition maps for resumable execution.
    baseline_map = {r["id"]: r for r in baseline}
    verified_map = {r["id"]: r for r in verified}
    all_rows = {"baseline": baseline.copy(), "verified": verified.copy()}

    print_header(
        model=args.model,
        dataset_size=len(dataset),
        timeout=timeout,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        historical_seconds=historical_seconds,
    )

    run_condition(
        dataset,
        condition="baseline",
        endpoint=args.endpoint,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        repair=False,
        timeout=timeout,
        existing=baseline_map,
        all_rows=all_rows,
        output=output,
    )
    run_condition(
        dataset,
        condition="verified",
        endpoint=args.endpoint,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        repair=args.repair,
        timeout=timeout,
        existing=verified_map,
        all_rows=all_rows,
        output=output,
    )

    result = {
        "experiment": "exp-0001",
        "model": args.model,
        "status": "completed",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "conditions": {
            "baseline": {"summary": summarize(all_rows["baseline"]), "results": all_rows["baseline"]},
            "verified": {"summary": summarize(all_rows["verified"]), "results": all_rows["verified"]},
        },
        "protocol": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "repair_enabled": args.repair,
            "timeout_seconds": timeout,
            "resumable": True,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + "=" * 68)
    print("EXPERIMENTO FINALIZADO")
    print(json.dumps({
        "output": str(output),
        "baseline": result["conditions"]["baseline"]["summary"],
        "verified": result["conditions"]["verified"]["summary"],
    }, ensure_ascii=False, indent=2))
    print("=" * 68)


if __name__ == "__main__":
    main()
