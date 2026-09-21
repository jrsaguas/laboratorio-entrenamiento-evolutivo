# Laboratorio de Entrenamiento Evolutivo

Laboratorio experimental para investigar cómo mejorar modelos de lenguaje relativamente pequeños mediante entrenamiento, post-entrenamiento, agentes, herramientas, recuperación, evaluación y ciclos controlados de experimentación.

> **Separación arquitectónica:** este repositorio es independiente de `praxis_suite`. Praxis podrá aportar componentes reutilizables después de una auditoría, pero no define esta arquitectura.

## Objetivo

Construir un entorno reproducible capaz de estudiar y modificar modelos abiertos, generar y curar datos, entrenar variantes, construir agentes y herramientas verificables, evaluar resultados y registrar ciclos de mejora.

## Principios

- Separar evolución **paramétrica** (pesos, adaptadores, arquitectura, receta de entrenamiento) de evolución **sistémica** (agentes, herramientas, RAG, memoria, prompts, evaluadores y workflows).
- No aceptar una mejora por una demostración aislada: debe medirse contra una referencia.
- Mantener experimentos reproducibles, versionados y auditables.
- Priorizar calidad por unidad de cómputo.
- Aislar cualquier componente generado automáticamente antes de integrarlo.

## Diseño técnico

La especificación viva está en [docs/diseno-tecnico/](docs/diseno-tecnico/), con índice maestro en [docs/diseno-tecnico/00-indice.md](docs/diseno-tecnico/00-indice.md).

Los documentos evolucionan en su misma ubicación; Git conserva el historial en lugar de crear copias v1/v2.

## Estado inicial

**Fase:** diseño técnico v0.1  
**Estado:** fundación del laboratorio  
**Prioridad:** arquitectura, hipótesis, métricas y protocolo experimental antes del entrenamiento real.

## Licenciamiento

La política de licencias se documentará antes de redistribuir modelos, pesos, datos o derivados.
