# 0002 — Puntaje de confianza ponderado + compuertas duras separadas

## Estado

Aceptado (Fase 2).

## Contexto

El sistema necesita decidir, por cada respuesta, si se muestra directo, con
advertencia, o se manda a revisión humana. Hay señales de dos naturalezas
muy distintas: continuas (similitud del mejor chunk, margen contra el
segundo) y binarias con consecuencia clara (¿el cliente pidió un humano?,
¿el modelo citó un chunk que no existía en el contexto?).

## Decisión

Solo tres señales entran en un puntaje ponderado 0–100
(`retrieval_score`, `retrieval_margin`, `support`, ver
`app/confidence/scoring.py`). `needs_human` y `citation_valid` son
**compuertas duras**, evaluadas antes y por fuera del puntaje
(`app/confidence/rules.py`): si el cliente pidió un humano, se escala sin
mirar el puntaje; si la cita es inválida, va a revisión sin mirar el
puntaje. Las reglas se evalúan en un orden estricto, la primera que aplica
gana. El puntaje igual se calcula y se guarda siempre — incluso cuando una
compuerta dura ya decidió — para no perder esa señal en el audit.

Explícitamente, **nunca se le pide al modelo su propia confianza**: el
puntaje se calcula del lado del sistema a partir de señales medibles
(similitud de retrieval, margen, y el `support` que el modelo reporta
comparando su respuesta contra el contexto, no una nota subjetiva de
"qué tan seguro estoy").

## Consecuencias

- Un reclamo o una cita inventada nunca puede "colarse" a `direct` solo
  porque el resto de las señales dieron un puntaje alto — la compuerta
  dura corta antes de llegar ahí.
- El desglose completo (peso, valor normalizado, puntos por señal) se
  expone en la API (`ConfidenceScoreBreakdown`), lo que permite mostrar
  "cómo se calculó" en el modo transparente del chat y en la consola sin
  que el frontend duplique la fórmula.
- Los pesos y umbrales viven en `.env`, no hardcodeados — son una
  heurística inicial pensada para calibrarse con `make eval` (Fase 6).

## Alternativas consideradas

- **Pedirle al modelo un score de confianza numérico.** Descartado
  explícitamente: un LLM no tiene una introspección confiable sobre su
  propia probabilidad de error: es un patrón conocido de sobreconfianza.
- **Meter `needs_human`/`citation_valid` como señales ponderadas más.**
  Descartado porque diluye su urgencia — un reclamo con puntaje ponderado
  "aceptable" en las demás señales podría terminar mostrándose directo.
