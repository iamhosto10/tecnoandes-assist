#!/usr/bin/env python
"""CLI: corre un puñado de preguntas reales contra el pipeline para dejar
la cola de revisión y el dashboard con casos representativos antes de una
demo — un "direct", un "warn", un "review" (sin soporte), un "escalate"
(reclamo) y una pregunta fuera de la base para alimentar las brechas de
conocimiento. Llama a la API de Anthropic de verdad, igual que `make eval`.

Uso: make seed-demo  (o `uv run python scripts/seed_demo.py`)
"""

from app.core.config import get_settings
from app.db.session import session_scope
from app.rag.embeddings import get_embedding_provider
from app.rag.generation import get_anthropic_client
from app.rag.pipeline import persist_ask_result, run_ask_pipeline

# Deliberadamente variados: cada pregunta apunta a una rama distinta del
# enrutamiento (ver app/confidence/rules.py), para que la cola de revisión
# y el dashboard muestren los cuatro casos de un vistazo, no solo "direct".
_DEMO_QUESTIONS = [
    "¿cuánto cuesta el iPhone 13?",
    "¿el Samsung Galaxy S23 viene en color azul?",
    "¿venden patinetas eléctricas?",
    "¿venden bicicletas eléctricas?",
    "¿tienen triciclos para niños?",
    "me cobraron dos veces por la misma compra, quiero que me devuelvan el dinero",
]


def main() -> None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        print(
            "ANTHROPIC_API_KEY no está configurada — seed-demo necesita llamar a la API "
            "de verdad, igual que make eval."
        )
        raise SystemExit(1)

    embedding_provider = get_embedding_provider()
    anthropic_client = get_anthropic_client()

    with session_scope() as db:
        for question in _DEMO_QUESTIONS:
            result = run_ask_pipeline(question, db, embedding_provider, anthropic_client)
            query = persist_ask_result(question, result, db)
            db.flush()
            print(f"[{result.routing.decision:8s}] {question!r} -> query #{query.id}")

    print(f"\n{len(_DEMO_QUESTIONS)} preguntas de demo cargadas.")


if __name__ == "__main__":
    main()
