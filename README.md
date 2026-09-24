# TecnoAndes Assist

> Placeholder de la Fase 1. El README de portafolio (problema/solución, capturas,
> diagrama de arquitectura, resultados reales de `make eval`, limitaciones) se
> escribe en la Fase 7, con datos reales en vez de estos de ejemplo.

RAG con sistema de confianza y revisión humana para una tienda de tecnología
colombiana ficticia. Ver [`CLAUDE.md`](CLAUDE.md) para comandos, convenciones y
decisiones de arquitectura.

## Quickstart (estado actual: Fase 1 — conocimiento y búsqueda)

```bash
cp .env.example .env        # completa ANTHROPIC_API_KEY y las contraseñas
make up                      # levanta Postgres + backend, sincroniza el venv local
make migrate                 # aplica migraciones (extensiones + tablas de conocimiento)
make ingest                  # procesa knowledge_base/*.md a chunks + embeddings
make search q="hay sede en Cali?"   # prueba el retrieval híbrido, sin LLM
```

Todavía no hay LLM ni endpoint `/ask` — eso llega en la Fase 2. `make ingest`
descarga el modelo de embeddings (`intfloat/multilingual-e5-small`, ~470MB) la
primera vez que corre; no necesita ninguna API key.
