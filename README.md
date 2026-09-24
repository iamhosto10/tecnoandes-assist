# TecnoAndes Assist

> Placeholder de la Fase 4. El README de portafolio (problema/solución, capturas,
> diagrama de arquitectura, resultados reales de `make eval`, limitaciones) se
> escribe en la Fase 7, con datos reales en vez de estos de ejemplo.

RAG con sistema de confianza y revisión humana para una tienda de tecnología
colombiana ficticia. Ver [`CLAUDE.md`](CLAUDE.md) para comandos, convenciones y
decisiones de arquitectura.

## Quickstart (estado actual: Fase 4 — chat del cliente)

```bash
cp .env.example .env        # completa ANTHROPIC_API_KEY y las contraseñas
make up                      # levanta Postgres + backend, sincroniza el venv local
make migrate                 # aplica migraciones
make ingest                  # procesa knowledge_base/*.md a chunks + embeddings
make search q="hay sede en Cali?"   # solo retrieval, sin LLM
make chat                    # chat del cliente en localhost:3000
```

Sin `ANTHROPIC_API_KEY` configurada, `/ask` sigue respondiendo `200` (nunca un
error técnico crudo): la decisión cae a `review` con un mensaje de respaldo,
tal como pasaría si la API de Anthropic fallara en producción — y ese caso
queda automáticamente en `/review/items`. El chat lo muestra igual, con el
aviso correspondiente.

El chat (`apps/chat`) tiene "modo transparente": un interruptor que muestra,
por cada respuesta, los chunks recuperados con sus puntajes, las señales de
confianza, el cálculo del puntaje y la regla de enrutamiento que se aplicó.

Todavía no hay consola de revisión (Fase 5) — para eso, la API en
`localhost:8000/docs` (protegida con el token de `REVIEW_CONSOLE_TOKEN`).
