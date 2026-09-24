# TecnoAndes Assist

> Placeholder de la Fase 0. El README de portafolio (problema/solución, capturas,
> diagrama de arquitectura, resultados reales de `make eval`, limitaciones) se
> escribe en la Fase 7, con datos reales en vez de estos de ejemplo.

RAG con sistema de confianza y revisión humana para una tienda de tecnología
colombiana ficticia. Ver [`CLAUDE.md`](CLAUDE.md) para comandos, convenciones y
decisiones de arquitectura.

## Quickstart (estado actual: Fase 0 — esqueleto)

```bash
cp .env.example .env        # completa ANTHROPIC_API_KEY y las contraseñas
make up                      # levanta Postgres + backend
make migrate                 # aplica migraciones (extensiones pgvector/unaccent)
curl localhost:8000/health   # {"status": "ok"}
```

Este comando de un solo paso (`make up && make ingest`) queda completo al
terminar la Fase 1, cuando exista `knowledge_base/` con contenido y el script
de ingesta.
