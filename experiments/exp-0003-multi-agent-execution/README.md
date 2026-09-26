# EXP-0003 — Ejecución multiagente reproducible

## Objetivo

Validar una primera ejecución real del orquestador con dos agentes especializados:
matemática → visualización Python.

La tarea fija es:

z = x² + y²

El experimento no compara modelos. Valida que una tarea pueda descomponerse,
ejecutarse mediante dependencias y producir un artefacto verificable.

## Flujo

problema → MathReasoningAgent → resultado simbólico
→ PythonVisualizationAgent → SVG → verificación → traza

## Reproducibilidad

Se registra el commit Git, protocolo, solicitud, grafo, traza, verificaciones,
hash SHA-256 y tamaño del artefacto. La generación del SVG usa solo Python
estándar, por lo que esta primera ejecución no depende de Matplotlib.

La latencia y las marcas temporales son métricas de ejecución y no forman parte
del contenido determinista del artefacto.

## Criterio de éxito

- ambos nodos terminan en completed;
- la derivación matemática pasa la verificación simbólica;
- el SVG pasa la verificación de integridad;
- existe una traza con el orden math → visualization;
- el hash del artefacto queda registrado.

## Limitación

Esta prueba valida la arquitectura y el flujo reproducible, no la capacidad
general de resolver cualquier problema matemático ni la calidad visual del SVG.
