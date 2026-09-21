# Protocolo de ejecución experimental

**Versión:** 0.2

## 1. Preparación

1. identificar modelo y versión/digest cuando sea posible;
2. fijar configuración;
3. identificar dataset y versión;
4. registrar hardware y runtime;
5. fijar semilla cuando aplique;
6. mostrar una estimación inicial o declarar que todavía no existe una referencia histórica.

## 2. Línea base

Ejecutar primero la condición de referencia sin la intervención estudiada.

## 3. Intervención

Aplicar únicamente la modificación definida por la hipótesis, salvo que el experimento declare una combinación.

## 4. Verificación

Aplicar verificadores deterministas disponibles y conservar su salida.

## 5. Evaluación

Calcular métricas primarias y secundarias. Registrar errores, timeouts y casos ambiguos.

## 6. Ejecución prolongada

El timeout del cliente es un mecanismo de protección, no una duración objetivo.

Se distinguen tres modos:

- **timeout finito:** una solicitud que excede el límite genera un error registrable;
- **sin timeout de cliente:** `timeout=0`; la solicitud continúa hasta que Ollama responda, falle o sea interrumpida;
- **interrupción manual:** el proceso puede detenerse sin considerar el trabajo restante como completado.

Una solicitud fallida no debe borrar resultados ya registrados.

## 7. Progreso y estimación

El runner debe mostrar antes y durante la ejecución:

- trabajo total;
- progreso;
- tiempo transcurrido;
- tiempo por tarea;
- estimación restante;
- estimación total cuando sea posible;
- errores/timeouts.

La estimación debe basarse en datos observados o históricos, nunca presentarse como una garantía.

## 8. Reanudación

Los resultados se escriben incrementalmente. Una ejecución interrumpida puede reanudarse utilizando el registro existente, evitando repetir tareas completadas.

Las ejecuciones nuevas deben conservar su propio archivo cuando se solicite `--new-run`.

## 9. Registro

Guardar configuración, entradas, salidas, trazas, métricas y artefactos necesarios para reconstruir el resultado.

## 10. Decisión

Separar observaciones de interpretación. No promocionar una variante por una sola métrica.

## 11. Reproducibilidad

Toda ejecución posterior debe indicar si reproduce exactamente el protocolo original o qué variable cambió.
