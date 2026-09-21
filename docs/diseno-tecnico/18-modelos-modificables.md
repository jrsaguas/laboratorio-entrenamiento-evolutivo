# 18. Modelos modificables

**Versión:** 0.1 | **Estado:** inicial

La modificabilidad se estudia por niveles:

1. prompts, herramientas y contexto;
2. adapters y fine-tuning;
3. pesos y arquitectura, cuando el stack experimental lo permita.

Cada experimento debe registrar exactamente qué parámetros o componentes fueron modificados y cuáles permanecieron constantes.

La cuantización usada para inferencia no debe confundirse con una modificación permanente de los pesos entrenables.
