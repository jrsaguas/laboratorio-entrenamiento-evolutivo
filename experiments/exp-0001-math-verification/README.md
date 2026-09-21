# EXP-0001 — Verificación matemática determinista

**Estado:** ejecutable y reanudable.

## Objetivo

Medir si una herramienta determinista mejora la fiabilidad matemática de un modelo base pequeño.

## Ejecución

Desde la raíz del repositorio:

```powershell
python experiments/exp-0001-math-verification/runner.py --model qwen3:4b-thinking-2507-q4_K_M --temperature 0 --max-tokens 128 --timeout 300
```

También puede ejecutarse sin límite de cliente:

```powershell
python experiments/exp-0001-math-verification/runner.py --model qwen3:4b-thinking-2507-q4_K_M --temperature 0 --max-tokens 128 --timeout 0
```

`--timeout 0` significa que el cliente Python no establece un límite temporal para la solicitud. Esto no impide una interrupción manual ni un fallo del servidor.

## Progreso y estimación

Antes de comenzar, el runner muestra:

- modelo y configuración;
- número de problemas;
- número total de generaciones;
- timeout;
- límite teórico cuando existe;
- estimación histórica si existen ejecuciones anteriores compatibles.

Durante la ejecución muestra:

- tarea actual;
- tiempo empleado;
- progreso global;
- estimación dinámica del tiempo restante.

La estimación es informativa y se recalcula con los tiempos reales observados.

## Reanudación

Después de cada tarea completada, el runner actualiza:

`experiments/exp-0001-math-verification/results/run.json`

Si el proceso se interrumpe y se vuelve a ejecutar con los mismos parámetros básicos y el mismo modelo, las tareas ya registradas se reutilizan y las faltantes continúan.

Para iniciar una ejecución nueva sin sobrescribir el registro anterior:

```powershell
python experiments/exp-0001-math-verification/runner.py --model qwen3:4b-thinking-2507-q4_K_M --temperature 0 --max-tokens 128 --timeout 0 --new-run
```

La nueva ejecución recibe un nombre con fecha y hora.

## Preflight

Antes de consumir tiempo de Ollama, ejecutar:

```powershell
python experiments/exp-0001-math-verification/preflight.py --model qwen3:4b-thinking-2507-q4_K_M
```

El preflight comprueba Ollama, la presencia del modelo y cuatro casos semánticos del verificador.

## Condiciones

- **Baseline:** el modelo responde directamente.
- **Verified:** el modelo responde y la respuesta se verifica con SymPy.
- `--repair` añade un intento explícito de corrección después de una verificación fallida.
- Ambas condiciones usan el mismo modelo, dataset, temperatura y límite de tokens.

La condición verificada no se interpreta como superior de antemano.

## Registro

Cada resultado conserva:

- respuesta y respuesta esperada;
- coincidencia exacta;
- éxito de verificación;
- intento de reparación;
- latencia;
- estadísticas devueltas por Ollama cuando están disponibles;
- errores;
- configuración del protocolo.

El resultado se guarda incrementalmente para reducir la pérdida de trabajo.

## Limitaciones conocidas

El dataset declara explícitamente el tipo semántico de cada respuesta (`scalar`, `expression`, `list` o `system`). El verificador normaliza formatos comunes y usa SymPy para las equivalencias. Una verificación fallida se registra con estado diagnóstico y **no debe interpretarse automáticamente como un error matemático del modelo**.

El dataset actual es piloto y no permite generalizar el comportamiento del modelo.
