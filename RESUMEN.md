# Resumen del proyecto — TecnoAndes Assist

Documento personal, de una sola pasada: qué se construyó, por qué se tomó
cada decisión grande, cómo se hizo, y cómo correrlo/probarlo/aprender de
él. El [`README.md`](README.md) es la versión "de portafolio" (para que
otra persona lo lea); este es el resumen para ti, más denso y directo.

## Qué es

Un asistente de atención al cliente tipo RAG para una tienda de tecnología
colombiana ficticia (TecnoAndes), con dos ideas centrales que lo separan
de una demo de RAG típica:

1. **El sistema no confía ciegamente en el modelo.** Calcula su propio
   puntaje de confianza (0–100) a partir de señales medibles — qué tan
   bien encajó la búsqueda, si el modelo mismo reporta que su respuesta
   está respaldada por el contexto, si citó algo real — y con eso decide
   si contesta directo, con advertencia, o manda el caso a un humano.
2. **Cuando manda a un humano, hay un lugar real donde ese humano trabaja.**
   La consola de revisión no es una tabla de logs: tiene cola con filtros
   y atajos de teclado, seis acciones de resolución, edición de la base
   de conocimiento con historial de versiones, "brechas de conocimiento"
   (qué documentos faltan, detectado automáticamente), y un dashboard.

## Por qué se construyó así (las decisiones grandes)

Cada una tiene su ADR completo en [`docs/adr/`](docs/adr/) con el
trade-off explícito; acá el resumen de una línea de las 5 más importantes:

- **Retrieval híbrido en SQL crudo + RRF en Python**
  ([ADR 0001](docs/adr/0001-hybrid-retrieval-raw-sql-rrf.md)): vectorial y
  texto completo son dos consultas SQL simples y separadas, fusionadas por
  *posición* (no por puntaje crudo) porque sus escalas no son comparables.
- **Puntaje ponderado + compuertas duras separadas**
  ([ADR 0002](docs/adr/0002-confidence-scoring-hard-gates.md)): un
  reclamo o una cita inventada nunca pueden "colarse" a una respuesta
  directa solo porque el resto del puntaje dio alto — se filtran ANTES,
  con reglas fijas, no con más peso ponderado.
- **Sin tabla de auditoría genérica**
  ([ADR 0003](docs/adr/0003-audit-trail-without-generic-log-table.md)):
  la trazabilidad sale de tres tablas de dominio (`queries`,
  `document_versions`, `review_actions`), cada una tipada y fácil de
  consultar, en vez de un `audit_log` polimórfico con un jsonb genérico.
- **LLM-as-judge sin autoconfianza**
  ([ADR 0004](docs/adr/0004-llm-as-judge-evaluation.md)): para medir si
  el pipeline "contestó bien" en `make eval`, un segundo modelo compara
  la respuesta real contra la esperada — nunca se le pregunta a ningún
  modelo "qué tan seguro estás", ni al que genera ni al juez.
- **Auth de un solo token para la consola**
  ([ADR 0005](docs/adr/0005-single-token-auth-review-console.md)):
  simplificación deliberada para una demo con un revisor, documentada
  explícitamente como no apta para producción.

