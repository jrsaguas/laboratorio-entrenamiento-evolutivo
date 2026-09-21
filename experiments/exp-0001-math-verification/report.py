from __future__ import annotations
import argparse, json
from pathlib import Path
from statistics import mean

def rate(rows, key): return sum(bool(r.get(key)) for r in rows) / len(rows) if rows else 0.0
def summarize(rows):
    lat=[r['latency_ms'] for r in rows if isinstance(r.get('latency_ms'),(int,float))]
    return {'n':len(rows),'exact_accuracy':rate(rows,'exact_match'),'contains_expected':rate(rows,'contains_expected'),'verification_success':rate(rows,'verification_success'),'mean_latency_ms':round(mean(lat),3) if lat else None,'errors':sum(bool(r.get('error')) for r in rows)}
def by_category(rows):
    g={}
    for r in rows: g.setdefault(r.get('category','unknown'),[]).append(r)
    return {k:summarize(v) for k,v in sorted(g.items())}
def pct(x): return f'{x*100:.1f}%'
def build(data):
    b=data['conditions']['baseline']; v=data['conditions']['verified']; bs=b['summary']; vs=v['summary']
    lines=['# EXP-0001 — Reporte automático','',f"**Modelo:** `{data.get('model','unknown')}`",'', '## Comparación global','', '| Métrica | Baseline | Verified | Delta |','|---|---:|---:|---:|']
    for label,key in [('Exactitud exacta','exact_accuracy'),('Contiene respuesta','contains_expected'),('Verificación exitosa','verification_success')]: lines.append(f'| {label} | {pct(bs[key])} | {pct(vs[key])} | {pct(vs[key]-bs[key])} |')
    lines.append(f"| Latencia media | {bs['mean_latency_ms']} ms | {vs['mean_latency_ms']} ms | — |")
    lines += ['', '## Desglose por categoría','']
    for name,title in [('baseline','Baseline'),('verified','Verified')]:
        lines += [f'### {title}','','| Categoría | n | Exactitud | Verificación | Latencia |','|---|---:|---:|---:|---:|']
        for cat,s in by_category(data['conditions'][name]['results']).items(): lines.append(f"| {cat} | {s['n']} | {pct(s['exact_accuracy'])} | {pct(s['verification_success'])} | {s['mean_latency_ms']} ms |")
    lines += ['', '## Interpretación','', '- El reporte describe diferencias observadas; no declara un ganador.','- Una verificación fallida puede corresponder a un error matemático o a un formato no aceptado.','- El dataset piloto no representa una evaluación general del modelo.','- Se requieren repeticiones y análisis de errores antes de usar estos resultados para entrenamiento.']
    return '\n'.join(lines)
def main():
    p=argparse.ArgumentParser(); p.add_argument('input',nargs='?',default='experiments/exp-0001-math-verification/results/run.json'); p.add_argument('--output',default='experiments/exp-0001-math-verification/results/report.md'); a=p.parse_args()
    data=json.loads(Path(a.input).read_text(encoding='utf-8')); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(build(data),encoding='utf-8'); print(out)
if __name__ == '__main__': main()