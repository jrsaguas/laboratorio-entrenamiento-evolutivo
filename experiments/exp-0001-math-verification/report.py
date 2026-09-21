"""Generate a comparison report from an EXP-0001 run.json artifact."""

from __future__ import annotations
import argparse, json
from pathlib import Path
from statistics import mean
from typing import Any

def rate(rows: list[dict[str, Any]], key: str) -> float:
    return sum(bool(r.get(key)) for r in rows) / len(rows) if rows else 0.0

def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lat = [r["latency_ms"] for r in rows if isinstance(r.get("latency_ms"), (int, float))]
    return {"n": len(rows), "exact_accuracy": rate(rows,"exact_match"), "contains_expected": rate(rows,"contains_expected"), "verification_success": rate(rows,"verification_success"), "first_verification_success": rate(rows,"first_verification_success"), "repair_attempt_rate": rate(rows,"repair_attempted"), "mean_latency_ms": round(mean(lat),3) if lat else None, "errors": sum(bool(r.get("error")) for r in rows)}

def by_category(rows):
    groups = {}
    for row in rows: groups.setdefault(row.get("category","unknown"), []).append(row)
    return {k:summarize(v) for k,v in sorted(groups.items())}

def pct(x): return f"{x*100:.1f}%"

def build_markdown(data):
    b, v = data["conditions"]["baseline"], data["conditions"]["verified"]
    bs, vs = b["summary"], v["summary"]
    lines = ["# EXP-0001 — Reporte automático", "", f"**Modelo:** `{data.get("model","unknown")}`", f"**Temperatura:** `{data.get("protocol",{}).get("temperature")}`", "", "## Comparación global", "", "| Métrica | Baseline | Verified | Delta |", "|---|---:|---:|---:|"]
    for label,key in [("Exactitud exacta","exact_accuracy"),("Contiene respuesta","contains_expected"),("Verificación exitosa","verification_success")]:
        delta=vs[key]-bs[key]; lines.append(f"| {label} | {pct(bs[key])} | {pct(vs[key])} | {pct(delta)} |")
    lines += [f"| Latencia media | {bs["mean_latency_ms"]} ms | {vs["mean_latency_ms"]} ms | — |", "", "## Desglose por categoría", ""]
    for name, title in [("baseline","Baseline"),("verified","Verified")]:
        lines += [f"### {title}", "", "| Categoría | n | Exactitud | Verificación | Latencia |", "|---|---:|---:|---:|---:|"]
        for cat,s in by_category(data["conditions"][name]["results"]).items(): lines.append(f"| {cat} | {s["n"]} | {pct(s["exact_accuracy"])} | {pct(s["verification_success"])} | {s["mean_latency_ms"]} ms |")
        lines.append("")
    lines += ["## Interpretación", "", "- El reporte describe diferencias observadas; no declara un ganador.", "- Una verificación fallida puede corresponder a un error matemático o a un formato de expresión no aceptado.", "- El dataset de 20 problemas es piloto y no representa una evaluación general del modelo.", "- Se requieren repeticiones y análisis de errores antes de usar estos resultados para entrenamiento.", "", f"- Delta de exactitud: **{pct(vs["exact_accuracy"]-bs["exact_accuracy"])}**.", f"- Delta de verificación: **{pct(vs["verification_success"]-bs["verification_success"])}**."]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser(); p.add_argument("input", nargs="?", default="experiments/exp-0001-math-verification/results/run.json"); p.add_argument("--output", default="experiments/exp-0001-math-verification/results/report.md"); a=p.parse_args()
    data=json.loads(Path(a.input).read_text(encoding="utf-8")); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(build_markdown(data),encoding="utf-8"); print(out)

if __name__ == "__main__": main()