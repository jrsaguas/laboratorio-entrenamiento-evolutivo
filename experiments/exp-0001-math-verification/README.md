# EXP-0001 — Verificación matemática determinista

**Estado:** piloto instrumentado; pendiente de smoke test.

## Objetivo

Medir por separado:

1. la exactitud matemática de una generación inicial;
2. la capacidad de un verificador determinista para diagnosticar esa respuesta;
3. el efecto de una reparación basada en la retroalimentación del verificador;
4. el coste adicional en tokens y latencia.

## Diseño experimental

Las condiciones están emparejadas por tarea.

**Baseline**

~~~text
problema → generación inicial → resultado
~~~

**Verified**

~~~text
problema → misma generación inicial del baseline → verificación
~~~

**Verified repair**

~~~text
problema → misma generación inicial → verificación
                              ↓ fallo
                         segunda generación
                              ↓
                         verificación final
~~~

La respuesta inicial no se genera dos veces. **Verified** reutiliza la respuesta producida por **baseline**, de modo que la comparación de verificación se realiza sobre exactamente el mismo candidato.

**Verified repair** añade una generación únicamente cuando la verificación inicial falla.

## Métricas

Se distinguen tres conceptos:

- **Exactitud textual:** la respuesta coincide literalmente con el campo answer del dataset.
- **Exactitud semántica:** la respuesta final pasa el oráculo determinista declarado por la tarea.
- **Verificación:** el proceso de intervención acepta o rechaza la respuesta.

La exactitud semántica es la métrica principal de corrección matemática. La coincidencia textual se conserva como diagnóstico.

Un falso rechazo se define sobre el resultado semánticamente correcto: el oráculo considera correcta la respuesta, pero la verificación inicial la rechaza.

## Ejecución

Desde la raíz del repositorio:

~~~powershell
python experiments/exp-0001-math-verification/preflight.py --model NOMBRE_DEL_MODELO
~~~

Smoke test inicial:

~~~powershell
python experiments/exp-0001-math-verification/runner.py --model NOMBRE_DEL_MODELO --ids math-001,math-019 --temperature 0 --max-tokens 128 --timeout 300 --seed 42 --repair --new-run
~~~

Después puede generarse el reporte:

~~~powershell
python experiments/exp-0001-math-verification/report.py
~~~

Para el piloto completo se recomienda conservar una semilla explícita y registrar el archivo de resultados como artefacto de la ejecución.

## Reanudación

El runner guarda el estado después de cada tarea.

Solo reutiliza un run.json existente si el archivo declara el protocolo nuevo con:

~~~text
paired_initial_generation: true
~~~

Para una nueva ejecución experimental se recomienda --new-run.

## Limitaciones

El dataset actual contiene 20 problemas y es deliberadamente piloto. No permite generalizar el comportamiento del modelo.

La verificación determinista también puede fallar por formato no soportado, parser o especificación insuficiente. Esos estados se conservan para no atribuir automáticamente el fallo al modelo.
