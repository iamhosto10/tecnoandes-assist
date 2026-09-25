# TecnoAndes Assist

RAG con sistema de confianza y revisión humana para una tienda de tecnología ficticia
(TecnoAndes). Proyecto de portafolio — ver el plan original y las fases en
`docs/adr/` y `docs/APRENDIZAJE.md` (se agregan en fases posteriores).

## Comandos

```bash
make up          # docker compose up -d --build (db + backend)
make down         # apaga todo
make logs         # logs del backend
make migrate      # aplica migraciones de Alembic
make db-shell     # psql dentro del contenedor de la db
make test         # pytest del backend (corre sin API key ni internet)
make lint         # ruff check

make ingest       # Fase 1 — procesa knowledge_base/ a chunks + embeddings
make search q="…" # Fase 1 — solo retrieval, sin LLM (para depurar búsqueda)
make eval         # Fase 6 — corre eval/seed.jsonl y calcula métricas
make seed-demo    # Fase 7 — carga consultas de ejemplo para la demo
make chat             # Fase 4 — pnpm install + dev server de apps/chat (localhost:3000)
make review-console  # Fase 5 — pnpm install + dev server de apps/review-console (localhost:3001)
```

Backend fuera de Docker: `cd backend && uv sync && uv run uvicorn app.main:app --reload`.

Si agregas una dependencia nueva a `backend/pyproject.toml`, el contenedor
del backend no la recoge solo con `--reload` (eso solo reinicia los
workers de uvicorn, no vuelve a correr `uv sync`) — hace falta
`docker compose restart backend` (o `make up` de nuevo) para que la
sincronice.

## Stack y convenciones

- **Backend**: Python 3.12 (fijado con `uv`), FastAPI **síncrono** (endpoints `def`,
  no `async def`), Pydantic v2, SQLAlchemy 2 + Alembic, driver `psycopg` v3.
- **DB**: Postgres + pgvector (`pgvector/pgvector:pg16`), un único contenedor para
  vectores, cola de revisión, evaluación y auditoría. Índice HNSW para vectores,
  `tsvector` en español (`unaccent`) para texto completo.
- **Embeddings**: `intfloat/multilingual-e5-small` (384 dim) local vía
  `sentence-transformers`, detrás de la interfaz `EmbeddingProvider`
  (`app/rag/embeddings.py`, Fase 1). Respeta los prefijos `query:` / `passage:` de E5.
