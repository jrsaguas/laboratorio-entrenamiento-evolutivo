# Protocolo de ejecución experimental

**Versión:** 0.1

## 1. Preparación

1. identificar el modelo y su versión;
2. fijar configuración;
3. identificar dataset y versión;
4. registrar hardware y runtime;
5. fijar semilla cuando aplique.

## 2. Línea base

Ejecutar primero la condición de referencia sin la intervención estudiada.

## 3. Intervención

Aplicar únicamente la modificación definida por la hipótesis, salvo que el experimento declare una combinación.

## 4. Verificación

Aplicar verificadores deterministas disponibles y conservar su salida.

## 5. Evaluación

Calcular métricas primarias y secundarias. Registrar errores y casos ambiguos.

## 6. Registro

Guardar configuración, entradas, salidas, trazas, métricas y artefactos necesarios para reconstruir el resultado.

## 7. Decisión

Separar observaciones de interpretación. No promocionar una variante por una sola métrica.

## 8. Reproducibilidad

Toda ejecución posterior debe indicar si reproduce exactamente el protocolo original o qué variable cambió.
