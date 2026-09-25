#!/usr/bin/env python
"""CLI: corre `eval/seed.jsonl` contra el pipeline real y persiste los
resultados. A diferencia de `make test`, esto SÍ llama a la API de
Anthropic de verdad (generación + juez) — cuesta dinero real, aunque poco
(ver el estimado que imprime antes de arrancar).

Uso: make eval  (o `uv run python scripts/evaluate.py`)
"""

import json
import sys
from pathlib import Path

from app.core.config import get_settings
from app.db.models.evaluation import EvaluationCase
from app.db.session import session_scope
from app.evaluation.runner import run_evaluation
from app.rag.embeddings import get_embedding_provider
from app.rag.generation import get_anthropic_client

_SEED_PATH = Path(__file__).resolve().parents[2] / "eval" / "seed.jsonl"
# Estimado grosero (no un tracking real de gasto): ~450 tokens de entrada +
# 60 de salida por generación, más ~250/40 por veredicto del juez cuando
# aplica — a precios de Haiku 4.5 da unos ~$0.0008 por caso.
_ESTIMATED_COST_PER_CASE_USD = 0.0008


def _load_cases() -> list[EvaluationCase]:
    if not _SEED_PATH.exists():
        print(f"No existe {_SEED_PATH}")
        raise SystemExit(1)

    cases = []
    with _SEED_PATH.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"{_SEED_PATH}:{line_number}: JSON inválido ({exc})")
                raise SystemExit(1) from exc
            cases.append(
                EvaluationCase(
                    question=row["question"],
                    expected_answer=row.get("expected_answer"),
                    expected_doc_slugs=row.get("expected_doc_slugs", []),
                    should_escalate=row.get("should_escalate", False),
                    category=row.get("category", "sin-categoria"),
                    origin="seed",
                )
            )
    return cases


def main() -> None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        print(
            "ANTHROPIC_API_KEY no está configurada — make eval necesita llamar a la API "
            "de verdad (generación + juez), a diferencia de make test."
        )
        raise SystemExit(1)

    cases = _load_cases()
    estimated_cost = len(cases) * _ESTIMATED_COST_PER_CASE_USD
    print(
        f"Corriendo {len(cases)} casos de {_SEED_PATH.name} "
        f"(~${estimated_cost:.4f} USD estimados)..."
    )
    if "--yes" not in sys.argv:
        answer = input("¿Continuar? [s/N] ").strip().lower()
        if answer not in ("s", "si", "sí", "y", "yes"):
            print("Cancelado.")
            raise SystemExit(0)

    embedding_provider = get_embedding_provider()
    anthropic_client = get_anthropic_client()

    with session_scope() as db:
        for case in cases:
            db.add(case)
        db.flush()

        run = run_evaluation(cases, db, embedding_provider, anthropic_client)
        run_id = run.id
        metrics = run.metrics

    print(f"\nCorrida #{run_id} guardada. Métricas:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
