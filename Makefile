.PHONY: up down logs migrate db-shell test lint ingest search eval seed-demo

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

ingest:
	cd backend && uv run python scripts/ingest.py

search:
	cd backend && uv run python scripts/search.py "$(q)"

eval:
	cd backend && uv run python scripts/evaluate.py

seed-demo:
	cd backend && uv run python scripts/seed_demo.py
