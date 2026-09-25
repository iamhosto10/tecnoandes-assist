"""Integración: `run_evaluation` contra la Postgres real y el retrieval
real (necesita `make up` + `make ingest` ya corridos, igual que
test_ask_endpoint.py) — el cliente de Anthropic se simula (generación Y
juez comparten `client.messages.create`, así que el mock distingue por
qué herramienta se le pidió).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.db.models.evaluation import EvaluationCase, EvaluationResult, EvaluationRun
from app.db.session import SessionLocal
from app.evaluation.runner import run_evaluation
from app.rag.embeddings import get_embedding_provider


def _tool_response(
    tool_name: str, tool_input: dict, input_tokens: int = 100, output_tokens: int = 30
):
    tool_block = SimpleNamespace(type="tool_use", input=tool_input, id="toolu_1", name=tool_name)
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[tool_block], usage=usage, stop_reason="tool_use")


def _mock_client(generation_input: dict, judge_input: dict | None = None):
    client = MagicMock()

    def side_effect(**kwargs):
        tool_name = kwargs["tool_choice"]["name"]
        if tool_name == "submit_answer":
            return _tool_response("submit_answer", generation_input)
        assert judge_input is not None, "no se esperaba una llamada al juez"
        return _tool_response("submit_verdict", judge_input)

    client.messages.create.side_effect = side_effect
    return client


@pytest.fixture
def embedding_provider():
    return get_embedding_provider()


@pytest.fixture
def created_case_ids():
    ids: list[int] = []
    yield ids
    if ids:
        db = SessionLocal()
        db.query(EvaluationResult).filter(EvaluationResult.case_id.in_(ids)).delete(
            synchronize_session=False
        )
        db.query(EvaluationCase).filter(EvaluationCase.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_kb_answerable_case_computes_recall_and_judge_verdict(embedding_provider, created_case_ids):
    client = _mock_client(
        generation_input={
            "answer": "El iPhone 13 cuesta $3.199.000 COP.",
            "support": "full",
            "cited_chunk_ids": [],
            "needs_human": False,
            "needs_human_reason": None,
        },
        judge_input={"verdict": "correct", "reason": "Mismo precio."},
    )

    db = SessionLocal()
    try:
        case = EvaluationCase(
            question="cuanto cuesta el iPhone 13",
            expected_answer="El iPhone 13 cuesta $3.199.000 COP.",
            expected_doc_slugs=["productos-celulares"],
            should_escalate=False,
            category="productos",
            origin="seed",
        )
        db.add(case)
        db.flush()
        created_case_ids.append(case.id)

        run = run_evaluation([case], db, embedding_provider, client)
        db.commit()

        assert len(run.results) == 1
        result = run.results[0]
        assert result.decision == "direct"
        assert result.routing_correct is True
        assert result.recall_at_k == 1.0
        assert result.judge_verdict == "correct"
        assert run.metrics["total_cases"] == 1
    finally:
        run_id = run.id
        db.close()

    cleanup_db = SessionLocal()
    cleanup_db.query(EvaluationRun).filter(EvaluationRun.id == run_id).delete(
        synchronize_session=False
    )
    cleanup_db.commit()
    cleanup_db.close()


def test_should_escalate_case_skips_the_judge(embedding_provider, created_case_ids):
    client = _mock_client(
        generation_input={
            "answer": "Lamento el inconveniente, un asesor te contactará pronto.",
            "support": "full",
            "cited_chunk_ids": [],
            "needs_human": True,
            "needs_human_reason": "Reclamo por cobro duplicado",
        },
        judge_input=None,
    )

    db = SessionLocal()
    try:
        case = EvaluationCase(
            question="me cobraron dos veces por la misma compra",
            expected_answer=None,
            expected_doc_slugs=[],
            should_escalate=True,
            category="reclamo",
            origin="seed",
        )
        db.add(case)
        db.flush()
        created_case_ids.append(case.id)

        run = run_evaluation([case], db, embedding_provider, client)
        db.commit()

        result = run.results[0]
        assert result.decision == "escalate"
        assert result.routing_correct is True
        assert result.recall_at_k is None
        assert result.judge_verdict is None
    finally:
        run_id = run.id
        db.close()

    cleanup_db = SessionLocal()
    cleanup_db.query(EvaluationRun).filter(EvaluationRun.id == run_id).delete(
        synchronize_session=False
    )
    cleanup_db.commit()
    cleanup_db.close()
