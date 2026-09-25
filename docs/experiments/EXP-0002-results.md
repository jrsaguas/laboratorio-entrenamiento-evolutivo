# EXP-0002 — Resultados formales y reevaluación

**Fecha de cierre de la fase experimental:** 25 de septiembre de 2026  
**Protocolo:** 0.2  
**Dataset:** 0.1  
**Experimento:** 0.2  
**Commit de las corridas formales:** `abfb96698f07efeefbe461cb38b13ef7d2721cd4`

## 1. Alcance

EXP-0002 mide el comportamiento de cuatro modelos locales bajo el mismo dataset de 20 tareas de EXP-0001, el mismo prompt, temperatura 0, máximo de tokens -1, verificación determinista y sin reparación. La unidad experimental es tarea × modelo.

La métrica `semantic_correct`/`verification_success` debe interpretarse como **aceptación por el verificador determinista vigente**, no como una prueba independiente de verdad matemática.

Los modelos de la corrida formal fueron:

- `qwen2-math:7b`
- `llama3.2:3b`
- `qwen3:4b-thinking-2507-q4_K_M`
- `phi4-mini:latest`

`qwen3:8b` y `gemma4:12b` no forman parte de la corrida formal debido a la restricción operacional de memoria documentada en el README. Sus smoke tests no se mezclan con estas métricas.

## 2. Resultados por modelo

| Modelo | Tareas | Aceptadas por verificador | Tasa | Exact match | Contains expected | Tokens | Latencia generación | Latencia total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `qwen2-math:7b` | 20 | 13 | 65% | 0/20 (0%) | 11/20 (55%) | 196 | 654472.967 ms | 868811.495 ms |
| `llama3.2:3b` | 20 | 13 | 65% | 0/20 (0%) | 6/20 (30%) | 282 | 65041.547 ms | 67687.063 ms |
| `qwen3:4b-thinking-2507-q4_K_M` | 20 | 15 | 75% | 10/20 (50%) | 11/20 (55%) | 10340 | 1318387.331 ms | 1357202.409 ms |
| `phi4-mini:latest` | 20 | 17 | 85% | 2/20 (10%) | 10/20 (50%) | 185 | 61057.172 ms | 61694.681 ms |

Las cuatro corridas completaron las 20 tareas sin errores de ejecución. La comparación se presenta por dimensiones y no como una clasificación global.

## 3. Reevaluación determinista

Cada artefacto original fue reevaluado sin regenerar respuestas y sin modificar el JSON fuente. La reevaluación utilizó el verificador asociado al commit `abfb96698f07efeefbe461cb38b13ef7d2721cd4`.

| Modelo | Aceptación original | Aceptación reevaluada | Cambios de veredicto | Estados observados |
|---|---:|---:|---:|---|
| `qwen2-math:7b` | 13/20 | 13/20 | 0 | verified 13; verified_difference 4; parser_or_verification_error 2; unsupported_format 1 |
| `llama3.2:3b` | 13/20 | 13/20 | 0 | verified 13; verified_difference 6; reference_mismatch 1 |
| `qwen3:4b-thinking-2507-q4_K_M` | 15/20 | 15/20 | 0 | verified 15; parser_or_verification_error 2; reference_mismatch 1; verified_difference 2 |
| `phi4-mini:latest` | 17/20 | 17/20 | 0 | verified 17; verified_difference 3 |

La ausencia de cambios de veredicto en las cuatro corridas indica que, para estos artefactos y este commit del verificador, la reevaluación reproduce las decisiones registradas durante la generación.

## 4. Coste de generación observado

El coste de generación varió ampliamente entre modelos. `phi4-mini:latest` produjo 185 tokens agregados en 61.06 s de generación; `llama3.2:3b` produjo 282 tokens en 65.04 s; `qwen2-math:7b` produjo 196 tokens en 654.47 s; y `qwen3:4b-thinking-2507-q4_K_M` produjo 10,340 tokens en 1,318.39 s.

Estas diferencias no deben interpretarse aisladamente como eficiencia intrínseca del modelo: las mediciones están condicionadas por el hardware local, el runtime de Ollama, el estado de carga y la composición de las 20 tareas.

## 5. Observaciones metodológicas

- Las cuatro corridas formales utilizaron el mismo dataset y contrato de medición.
- No hubo reparación, por lo que los resultados describen la generación inicial.
- La reevaluación no regeneró respuestas y no produjo cambios de veredicto.
- La ausencia de `verifier_false_rejection` en las corridas formales es consistente con el contrato de medición, pero no demuestra que el verificador sea universalmente libre de falsos rechazos.
- `exact_match` y `contains_expected` no son sustitutos de la verificación semántica.
- Los resultados no establecen por sí mismos una conclusión general sobre las capacidades matemáticas de los modelos fuera de este dataset y este entorno.

## 6. Artefactos

Corridas originales:

- `results/run-20260925T073809Z.json`
- `results/run-20260925T192845Z.json`
- `results/run-20260925T193123Z.json`
- `results/run-20260925T210526Z.json`

Reevaluaciones:

- `results/reevaluated/run-20260925T073809Z--verifier-abfb96698f07.json`
- `results/reevaluated/run-20260925T192845Z--verifier-abfb96698f07.json`
- `results/reevaluated/run-20260925T193123Z--verifier-abfb96698f07.json`
- `results/reevaluated/run-20260925T210526Z--verifier-abfb96698f07.json`

## 7. Criterio de cierre de esta fase

EXP-0002 queda experimentalmente cerrado cuando:

1. las cuatro corridas formales existen y tienen 20 tareas válidas;
2. cada artefacto conserva el protocolo 0.2 y el commit experimental correspondiente;
3. los cuatro artefactos fueron reevaluados con el verificador determinista;
4. la reevaluación no cambió los veredictos de estas corridas;
5. los resultados y limitaciones quedan documentados sin convertir las métricas en una clasificación global.

Con las ejecuciones registradas el 25 de septiembre de 2026 y la reevaluación completada con salida de código 0, estos cinco criterios quedan satisfechos.
