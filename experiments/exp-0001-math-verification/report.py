"""Generate a Markdown report from an EXP-0001 run JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def pct(value: float | None) -> str:
    return "n/d" if value is None else f"{value * 100:.1f}%"


def condition_summary(summary: dict[str, Any]) -> list[str]:
    return [
        f"- Total: {summary.get('total')}",
        f"- Exactitud textual: {pct(summary.get('exact_accuracy'))}",
        f"- Exactitud semántica: {pct(summary.get('semantic_accuracy'))}",
        f"- Verificación inicial: {pct(summary.get('initial_verification_success_rate'))}",
        f"- Verificación final: {pct(summary.get('verification_success_rate'))}",
        f"- Errores detectados: {summary.get('detected_errors')}",
        f"- Falsos rechazos: {summary.get('verifier_false_rejection')}",
        f"- Reparaciones: {summary.get('repair_attempts')}",
        f"- Reparaciones exitosas: {summary.get('repair_successes')}",
        f"- Tokens: {summary.get('tokens')}",
        f"- Latencia media de generación: {summary.get('average_generation_latency_ms')} ms",
        f"- Latencia media de intervención/verificación: {summary.get('average_verification_latency_ms')} ms",
        f"- Latencia media de reparación: {summary.get('average_repair_latency_ms')} ms",
        f"- Latencia media del oráculo diagnóstico: {summary.get('average_oracle_latency_ms')} ms",
        f"- Latencia media de la condición: {summary.get('average_latency_ms')} ms",
        f"- Latencia media observada con diagnóstico: {summary.get('average_observed_latency_ms')} ms",
    ]


def build(data: dict[str, Any]) -> str:
    lines = [
        "# EXP-0001 — Reporte automático",
        "",
        f"Modelo: {data.get('model', 'unknown')}",
        "",
        "## Protocolo",
        "",
    ]
    protocol = data.get("protocol", {})
    for key in (
        "temperature", "max_tokens", "max_tokens_mode", "seed",
        "timeout_seconds", "timeout_mode",
        "paired_initial_generation", "repair_is_separate_condition",
    ):
        if key in protocol:
            lines.append(f"- {key}: {protocol[key]}")

    lines.extend(["", "## Condiciones", ""])
    for name, condition in data.get("conditions", {}).items():
        lines.extend([f"### {name}", ""])
        lines.extend(condition_summary(condition.get("summary", {})))
        lines.append("")

    lines.extend([
        "## Comparación de exactitud semántica",
        "",
        "| Condición | Exactitud semántica | Latencia de condición | Generación | Verificación | Reparación | Tokens |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for name, condition in data.get("conditions", {}).items():
        summary = condition.get("summary", {})
        lines.append(
            f"| {name} | {pct(summary.get('semantic_accuracy'))} | "
            f"{summary.get('average_latency_ms')} ms | {summary.get('average_tokens')} |"
        )

    lines.extend([
        "",
        "## Interpretación metodológica",
        "",
        "- baseline representa la generación inicial sin intervención.",
        "- verified reutiliza exactamente la misma respuesta inicial del baseline y añade verificación.",
        "- verified_repair parte de esa misma respuesta inicial y solo genera una segunda respuesta cuando la verificación inicial falla.",
        "- La exactitud semántica se obtiene mediante el oráculo determinista declarado por cada tarea.",
        "- La latencia de la condición representa generación + verificación/reparación que forma parte de la intervención.",
        "- La latencia del oráculo diagnóstico se registra por separado y no se carga a baseline ni a la intervención.",
        "- La latencia observada con diagnóstico suma también el coste del oráculo usado para medir la corrección semántica.",
        "- Un fallo de verificación no se atribuye automáticamente al modelo: puede corresponder a formato no soportado o error del propio proceso de verificación.",
        "- El dataset actual es piloto y no permite generalizar resultados.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="experiments/exp-0001-math-verification/results/run.json")
    parser.add_argument("--output", default="experiments/exp-0001-math-verification/results/report.md")
    args = parser.parse_args()
    input_path = Path(args.input)
    if not input_path.exists() and str(input_path).endswith("results/run.json"):
        candidates = sorted(input_path.parent.glob("run-*.json"))
        if candidates:
            input_path = candidates[-1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build(data), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
