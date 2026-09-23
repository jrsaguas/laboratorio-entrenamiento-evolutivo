"""Generate a compact Markdown report from an EXP-0001 run JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def render(data: dict[str, Any]) -> str:
    lines = [
        "# EXP-0001 — Reporte de resultados",
        "",
        "- Estado: **" + str(data.get("status", "unknown")) + "**",
        "- Modelo: **" + str(data.get("model", "unknown")) + "**",
        "",
        "## Protocolo",
        "",
    ]
    protocol = data.get("protocol", {})
    for key in ("temperature", "max_tokens", "max_tokens_mode", "seed",
                "timeout_seconds", "timeout_mode", "repair_is_separate_condition"):
        if key in protocol:
            lines.append("- " + key + ": " + str(protocol[key]))

    lines.extend(["", "## Condiciones", ""])
    for name, condition in data.get("conditions", {}).items():
        summary = condition.get("summary", {})
        lines.extend([
            "### " + name,
            "",
            "- Total: " + str(summary.get("total")),
            "- Exactitud: " + str(summary.get("exact_accuracy")),
            "- Verificación inicial: " + str(summary.get("initial_verification_success_rate")),
            "- Verificación final: " + str(summary.get("verification_success_rate")),
            "- Errores detectados: " + str(summary.get("detected_errors")),
            "- Reparaciones: " + str(summary.get("repair_attempts")),
            "- Reparaciones exitosas: " + str(summary.get("repair_successes")),
            "- Tokens: " + str(summary.get("tokens")),
            "- Latencia total (ms): " + str(summary.get("latency_ms")),
            "",
        ])

    lines.extend([
        "## Nota metodológica",
        "",
        "verified mide la generación seguida de verificación determinista.",
        "verified_repair añade una segunda generación después de un fallo de verificación, "
        "por lo que su coste de inferencia debe analizarse por separado.",
        "La exactitud de cadena y la verificación semántica no son métricas equivalentes.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    parser.add_argument("--output")
    args = parser.parse_args()
    path = Path(args.run)
    data = json.loads(path.read_text(encoding="utf-8"))
    output = Path(args.output) if args.output else path.with_suffix(".md")
    output.write_text(render(data), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
