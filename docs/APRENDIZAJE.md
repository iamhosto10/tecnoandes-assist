# Guía de aprendizaje

Cada concepto de RAG que toca este proyecto, con el archivo exacto donde
está implementado y qué problema resuelve ahí. Pensado para quien quiera
entender el "por qué" de una decisión sin leer todo el código.

## Chunking consciente de estructura

**`app/rag/chunking.py`** — el Markdown se parte por encabezados y
párrafos, con solapamiento entre chunks consecutivos, nunca por un conteo
fijo de caracteres. Cortar a ciegas puede partir una tabla de precios o
una oración a la mitad, perdiendo el dato justo que el cliente preguntó.

## Embeddings con prefijos de rol (E5)

**`app/rag/embeddings.py`** — `intfloat/multilingual-e5-small`, local vía
`sentence-transformers`, sin costo ni API key. E5 se entrenó distinguiendo
si el texto es una pregunta (`query: `) o un fragmento de la base de
conocimiento (`passage: `); sin esos prefijos la calidad del retrieval
baja notablemente porque el modelo no sabe qué rol está viendo.

## Ingesta idempotente

**`app/rag/ingestion.py`** — hash sha256 por chunk: solo se recalculan
embeddings de lo que cambió, no de la base entera en cada `make ingest`.
Bug real encontrado acá: la unique constraint de `chunk_index` se valida
por statement en Postgres, no al final de la transacción — insertar un
chunk nuevo antes de borrar el viejo con el mismo índice revienta la
constraint aunque el borrado esté en la misma transacción.

## Búsqueda híbrida + Reciprocal Rank Fusion

**`app/rag/retrieval.py`** — similitud vectorial y texto completo en
español, cada una una consulta SQL simple, fusionadas con RRF
(`score = sum(1 / (k + rank))` sobre la posición, no el puntaje crudo).
Ver [ADR 0001](adr/0001-hybrid-retrieval-raw-sql-rrf.md) para el porqué de
RRF sobre sumar puntajes directamente.

## Tool use forzado para salida estructurada confiable

**`app/rag/generation.py`** — `tool_choice` fijo contra `submit_answer`
con `strict: true`, en vez de pedirle al modelo que devuelva JSON en texto
libre. La API garantiza que la salida cumple el schema; Pydantic valida
una segunda vez, y cualquier falla (de red, de validación, de
credenciales) se refleja en `error` sin filtrarse como un 500 crudo al
cliente.

## Sistema de confianza explicable

**`app/confidence/`** — un puntaje ponderado (señales continuas) más
compuertas duras separadas (señales binarias con consecuencia clara). Ver
[ADR 0002](adr/0002-confidence-scoring-hard-gates.md). El desglose
completo (peso, valor normalizado, puntos por señal) se expone en la API
para que un frontend pueda mostrar "cómo se calculó" sin duplicar la
fórmula — ver `ConfidenceScoreBreakdown` en `app/confidence/scoring.py`.

## Calibración con datos, no a ojo

**`app/evaluation/`, `eval/seed.jsonl`** — los pesos y umbrales de
confianza empiezan como una heurística inicial (`.env`) y se recalibran
corriendo `make eval` contra un set de preguntas con respuesta esperada,
mirando `recall@k`, precisión de enrutamiento y el veredicto del juez, en
vez de ajustar números sin medir el efecto.

## LLM-as-judge (sin autoconfianza)

**`app/evaluation/judge.py`** — un segundo modelo compara la respuesta
real contra la esperada y emite un veredicto de hechos, vía el mismo
patrón de tool use forzado que la generación. Nunca se le pide al modelo
—ni al que genera ni al juez— su propia confianza: eso es justamente lo
que el sistema de confianza (arriba) calcula del lado del sistema, con
señales medibles. Ver [ADR 0004](adr/0004-llm-as-judge-evaluation.md).

## Human-in-the-loop de punta a punta

**`app/review/`** — la cola se puebla automáticamente cuando la decisión
no es `direct` (no hay un paso manual aparte); seis acciones de revisor
(`app/review/actions.py`); versionado de documentos antes de sobrescribir
(`app/review/documents.py`); y "re-probar" (`app/review/` +
`run_ask_pipeline`) corre el mismo pipeline de nuevo sobre la base ya
corregida — reusando la lógica de negocio, no el endpoint HTTP — para
comparar antes/después sin crear un caso duplicado.

## Brechas de conocimiento sin infraestructura extra

**`app/review/gaps.py`** — las preguntas sin soporte (`support=none`) se
agrupan por similitud de embeddings con `AgglomerativeClustering`
(métrica coseno, sin fijar de antemano cuántos grupos van a salir), **on
demand**, sin una tabla cacheada — a la escala de esta demo, recalcular es
instantáneo. Es el mismo patrón de "no construir infraestructura hasta que
haga falta" que la Decisión 5 de `CLAUDE.md`.

## Tipos de extremo a extremo

**`packages/api-client`** — tipos TypeScript generados directo del OpenAPI
de FastAPI (`openapi-typescript`), no interfaces duplicadas a mano.
Declarar los campos de enrutamiento como `Literal` (no `str`) en los
esquemas Pydantic hace que el OpenAPI genere enums de verdad, y el cliente
TS generado también — un cambio de backend que rompe un contrato se nota
en `tsc`, no en producción.
