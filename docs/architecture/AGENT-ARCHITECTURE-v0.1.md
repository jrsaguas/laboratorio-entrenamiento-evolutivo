# Arquitectura de agentes especializados — Contrato v0.1

**Proyecto:** laboratorio-entrenamiento-evolutivo  
**Fecha:** 25 de septiembre de 2026  
**Estado:** diseño inicial posterior a EXP-0002

## 1. Objetivo

Definir un contrato común para agentes especializados antes de implementar el orquestador. El objetivo no es crear varios chatbots independientes, sino componentes intercambiables que produzcan artefactos verificables y que puedan ser coordinados por un orquestador experimental.

El ciclo global previsto es:

`problema → generación → verificación → crítica → reparación → reevaluación → evidencia → memoria/evolución`

El orquestador añade la selección y coordinación de capacidades:

`tarea → análisis → plan → delegación → ejecución → verificación → integración → evidencia → resultado`

## 2. Principio arquitectónico

Un agente no decide unilateralmente que su trabajo es correcto. Produce una salida junto con evidencia, estado y artefactos. La verificación pertenece a componentes explícitos y reproducibles.

La especialización determina **cómo trabaja** un agente; el contrato determina **cómo se comunica** con el resto del sistema.

## 3. Contrato común del agente

Cada agente debe aceptar una solicitud estructurada con al menos:

- `task_id`: identificador único.
- `objective`: objetivo de la tarea.
- `input`: datos necesarios para trabajar.
- `constraints`: restricciones explícitas.
- `depth_profile`: perfil multidimensional de profundidad matemática.
- `requested_artifacts`: artefactos solicitados.
- `verification_requirements`: verificaciones obligatorias.
- `context_refs`: referencias/evidencia disponible.
- `budget`: límites de tiempo, tokens, herramientas o iteraciones.

Cada ejecución debe devolver:

- `task_id`
- `agent_id`
- `status`: `completed`, `partial`, `failed`, `blocked`.
- `result`: resultado principal.
- `artifacts`: archivos/código/figuras/documentos generados.
- `claims`: afirmaciones que requieren verificación.
- `evidence`: fuentes, cálculos, pruebas o trazas que respaldan el resultado.
- `verification`: resultados de verificadores ejecutados.
- `uncertainties`: puntos no resueltos o supuestos.
- `actions`: operaciones realizadas.
- `metrics`: latencia, tokens, iteraciones y otros datos disponibles.
- `provenance`: modelo, versión de agente, herramientas y commit/configuración relevante.

## 4. Estados y separación de responsabilidades

`completed` significa que el agente terminó su trabajo, no que el resultado sea verdadero.

`verification` registra la evaluación externa o determinista.

`uncertainties` impide convertir supuestos en hechos.

`provenance` permite reproducir la ejecución.

Ningún agente debe ocultar errores de herramienta, fallos parciales o respuestas no verificadas.

## 5. Perfil multidimensional de profundidad matemática

La profundidad no será un único nivel ordinal. Se representa como dimensiones independientes, inicialmente en escala 0–100:

| Dimensión | Qué controla |
|---|---|
| `rigor` | precisión de definiciones, condiciones y argumentos |
| `prerequisites` | cantidad/profundidad de conocimientos previos asumidos |
| `formalism` | formalización simbólica y notación |
| `proof` | demostración, justificación y trazabilidad lógica |
| `research` | tratamiento de literatura, estado del conocimiento y cuestiones abiertas |
| `visualization` | uso y profundidad de representaciones geométricas/gráficas |
| `experimentation` | uso de cálculo computacional y experimentos reproducibles |
| `generalization` | extensión a casos abstractos, familias o estructuras generales |

Un perfil de nivel doctoral no significa simplemente `100` en todo. Puede expresar, por ejemplo, alto rigor/proof/formalism y una visualización o experimentación ajustada al objetivo.

## 6. Agentes iniciales

### 6.1 Math Reasoning Agent

Responsabilidad: resolver, derivar, demostrar, verificar conceptualmente y estructurar razonamiento matemático.

Herramientas potenciales: SymPy/CAS, verificador determinista, Python, recuperación de referencias.

No debe declarar verdad matemática únicamente por producir una respuesta plausible.

### 6.2 Code Agent

Responsabilidad: diseñar, implementar, modificar y probar código.

Debe producir cambios trazables, pruebas y diagnóstico de fallos. No debe mezclar una explicación conceptual con cambios de código no declarados.

### 6.3 HTML/JS Canvas Agent

Responsabilidad: construir interfaces web interactivas, visualizaciones Canvas/SVG/DOM y componentes de interacción.

Debe separar estructura, lógica, estilos y datos cuando corresponda y generar una interfaz reproducible a partir de sus entradas.

### 6.4 Python Math/Physics Visualization Agent

Responsabilidad: generar modelos computacionales, gráficas y visualizaciones de matemáticas/física mediante Python, con énfasis en reproducibilidad numérica y trazabilidad de parámetros.

Debe conservar código fuente de la figura/experimento cuando sea parte del artefacto solicitado.

## 7. Capacidades frente a herramientas

Un agente define capacidades; el acceso a una herramienta concreta es una dependencia de ejecución.

