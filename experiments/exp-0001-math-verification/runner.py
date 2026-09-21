"""Run EXP-0001 in baseline and verified conditions.

The verified condition uses a deterministic SymPy check and, when requested,
one repair attempt with explicit verifier feedback. The runner records both
conditions so the effect of verification can be measured rather than assumed.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from evaluation.metrics.metrics import summarize
from tools.model_runtime import generate
from tools.math_verifier import verify_symbolic_equality


def load_dataset(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def ask(item: dict[str, Any], *, endpoint: str, model: str, temperature: float, max_tokens: int, feedback: str | None = None) -> tuple[str, float]:
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
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    return response.text.strip(), elapsed_ms


def verify(item: dict[str, Any], candidate: str) -> dict[str, Any]:
    reference = item.get("verification_reference")
    if not reference:
        return {"ok": False, "method": None, "details": "no verification reference"}

    result = verify_symbolic_equality(candidate, reference)
    return {
        "ok": result.ok,
        "method": result.method,
        "details": result.details,
        "metadata": result.metadata,
    }


def run_condition(
    dataset: list[dict[str, Any]],
    *,
    condition: str,
    endpoint: str,
    model: str,
    temperature: float,
    max_tokens: int,
    repair: bool,
) -> list[dict[str, Any]]:
    rows = []

    for item in dataset:
        try:
            response, latency = ask(
                item,
                endpoint=endpoint,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            first_verification = verify(item, response) if condition == "verified" else None
            repaired = False

            if condition == "verified" and repair and not first_verification["ok"]:
                feedback = first_verification["details"]
                response, repair_latency = ask(
                    item,
                    endpoint=endpoint,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    feedback=feedback,
                )
                latency += repair_latency
                repaired = True

            final_verification = verify(item, response) if condition == "verified" else None
            expected = item["answer"]

            rows.append({
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
                "error": None,
            })
        except Exception as exc:
            rows.append({
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
                "latency_ms": None,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            })

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="experiments/exp-0001-math-verification/dataset.jsonl")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", default="experiments/exp-0001-math-verification/results/run.json")
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))

    baseline = run_condition(
        dataset,
        condition="baseline",
        endpoint=args.endpoint,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        repair=False,
    )
    verified = run_condition(
        dataset,
        condition="verified",
        endpoint=args.endpoint,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        repair=args.repair,
    )

    result = {
        "experiment": "exp-0001",
        "model": args.model,
        "conditions": {
            "baseline": {
                "summary": summarize(baseline),
                "results": baseline,
            },
            "verified": {
                "summary": summarize(verified),
                "results": verified,
            },
        },
        "protocol": {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "repair_enabled": args.repair,
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "baseline": result["conditions"]["baseline"]["summary"],
        "verified": result["conditions"]["verified"]["summary"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