- **LLM**: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`), configurable vía
  `ANTHROPIC_MODEL`, nunca hardcodeado.
- **Frontends**: `apps/chat` y `apps/review-console`, Next.js (App Router) + TS +
  Tailwind + shadcn/ui, en un workspace de **pnpm**. `packages/api-client` tiene
  tipos TS generados del OpenAPI del backend, compartidos por ambas apps.
- **Sin LangChain/LlamaIndex** en el núcleo — el pipeline RAG se escribe a mano.
- **Idioma**: UI en español, código (variables/funciones/clases) en inglés.
- **Comentarios**: solo explican el *por qué*, nunca el *qué*. Cada concepto de RAG
  (chunking, RRF, calibración, etc.) lleva un comentario corto donde se implementa.
- **Secretos**: todo en `.env` (raíz del repo, gitignored), nunca en código.
  `.env.example` documenta cada variable.

## Decisiones clave (con su trade-off)

1. **Retrieval híbrido en SQL crudo.** Modelos/CRUD usan SQLAlchemy ORM +
   Alembic, pero la consulta de RRF (vector + full-text) se escribe con
   `sqlalchemy.text()` porque un CTE de RRF es incómodo en el query builder y
   es la pieza que más se debuggea en un RAG — se prioriza la legibilidad del SQL.
2. **Sin tabla de auditoría genérica.** La trazabilidad sale de `queries`
   (log inmutable de cada `/ask`), `document_versions` (historial de documentos)
   y `review_actions` (historial de acciones del revisor) — más simples de
   consultar que una tabla `audit_log` polimórfica.
3. **"Brechas de conocimiento" sin tabla persistida.** Se agrupan on-demand por
   similitud de embeddings sobre `queries` con `support=none`, no en una tabla
   cacheada — a escala de demo, recalcular es instantáneo.
4. **Auth de la consola de revisión**: token único en `.env`
   (`REVIEW_CONSOLE_TOKEN`). Es solo para la demo; documentado en
   `docs/adr/` qué se usaría en producción (OAuth/sesiones por usuario).
5. **RRF en Python, no en el SQL.** `hybrid_search` corre dos consultas simples
   (vector, full-text) y fusiona los rankings con `reciprocal_rank_fusion`, una
   función pura en `app/rag/retrieval.py` — así el SQL se puede depurar por
   separado y la fórmula de RRF se puede testear sin base de datos.
6. **`torch` fijado al índice CPU-only** de PyTorch (`[tool.uv.sources]` en
   `backend/pyproject.toml`). El wheel por defecto de PyPI arrastra ~2GB de
   paquetes `nvidia-*` en Linux que nunca se usan (embeddings corren en CPU).
7. **`needs_human`/`citation_valid` son compuertas duras, no señales ponderadas.**
   Solo `retrieval_score`, `retrieval_margin` y `support` entran en el puntaje
   0-100; las otras dos deciden el enrutamiento directamente en `rules.py`
   (ver sección 9 del diseño original). El puntaje igual se calcula y se
   guarda siempre, aunque una regla dura ya haya decidido, para el audit.
8. **"review" nunca muestra la respuesta cruda del modelo; "escalate" sí.**
   Cuando la decisión es `review` (sin soporte, puntaje bajo, o error de
   generación) el cliente ve un mensaje de respaldo genérico — no lo que
   escribió el modelo, aunque sea válido, porque `support=none`/error
   significan que no se confía en esa respuesta. Cuando es `escalate`
   (`needs_human=true`) sí se muestra la respuesta del modelo, porque el
   prompt lo instruye a redactarla ya pensando en el traspaso a un humano.
9. **El SDK de Anthropic puede lanzar `TypeError`, no solo `anthropic.APIError`,
   si no hay ninguna credencial configurada** (confirmado corriendo el
   endpoint real sin `ANTHROPIC_API_KEY`). `generate_answer` atrapa ambos —
   de lo contrario esa falla de configuración se filtraba como un 500 crudo.
10. **`review_items` se crea automáticamente en `/ask`** cuando la decisión
    no es "direct" — no hay un paso manual ni un job aparte; el mismo
    request que responde al cliente deja el caso listo en la cola.
    `reason` reusa el `rule_applied` de la regla de confianza que disparó,
    sin inventar una segunda taxonomía de motivos.
11. **`ingest_document` borra antes de insertar, nunca al revés.**
    `chunk_index` tiene una unique constraint por documento que Postgres
    valida al ejecutar cada statement (no al final de la transacción) —
    intentar insertar el chunk nuevo antes de borrar el viejo con el mismo
    índice revienta esa constraint incluso si el borrado iba a pasar en la
    misma transacción. Se corrige borrando los chunks obsoletos primero
    (con flush) y pasando los reusados por un índice temporal negativo
    antes de asignarles su posición final. Encontrado por los tests de
    integración de `PUT /documents/{id}` al reemplazar todo el contenido
    de un documento.
12. **`compute_confidence_score` devuelve el desglose completo, no solo el
    total.** Cada señal normalizada trae su peso y sus puntos aportados
    (`ConfidenceScoreBreakdown`), expuesto en la API como
    `confidence.score_breakdown` — es lo que hace posible mostrar "el
    cálculo del puntaje" en el modo transparente del chat sin que el
    frontend tenga que adivinar o duplicar los pesos de `.env`.
13. **`decision`/`rule_applied`/`status`/`action_type` son `Literal`, no
    `str`, en los esquemas Pydantic.** Así el OpenAPI genera enums de
    verdad y `packages/api-client` produce tipos TS reales (`"direct" |
    "warn" | ...`) en vez de un `string` genérico — se notó al
    type-checkear `apps/chat` contra el cliente generado.
14. **Un solo pnpm-workspace.yaml, en la raíz.** `create-next-app` genera
    su propio `pnpm-workspace.yaml` dentro de `apps/chat` si no detecta
    uno más arriba en el momento del scaffold — hay que borrarlo y mover
    cualquier config real (`ignoredBuiltDependencies`, por los build
    scripts de `sharp`/`unrs-resolver`) a la raíz, o `apps/chat` queda
    como un workspace pnpm aislado y no puede resolver
    `@tecnoandes/api-client` como dependencia de workspace. Pasó de nuevo
    al scaffolding de `apps/review-console` — mismo síntoma, misma
    corrección; es un gotcha recurrente de `create-next-app`, no algo
    puntual de la primera app.
15. **Base UI (`@base-ui/react`), no Radix, detrás de shadcn/ui.** El
    generador de shadcn eligió Base UI para este proyecto. Dos diferencias
    que rompen el hábito de Radix:
    - `Button` no tiene prop `asChild`; se compone con `render={<X/>}` en
      su lugar (`DialogTrigger render={<Button>...</Button>} />`, etc.).
    - `Button` **nunca** debe envolver un `<Link>` — la documentación de
      Base UI lo prohíbe explícitamente (rompe accesibilidad: "expected a
      native `<button>`"). Para un link con estilo de botón se aplica
      `buttonVariants({...})` como `className` directo sobre el `<Link>`,
      no se anida un `Button` alrededor.
16. **`Select.Value` de Base UI muestra el `value` crudo, no la label del
    `SelectItem` seleccionado** (a diferencia de Radix, que sí la infiere
    solas). Hay que mapear a mano con el patrón de children-como-función:
    `<SelectValue>{(value) => LABELS[value] ?? fallback}</SelectValue>`.
    Se encontró probando en vivo (mostraba el id numérico del documento y
    hubiera mostrado literales como `needs_human` en el filtro de la cola).
    `REASON_LABELS` se exporta una sola vez desde `badges.tsx` y se reusa
    en el filtro de la cola para no duplicar las etiquetas en español.
17. **Brechas de conocimiento: clustering con `AgglomerativeClustering`
    (scikit-learn), no un umbral manual de coseno.** `distance_threshold`
    en vez de `n_clusters` (no se sabe cuántos grupos hay de antemano),
    métrica coseno, linkage promedio. Solo agrupa preguntas con
    `support="none"`; el representante de cada grupo es la pregunta más
    corta (mejor candidata a título de un documento nuevo). Umbral
    configurable vía `KNOWLEDGE_GAP_DISTANCE_THRESHOLD` (`.env`).
18. **La consola de revisión recalcula el desglose de confianza con los
    pesos ACTUALES de `.env`, no con los que estaban vigentes cuando se
    creó el caso.** Simplificación aceptada para la demo — las señales
    crudas (`retrieval_score`, `retrieval_margin`, `support`) sí quedan
    guardadas en `queries`, así que el recálculo es reproducible, pero si
    cambias los pesos después de que un caso quedó en la cola, el
    "cálculo del puntaje" que ve el revisor usa los pesos de hoy.
19. **`routing_correct` en la evaluación solo exige acertar escalar o no
    escalar, no las cuatro categorías de la escala completa
    (direct/warn/review/escalate).** `should_escalate=true` en
    `eval/seed.jsonl` marca reclamos y problemas de pedido/pago, que
    DEBEN terminar en "escalate"; cualquier otro caso NUNCA debe escalar
    por error. El resto de la escala depende de umbrales que
    `make eval` existe justamente para calibrar — exigirle a un caso
    "debe caer en warn exacto" antes de calibrar sería circular. Escalar
    mal (o no escalar un reclamo real) es, además, el único error de
    enrutamiento con consecuencia real para un cliente.
20. **El juez de la evaluación (`app/evaluation/judge.py`) compara dos
    textos contra una pregunta puntual — nunca le pide al modelo su
    propia confianza ni una nota subjetiva.** Es tool use forzado, mismo
    patrón que la generación (`strict: true`, veredicto
    correct/partial/incorrect + una razón breve), y solo se llama en
    casos con `expected_answer`; un caso `should_escalate` se evalúa por
    `routing_correct`, no por si el mensaje de traspaso "suena bien". El
    modelo juez es configurable aparte del modelo de generación
    (`ANTHROPIC_JUDGE_MODEL`, mismo Haiku 4.5 por defecto) para poder
    calibrar con un juez distinto al que genera si hiciera falta.
21. **`recall_at_k` es `None`, no `0.0`, cuando un caso no tiene
    `expected_doc_slugs`.** Aplica a los casos `should_escalate` y a los
    "fuera de alcance" (preguntas que a propósito no están en la base de
    conocimiento) — ahí "no encontrar ningún documento esperado" es el
    comportamiento correcto, no un fallo de retrieval. `aggregate_metrics`
    promedia solo sobre los casos donde la métrica aplica (mismo criterio
    para `judge_correct_rate`), para que corridas con muchos casos de
    escalamiento no arrastren el promedio hacia abajo de forma artificial.
22. **La migración de las tablas de evaluación se escribió a mano, no con
    el autogenerado de Alembic tal cual salió.** `alembic revision
    --autogenerate` detectó drift preexistente entre los modelos y la
    base (columnas de timestamp sin timezone, la columna generada
    `content_tsv` que no está mapeada en el ORM, índices/constraints que
    ya no coinciden) que no tiene nada que ver con esta fase — se
    descartó ese ruido y la migración final solo crea las tres tablas
    nuevas, mismo criterio que la migración de `review_items` (Fase 3).
    Si una fase futura autogenera una migración, hay que revisar el
    diff con cuidado antes de aplicarlo, no confiar en él a ciegas.
23. **`make eval` es interactivo y pide confirmación antes de gastar
    dinero real** (a menos que se pase `--yes`) — es el único script del
    proyecto que llama a la API de Anthropic de verdad sin que un humano
    esté mirando una demo en vivo; un costo estimado se imprime antes de
    preguntar. El costo real es marginal (~$0.02 USD por los 25 casos de
    `eval/seed.jsonl`, a precios de Haiku 4.5), pero el diseño original
    pide explícitamente no gastar plata sin que quede claro que va a pasar.

## Esquema de base de datos (visión completa; se crea de forma incremental)

- **Conocimiento** (Fase 1): `documents`, `document_versions`, `chunks`
  (`embedding vector(384)`, `content_tsv` generado).
- **Consultas y confianza** (Fase 2): `queries` (todas las señales + decisión),
  `retrieved_chunks` (detalle por consulta, para el "modo transparente").
- **Revisión** (Fase 3): `review_items`, `review_actions`.
- **Evaluación** (Fase 6): `evaluation_cases` (pregunta + respuesta/documentos
  esperados + `should_escalate`), `evaluation_runs` (`config_snapshot` +
  `metrics` agregadas por corrida), `evaluation_results` (un resultado por
  caso, con `recall_at_k` y el veredicto del juez cuando aplica).

## Fases

Ver el plan aprobado. Cada fase termina con: tests corriendo, resumen de lo
hecho, pasos para probarlo manualmente, y un commit en Conventional Commits.
Se espera confirmación antes de pasar a la siguiente fase.

- [x] Fase 0 — Plan y esqueleto
- [x] Fase 1 — Conocimiento y búsqueda
- [x] Fase 2 — Generación y confianza
- [x] Fase 3 — Revisión en el backend
- [x] Fase 4 — Chat del cliente
- [x] Fase 5 — Consola del revisor
- [x] Fase 6 — Evaluación
- [ ] Fase 7 — Pulido (dashboard, CI, README, docs, ADRs, demo)
