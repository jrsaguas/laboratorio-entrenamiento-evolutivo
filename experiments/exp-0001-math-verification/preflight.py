"""Preflight checks for EXP-0001 local execution."""

from __future__ import annotations

import argparse
import json
import urllib.request


def get_json(url: str, timeout: int) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/tags")
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

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
