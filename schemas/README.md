# Agent schemas

Schemas ejecutables del contrato de agentes definido en
`docs/architecture/AGENT-ARCHITECTURE-v0.1.md`.

## Archivos

- `depth_profile.json`: perfil matemático multidimensional 0-100.
- `verification_policy.json`: política explícita de verificación y reparación.
- `agent_request.json`: entrada común para cualquier agente.
- `agent_result.json`: salida común para cualquier agente.
- `task_node.json`: nodo ejecutable del grafo de tareas.
- `task_graph.json`: grafo compuesto por nodos y dependencias.

Todos usan JSON Schema Draft 2020-12 y referencias relativas entre
schemas. El contrato no fija proveedor, modelo ni herramienta concreta.

## Regla de compatibilidad

Los adaptadores de agentes deben producir documentos compatibles con estos
schemas sin cambiar el contrato común. Las herramientas y modelos se
declaran en `provenance` o en la configuración de ejecución, no en el
schema de identidad del agente.

## Validación

La batería de tests del repositorio comprueba que los schemas son JSON
válido y que sus invariantes contractuales básicas permanecen estables.
La validación completa con un motor JSON Schema externo queda desacoplada
del contrato para no introducir una dependencia de ejecución en esta fase.