Otras ~20 decisiones más puntuales (por qué FastAPI síncrono, por qué
`torch` fijado a CPU-only, el bug real de `chunk_index` en la ingesta,
por qué Base UI rompe el hábito de Radix, etc.) están en
[`CLAUDE.md`](CLAUDE.md#decisiones-clave-con-su-trade-off) — vale la pena
leerlas porque varias vienen de bugs reales encontrados corriendo el
código, no de teoría.

## Cómo se construyó (las 8 fases)

Se hizo fase por fase, cada una con su propio commit y verificación antes
de avanzar — nunca "todo junto":

| Fase | Qué se agregó |
|---|---|
| 0 | Esqueleto: Docker Compose (Postgres+pgvector), FastAPI mínimo, `uv`, estructura de carpetas |
| 1 | Ingesta idempotente + chunking + embeddings E5 + retrieval híbrido |
| 2 | Generación con Claude (tool use forzado) + sistema de confianza + enrutamiento |
| 3 | Cola de revisión, acciones del revisor, versionado de documentos, re-test |
| 4 | Chat del cliente (Next.js) con "modo transparente" |
| 5 | Consola de revisión (Next.js) — la app más grande del proyecto |
| 6 | Harness de evaluación (`make eval`) con LLM-as-judge |
| 7 | Dashboard, CI, README de portafolio, ADRs, guion de demo |

## Cómo correrlo

```bash
cp .env.example .env        # completa ANTHROPIC_API_KEY (real, para generación/juez/demo)
make up                      # Postgres + backend en Docker, sincroniza el venv local
make migrate                 # aplica migraciones de Alembic
make ingest                  # procesa knowledge_base/*.md a chunks + embeddings
make chat                    # localhost:3000 — chat del cliente
make review-console          # localhost:3001 — consola (token: REVIEW_CONSOLE_TOKEN en .env)
```

Sin `ANTHROPIC_API_KEY` real, el chat igual funciona: cada pregunta cae en
`review` con un mensaje de respaldo (así se comporta el sistema si la API
de Anthropic fallara en producción). Para ver el pipeline completo de
verdad (respuestas directas, advertencias, escalamientos reales) hace
falta la key.

## Cómo probarlo

**Automatizado** (no gasta dinero, no necesita API key real):

```bash
make lint    # ruff, backend
make test    # pytest, backend — 85 tests, el cliente de Anthropic se simula
```

Frontend (desde la raíz del repo):
```bash
pnpm --filter @tecnoandes/chat exec tsc --noEmit
pnpm --filter @tecnoandes/review-console exec tsc --noEmit
pnpm --filter @tecnoandes/chat run lint
pnpm --filter @tecnoandes/review-console run lint
```

Todo esto también corre solo en GitHub Actions
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) en cada push/PR.

**Manual, con API key real** — sigue [`docs/DEMO.md`](docs/DEMO.md)
(~6 minutos, guion paso a paso): una respuesta directa, una zona gris, un
caso sin soporte y un reclamo que escala, resolver un caso desde la
consola creando un documento nuevo, ver ese documento ya funcionando en
el chat, y el dashboard con los números reales de esa sesión.

**Con datos de verdad para la demo:**
```bash
make seed-demo   # carga preguntas variadas en la cola (necesita API key real)
make eval        # corre eval/seed.jsonl y mide recall@k, enrutamiento y veredicto del juez
```

Ninguno de los dos se corrió en este entorno (no había una API key real
configurada) — los números que verías en el dashboard después de
correrlos son reales de tu propia ejecución, no vienen precalculados en
ningún lado del repo (a propósito: pediste explícitamente no fabricar
métricas).

## Qué aprender de esto

[`docs/APRENDIZAJE.md`](docs/APRENDIZAJE.md) tiene el mapa completo
concepto → archivo exacto (chunking consciente de estructura, embeddings
con prefijos de rol, RRF, tool use forzado, sistema de confianza
explicable, calibración con datos, LLM-as-judge, human-in-the-loop de
punta a punta). Si solo vas a leer tres archivos para entender la
columna vertebral técnica del proyecto:

1. **`backend/app/rag/pipeline.py`** — el pipeline completo de una
   pregunta en ~80 líneas: retrieval → generación → señales → puntaje →
   decisión. Todo lo demás son detalles de cada paso.
2. **`backend/app/confidence/rules.py`** — las 7 reglas de enrutamiento,
   en orden, con el comentario de por qué el orden importa.
3. **`backend/app/evaluation/runner.py`** — cómo se mide si el sistema
   completo "funciona bien", no solo si cada pieza pasa sus tests
   unitarios por separado.

Tu propio registro de aprendizaje de proyectos con Claude Code (por si
quieres actualizarlo con lo de este proyecto) está en
`~/.claude/EXPERIENCIA_PYTHON_RAG.md`.
