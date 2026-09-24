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

## Contrato de medición congelado

A partir del protocolo 0.2, las corridas formales de EXP-0002 conservan por tarea y modelo estas métricas y campos, sin redefinirlos entre modelos:

| Campo | Significado |
|---|---|
| `exact_match` | La respuesta coincide literalmente con `answer`, tras `strip()`. |
| `contains_expected` | La cadena de `answer` aparece literalmente en la respuesta. |
| `verifier_accepts` | El verificador determinista actual acepta la respuesta. En los artefactos de generación este valor se registra como `verification_success`. |
| `verification_status` | Estado estructurado producido por el verificador, por ejemplo `verified`, `verified_difference`, `unsupported_format` o `parser_or_verification_error`. |
| `verification_method` | Método concreto utilizado por el verificador. |
| `verification_details` | Detalle diagnóstico del resultado del verificador. |

### Interpretación

`semantic_correct`, `verification_success` y `verifier_accepts` representan **aceptación por el verificador determinista**, no una prueba independiente de verdad matemática.

La reevaluación de artefactos históricos se mantiene separada de la generación original. No modifica el JSON fuente y registra el commit del verificador utilizado. Por ello pueden existir diferencias entre `verification_success` original y `verifier_accepts` reevaluado sin que haya cambiado la respuesta del modelo.

Los artefactos de generación conservan además `generation_latency_ms`, `verification_latency_ms`, `latency_ms`, `observed_latency_ms` y los datos de runtime disponibles de Ollama. La latencia de carga se conserva para distinguir el coste de cold start del resto del runtime.

**Regla de comparación:** no se utilizará una única cifra agregada como "precisión matemática" ni se establecerá un modelo ganador automáticamente. Los resultados se interpretarán conjuntamente con los estados del verificador, el coste de generación, el hardware y la composición del dataset.

Una corrida formal no debe ejecutarse con una definición diferente de estos campos. Si el contrato necesita cambiar, debe incrementarse la versión del protocolo y documentarse el cambio antes de generar nuevos resultados.

