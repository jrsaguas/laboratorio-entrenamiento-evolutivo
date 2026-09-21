# EXP-0001 — Verificación matemática determinista

**Estado:** especificación inicial  
**Objetivo:** medir si una herramienta determinista mejora la fiabilidad matemática de un modelo base pequeño.

## Pregunta

¿La incorporación de Python/SymPy como mecanismo de verificación reduce errores matemáticos frente a una respuesta generada únicamente por el modelo?

## Diseño

- **Baseline A:** modelo responde directamente.
- **Intervención B:** modelo propone una solución y Python/SymPy verifica los pasos o el resultado cuando sea posible.
- **Variable independiente:** presencia del verificador.
- **Variables controladas:** modelo, conjunto de problemas, temperatura/configuración, presupuesto de tokens y formato de respuesta.
- **Unidad experimental:** problema matemático individual.
- **Repetición:** cada condición debe ejecutarse con semillas/configuraciones documentadas.

## Dataset inicial

Se comenzará con problemas deterministas y verificables automáticamente, por ejemplo:

- álgebra elemental;
- ecuaciones;
- derivadas;
- integrales sencillas;
- simplificación simbólica.

El dataset debe crecer por dificultad y conservar una referencia verificable.

## Métricas

1. exactitud final;
2. resultado verificado correctamente;
3. tasa de errores detectados;
4. tasa de falsos positivos del verificador;
5. tokens utilizados;
6. latencia;
7. coste computacional aproximado.

## Criterio

El resultado no se reducirá a una sola puntuación. Se reportarán métricas por condición y por categoría de problema.

Una mejora solo se considerará evidencia a favor de la intervención si supera la línea base bajo el mismo protocolo y no introduce una regresión relevante en las métricas secundarias.

## Artefactos previstos

- especificación del experimento;
- dataset versionado;
- respuestas del modelo;
- resultados del verificador;
- métricas;
- configuración;
- trazas;
- informe final.

## Regla de seguridad experimental

El verificador es una fuente externa de evidencia. Su resultado no debe convertirse automáticamente en una modificación de pesos. Primero se registra, evalúa y analiza.
