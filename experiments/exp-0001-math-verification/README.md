# EXP-0001 — Verificación matemática determinista

**Estado:** ejecutable como experimento inicial  
**Objetivo:** medir si una herramienta determinista mejora la fiabilidad matemática de un modelo base pequeño.

## Pregunta

¿La incorporación de Python/SymPy como mecanismo de verificación reduce errores matemáticos frente a una respuesta generada directamente por el modelo?

## Condiciones

- **Baseline:** el modelo responde directamente.
- **Verified:** el modelo responde, la respuesta se verifica con SymPy y puede realizarse una reparación explícita cuando se ejecuta con `--repair`.
- **Mismo modelo:** ambas condiciones utilizan el mismo identificador de modelo.
- **Mismo dataset:** ambas condiciones utilizan exactamente el mismo archivo.
- **Misma configuración:** temperatura y límite de tokens se mantienen constantes.

La condición verificada no se interpreta como superior de antemano. El runner registra ambas condiciones para compararlas.

## Ejecución local

El runner utiliza por defecto la API nativa de Ollama:

```text
http://127.0.0.1:11434/api/generate
```

Esto evita depender de la compatibilidad OpenAI y permite trabajar directamente con los modelos instalados localmente.

Ejemplo:

```powershell
python -m experiments.exp-0001-math-verification.runner --model qwen2-math:7b --repair
```

Si el paquete se ejecuta directamente desde el directorio raíz, puede utilizarse:

```powershell
python experiments/exp-0001-math-verification/runner.py --model qwen2-math:7b --repair
```

El segundo formato puede requerir que el directorio raíz esté en `PYTHONPATH`; el primer formato es el preferido cuando los paquetes tengan los `__init__.py` correspondientes.

## Salida

El resultado se escribe en:

```text
experiments/exp-0001-math-verification/results/run.json
```

El JSON conserva:

- condición;
- problema;
- respuesta;
- respuesta esperada;
- coincidencia exacta;
- verificación;
- intento de reparación;
- latencia;
- errores;
- configuración del protocolo.

## Métricas

1. exactitud final;
2. éxito de verificación;
3. errores detectados;
4. éxito después de reparación;
5. latencia;
6. tokens, cuando el runtime los proporcione;
7. coste computacional aproximado.

## Interpretación

Una mejora debe compararse con la baseline bajo el mismo protocolo. El tamaño inicial del dataset es deliberadamente pequeño y **no permite extraer conclusiones generales sobre un modelo**. Su función actual es validar el circuito experimental.

## Próxima ampliación

Después de comprobar que el circuito funciona, se ampliará el dataset, se añadirán categorías y dificultad, se registrarán más estadísticas del runtime y se incorporarán pruebas repetidas antes de usar los resultados para generar datos de entrenamiento.
