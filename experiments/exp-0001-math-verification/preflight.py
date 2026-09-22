"""Preflight checks for EXP-0001 local execution."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
import sys


def get_json(url: str, timeout: int) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_verifier() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from tools.math_verifier import verify_answer

    checks = [
        ("Respuesta: 5", "5", None),
        ("[2, 3]", None, {"type": "list", "expected": [2, 3]}),
        (
            "[6, 4]",
            None,
            {
                "type": "system",
                "variables": ["x", "y"],
                "expected": [6, 4],
                "equations": ["x+y-10", "x-y-2"],
                "ordered": True,
            },
        ),
        ("3*x**2 + 2", "2 + 3*x**2", None),
    ]

    failures = []
    for candidate, reference, spec in checks:
        result = verify_answer(candidate, reference, spec)
        if not result.ok:
            failures.append({
                "candidate": candidate,
                "reference": reference,
                "spec": spec,
                "details": result.details,
                "metadata": result.metadata,
            })

    if failures:
        raise SystemExit(
            "VERIFIER_FAILED: las comprobaciones semánticas no pasaron.\n"
            + json.dumps(failures, ensure_ascii=False, indent=2)
        )

    print("Verifier: OK (4 comprobaciones semánticas)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/tags")
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    check_verifier()

    try:
        data = get_json(args.endpoint, args.timeout)
    except Exception as exc:
        raise SystemExit(
            "OLLAMA_UNREACHABLE: no se pudo conectar con "
            f"{args.endpoint}. Detalle: {type(exc).__name__}: {exc}"
        )

    models = [m.get("name") for m in data.get("models", [])]
    if args.model not in models:
        raise SystemExit(
            "MODEL_NOT_FOUND: el modelo solicitado no aparece en Ollama. "
            f"Solicitado={args.model}; disponibles={models}"
        )

    print(json.dumps({
        "status": "ok",
        "endpoint": args.endpoint,
        "model": args.model,
        "available_models": models,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