Ejemplo:

`Math Reasoning Agent → capacidad: symbolic_verification`

puede resolverse mediante:

`SymPy | CAS externo | verificador interno`

El contrato no debe acoplar al agente a un proveedor único.

## 8. Orquestador

El orquestador no genera necesariamente el contenido final. Sus responsabilidades son:

1. interpretar la tarea;
2. construir el perfil de requisitos;
3. seleccionar capacidades/agentes;
4. construir el grafo de trabajo;
5. pasar contexto y restricciones;
6. ejecutar etapas y dependencias;
7. solicitar verificación cuando corresponda;
8. decidir si una salida requiere crítica o reparación;
9. integrar artefactos compatibles;
10. registrar evidencia y provenance;
11. devolver un resultado compuesto.

La selección debe basarse en **capacidades y requisitos**, no solamente en nombres de agentes.

## 9. Grafo de tarea

Una tarea compleja se representa como nodos con:

- `node_id`
- `capability`
- `agent`
- `inputs`
- `dependencies`
- `constraints`
- `verification_policy`
- `retry_policy`
- `status`
- `artifacts`

Esto permite que, por ejemplo, una tarea matemática con visualización genere un flujo:

`Math Reasoning → Math Verification → Python Visualization → Visualization Check → Integration`

mientras que una tarea de implementación pueda usar:

`Planner → Code Agent → Tests → Reviewer → Integration`.

## 10. Verificación y reparación

La reparación no forma parte automáticamente de todos los agentes. Es una intervención explícita del grafo.

Patrón:

`generate → verify → if failure → critique → repair → verify`

Cada intervención debe registrar su coste y resultado. El sistema debe poder distinguir:

- fallo del modelo;
- fallo del parser/verificador;
- fallo de herramienta;
- fallo de integración;
- restricción incumplida.

## 11. Evidencia y memoria

La salida de un agente puede convertirse en evidencia experimental únicamente si conserva provenance suficiente.

La memoria futura debe distinguir al menos:

- conocimiento/evidencia externa;
- resultado experimental;
- estrategia utilizada;
- resultado de la estrategia;
- error conocido;
- artefacto generado;
- preferencia/configuración del usuario cuando sea explícitamente relevante.

## 12. Reglas de implementación

1. Primero contrato y schemas.
2. Después adaptadores de agentes.
3. Después orquestación mínima.
4. Después verificación cruzada.
5. Después experimentos multiagente.
6. Las nuevas capacidades deben añadir pruebas antes de incorporarse al ciclo experimental.

No se implementará todavía un sistema evolutivo completo ni una memoria de aprendizaje antes de disponer de trazas reproducibles de las ejecuciones multiagente.

## 13. Criterio de aceptación del diseño

El diseño queda listo para implementación cuando:

- el contrato de entrada/salida es representable como schema;
- los cuatro agentes pueden implementar el mismo contrato sin compartir lógica específica;
- las herramientas se pueden sustituir sin cambiar el contrato;
- el orquestador puede representar dependencias entre tareas;
- verificación, reparación y provenance son explícitos;
- el perfil matemático no depende de un único nivel ordinal;
- cada ejecución puede convertirse en una traza experimental reproducible.

## 14. Separación entre capacidad e implementación

La capacidad es la unidad estable que consume el planificador. La implementación es el mecanismo concreto que ejecuta esa capacidad.

Ejemplo conceptual:

`solve_math`
→ `builtin.sympy`
→ `ollama.qwen2-math`
→ `ollama.qwen3`
→ `gemini`

La misma capacidad puede tener múltiples implementaciones sin cambiar el contrato del nodo de tarea.

Cada implementación declara como mínimo:

- `implementation_id`;
- `capability`;
- `provider`;
- `model` cuando aplique;
- `execution_mode`;
- `cost_class`;
- `deterministic`;
- `available`.

El orquestador resuelve en dos pasos:

`capability → implementation → agent`

El grafo puede fijar una implementación explícita, pero si no lo hace se utiliza la implementación predeterminada registrada para esa capacidad. La traza registra siempre la implementación efectiva y su provenance.

Esta separación permite introducir posteriormente backends locales, Ollama, APIs externas u otras ejecuciones sin convertir al proveedor en parte del contrato de la capacidad.

La selección automática de modelos o proveedores queda fuera de este bloque. Primero debe existir un registro reproducible y una medición controlada; después podrán evaluarse estrategias de selección.

## 15. Primer backend de modelo: Ollama

La primera implementación externa registrada para solve_math es ollama.qwen2-math, con:

- provider: ollama;
- model: qwen2-math:7b;
- execution mode: ollama_api;
- selección explícita, no predeterminada.

El adaptador conserva el resultado del modelo como generación y deja la verificación semántica a un verificador determinista externo.

Se realizó además un smoke test real independiente del protocolo formal: el adaptador ejecutó qwen2.5:3b para 1 + 1 y obtuvo 2 en 76.90 s. Esta medición valida la conectividad y el contrato del backend; no constituye una comparación de modelos ni una afirmación de exactitud general.

La implementación predeterminada de solve_math continúa siendo builtin.sympy.
