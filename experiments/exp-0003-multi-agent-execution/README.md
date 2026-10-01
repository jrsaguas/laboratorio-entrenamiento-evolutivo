# EXP-0003 — Ejecución multiagente reproducible

## Objetivo

Validar una primera ejecución real del orquestador con planificación automática y
dos agentes especializados:

matemática → visualización Python.

La tarea fija es:

z = x² + y²

El experimento no compara modelos. Valida que una tarea pueda ser interpretada,
descompuesta mediante capacidades, ejecutada mediante dependencias y produzca
un artefacto verificable.

## Flujo

problema
→ planificación determinista
→ MathReasoningAgent
→ resultado simbólico
→ PythonVisualizationAgent
→ SVG
→ verificación
→ traza.

## Planificación

La primera versión del planificador es deliberadamente determinista y auditable.
No utiliza un LLM para decidir todavía. Extrae señales explícitas del objetivo,
entrada y artefactos solicitados y selecciona capacidades del registro.

Para esta tarea decidió:

1. solve_math porque existe estructura matemática.
2. visualize_math_python porque se solicitó una visualización y debe consumir
   el resultado matemático.

La decisión y su justificación quedan registradas en run.json.

## Reproducibilidad

Se registra el commit Git, protocolo, solicitud, plan, grafo, traza,
verificaciones, hash SHA-256 y tamaño del artefacto. La generación del SVG usa
solo Python estándar, por lo que esta primera ejecución no depende de Matplotlib.

La latencia y las marcas temporales son métricas de ejecución y no forman parte
del contenido determinista del artefacto.

Dos ejecuciones consecutivas produjeron el mismo SHA-256:

a4ddeb4ca0568f1c5e67304cbbdddd558a44032585e7eb13da363ae00c0ddacf

## Criterio de éxito

- el planificador selecciona las capacidades esperadas;
- ambos nodos terminan en completed;
- la derivación matemática pasa la verificación simbólica;
- el SVG pasa la verificación de integridad;
- existe una traza con el orden matemática → visualización;
- el hash del artefacto queda registrado y es estable entre ejecuciones.

## Limitación

Esta prueba valida la arquitectura de planificación y ejecución, no la capacidad
general de resolver cualquier problema. El planificador actual usa reglas
deterministas explícitas; todavía no realiza selección semántica general,
optimización de costes, reparación automática ni aprendizaje de estrategias.
