"""Run EXP-0001 against a model endpoint.

The runner intentionally keeps the baseline and verified conditions explicit.
It does not modify model weights and it does not perform automatic promotion.
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
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(dataset: list[dict[str, Any]], endpoint: str, model: str, temperature: float, max_tokens: int) -> dict[str, Any]:
    rows = []
    for item in dataset:
        prompt = item["prompt"]
        started = time.perf_counter()
        try:
            response = generate(
                prompt,
                endpoint=endpoint,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
            text = response.text

            # The first version records deterministic verification only for
            # expressions with a known reference. Future versions will parse
            # equations/derivatives more formally.
            verification = None
            if item.get("verification") == "sympy" and item.get("answer"):
                verification = verify_symbolic_equality(text, item["answer"])

            rows.append({
                "id": item["id"],
                "category": item["category"],
                "response": text,
                "expected": item["answer"],
                "contains_expected": item["answer"] in text,
                "exact_match": text.strip() == item["answer"].strip(),
                "verification_success": bool(verification and verification.ok),
                "verification_method": verification.method if verification else None,
                "latency_ms": elapsed_ms,
                "error": None,
            })
        except Exception as exc:
            rows.append({
                "id": item["id"],
                "category": item["category"],
                "response": None,
                "expected": item["answer"],
                "contains_expected": False,
                "exact_match": False,
                "verification_success": False,
                "verification_method": None,
                "latency_ms": None,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            })

    return {"summary": summarize(rows), "results": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/v1/chat/completions")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="experiments/exp-0001-math-verification/dataset.jsonl")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--output", default="experiments/exp-0001-math-verification/results/run.json")
    args = parser.parse_args()

    dataset = load_dataset(Path(args.dataset))
    result = run(dataset, args.endpoint, args.model, args.temperature, args.max_tokens)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
