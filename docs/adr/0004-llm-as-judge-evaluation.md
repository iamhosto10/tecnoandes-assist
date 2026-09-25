# 0004 — LLM-as-judge para evaluar calidad de respuesta, no autoconfianza

## Estado

Aceptado (Fase 6).

## Contexto

`make eval` necesita medir si el pipeline "contestó bien" comparado contra
un set de preguntas con respuesta esperada
(`eval/seed.jsonl`). Comparar texto libre contra texto libre no se puede
hacer con un `==` ni con similitud léxica simple (dos respuestas correctas
pueden estar redactadas de forma distinta).

## Decisión

Un segundo modelo (configurable aparte, `ANTHROPIC_JUDGE_MODEL`, Haiku 4.5
por defecto) actúa de juez: recibe la pregunta, la respuesta esperada y la
respuesta real, y devuelve un veredicto (`correct`/`partial`/`incorrect`)
más una razón breve, vía tool use forzado (mismo patrón que la generación:
`strict: true`, sin texto libre). El juez compara **hechos** (precios,
plazos, sedes, políticas), no estilo ni longitud.

Como en la Decisión 0002, **nunca se le pide al juez ni al modelo generador
su propia confianza** — el juez emite un juicio de hechos sobre dos textos
que se le entregan, no una introspección sobre su propia certeza.

El juez solo se llama en casos que tienen una `expected_answer` — los casos
`should_escalate` (reclamos) se evalúan por si el sistema escaló o no
(`routing_correct`), no por la calidad prosa del mensaje de traspaso.

## Consecuencias

- El costo de evaluar casi se duplica (una llamada de generación + una de
  juicio por caso), pero a precios de Haiku 4.5 sigue siendo marginal
  (~$0.02 USD por los 25 casos del set semilla).
- El juez puede equivocarse — es otro LLM, no un oráculo. Se documenta
  como limitación conocida, no se presenta como verdad absoluta; sirve
  para detectar regresiones y guiar la calibración, no como aprobación
  final sin revisión humana.
- Usar el mismo modelo para generar y para juzgar corre el riesgo de que
  un modelo "se audite a sí mismo" de forma indulgente — por eso el
  modelo juez es configurable aparte, aunque por defecto coincida.

## Alternativas consideradas

- **Comparación léxica (BLEU/ROUGE, similitud de embeddings).** Descartada
  porque penaliza respuestas correctas con distinta redacción y no
  distingue "cambié una palabra" de "cambié el precio".
- **Revisión 100% humana del set de evaluación.** Más confiable pero no
  escala a correr en cada recalibración — el juez LLM es el primer filtro
  automático, no un reemplazo de la revisión humana que ya hace el resto
  del sistema (Fase 3).
