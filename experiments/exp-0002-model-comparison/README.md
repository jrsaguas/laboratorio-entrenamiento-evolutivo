# EXP-0002 — Comparación controlada de modelos

## Propósito

Comparar modelos de lenguaje bajo un protocolo común para medir su comportamiento en las mismas tareas matemáticas de EXP-0001.

EXP-0001 queda congelado como referencia metodológica. EXP-0002 no modifica su dataset ni su runner.

## Pregunta experimental

¿Cómo cambia la corrección matemática, el formato de respuesta y el coste de generación cuando se sustituye únicamente el modelo?

## Diseño

- Unidad de comparación: tarea × modelo.
- Dataset: `experiments/exp-0001-math-verification/dataset.jsonl`, versión 0.1.
- Mismo prompt de generación para todos los modelos.
- Temperatura, límite de tokens, seed y timeout comunes.
- Verificación semántica determinista mediante `tools/math_verifier.py`.
- Una generación inicial por modelo y tarea.
- Sin reparación: la reparación pertenece a EXP-0001.
- Se conservan latencia de generación y datos de runtime.
- La carga inicial del modelo no se oculta: se registra para distinguir cold start de inferencia posterior.

## No es una clasificación

El experimento produce mediciones por modelo. No incorpora una puntuación agregada ni una decisión automática de "mejor modelo". Las conclusiones deben considerar tamaño del modelo, hardware, warm/cold state y composición del dataset.

## Ejecución

`python experiments/exp-0002-model-comparison/runner.py --models "qwen2-math:7b,llama3.2:3b"`

Prueba corta:

`python experiments/exp-0002-model-comparison/runner.py --models "qwen2-math:7b,llama3.2:3b" --limit 3`

La corrida completa utiliza los 20 problemas de EXP-0001.

## Artefactos

El protocolo de artefactos actual es la versión 0.2.

Cada ejecución crea por defecto un artefacto JSON independiente identificado por su `run_id`:

`experiments/exp-0002-model-comparison/results/run-<timestamp>.json`

Esto evita que una ejecución posterior sobrescriba los resultados de un modelo anterior. El parámetro `--output` permite seleccionar explícitamente otra ruta cuando sea necesario.
