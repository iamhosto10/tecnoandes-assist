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
```

Backend fuera de Docker: `cd backend && uv sync && uv run uvicorn app.main:app --reload`.

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

## Esquema de base de datos (visión completa; se crea de forma incremental)

- **Conocimiento** (Fase 1): `documents`, `document_versions`, `chunks`
  (`embedding vector(384)`, `content_tsv` generado).
- **Consultas y confianza** (Fase 2): `queries` (todas las señales + decisión),
  `retrieved_chunks` (detalle por consulta, para el "modo transparente").
- **Revisión** (Fase 3): `review_items`, `review_actions`.
- **Evaluación** (Fase 6): `evaluation_cases`, `evaluation_runs`, `evaluation_results`.

## Fases

Ver el plan aprobado. Cada fase termina con: tests corriendo, resumen de lo
hecho, pasos para probarlo manualmente, y un commit en Conventional Commits.
Se espera confirmación antes de pasar a la siguiente fase.

- [x] Fase 0 — Plan y esqueleto
- [ ] Fase 1 — Conocimiento y búsqueda
- [ ] Fase 2 — Generación y confianza
- [ ] Fase 3 — Revisión en el backend
- [ ] Fase 4 — Chat del cliente
- [ ] Fase 5 — Consola del revisor
- [ ] Fase 6 — Evaluación
- [ ] Fase 7 — Pulido (dashboard, CI, README, docs, ADRs, demo)
