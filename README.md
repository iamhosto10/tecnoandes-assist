# TecnoAndes Assist

> Placeholder de la Fase 3. El README de portafolio (problema/solución, capturas,
> diagrama de arquitectura, resultados reales de `make eval`, limitaciones) se
> escribe en la Fase 7, con datos reales en vez de estos de ejemplo.

RAG con sistema de confianza y revisión humana para una tienda de tecnología
colombiana ficticia. Ver [`CLAUDE.md`](CLAUDE.md) para comandos, convenciones y
decisiones de arquitectura.

## Quickstart (estado actual: Fase 3 — revisión en el backend)

```bash
cp .env.example .env        # completa ANTHROPIC_API_KEY y las contraseñas
make up                      # levanta Postgres + backend, sincroniza el venv local
make migrate                 # aplica migraciones
make ingest                  # procesa knowledge_base/*.md a chunks + embeddings
make search q="hay sede en Cali?"   # solo retrieval, sin LLM

curl -X POST localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "cuanto cuesta el iPhone 13"}'

# la cola de revisión y el CRUD de documentos piden el token de .env
curl localhost:8000/review/items -H "Authorization: Bearer change-me-too"
```

Sin `ANTHROPIC_API_KEY` configurada, `/ask` sigue respondiendo `200` (nunca un
error técnico crudo): la decisión cae a `review` con un mensaje de respaldo,
tal como pasaría si la API de Anthropic fallara en producción — y ese caso
queda automáticamente en `/review/items`.

Todavía no hay frontends (Fase 4/5) — por ahora la API es el único punto de
entrada. Docs interactivas en `localhost:8000/docs`.
