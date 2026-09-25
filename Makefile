.PHONY: up down logs migrate db-shell test lint ingest search eval seed-demo chat review-console

up:
	docker compose up -d --build
	# Los scripts (ingest/search/eval/migrate/test/lint) corren en el host, no
	# en el contenedor, para que el editor tenga autocompletado/type-checking
	# reales. `uv sync` aquí es lo que hace que "make up && make ingest" sea
	# de verdad un solo paso.
	cd backend && uv sync

down:
	docker compose down

logs:
	docker compose logs -f backend

migrate:
	cd backend && uv run alembic upgrade head

db-shell:
	docker compose exec db psql -U $${POSTGRES_USER:-tecnoandes} -d $${POSTGRES_DB:-tecnoandes}

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check .

# Los siguientes targets se activan en las fases que crean sus scripts:
# ingest  -> Fase 1 (backend/scripts/ingest.py)
# search  -> Fase 1 (backend/scripts/search.py), uso: make search q="pregunta"
# eval    -> Fase 6 (backend/scripts/evaluate.py)
# seed-demo -> Fase 7 (backend/scripts/seed_demo.py)

# PYTHONPATH=. porque los scripts corren como `python scripts/x.py` (no como
# módulo empaquetado): sin esto, `import app...` no encuentra el paquete.
ingest:
	cd backend && PYTHONPATH=. uv run python scripts/ingest.py

search:
	cd backend && PYTHONPATH=. uv run python scripts/search.py "$(q)"

eval:
	cd backend && PYTHONPATH=. uv run python scripts/evaluate.py

seed-demo:
	cd backend && PYTHONPATH=. uv run python scripts/seed_demo.py

# Fase 4 — chat del cliente (Next.js). Necesita el backend en localhost:8000.
chat:
	pnpm install
	pnpm --filter @tecnoandes/chat dev

# Fase 5 — consola del revisor (Next.js, localhost:3001). Pide el token de
# REVIEW_CONSOLE_TOKEN (.env en la raíz) para iniciar sesión.
review-console:
	pnpm install
	pnpm --filter @tecnoandes/review-console dev
