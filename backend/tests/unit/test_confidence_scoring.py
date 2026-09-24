from app.confidence.scoring import compute_confidence_score
from app.confidence.signals import ConfidenceSignals

# Los tests asumen los valores por defecto de Settings (ver core/config.py /
# .env.example): pesos 0.5 / 0.15 / 0.35, retrieval floor=0.75 ceiling=0.90,
# margin ceiling=0.05. Ambas fuentes están sincronizadas a propósito.


def _signals(**overrides) -> ConfidenceSignals:
    defaults = dict(
        retrieval_score=0.75,  # = floor -> normalizado a 0
        retrieval_margin=0.0,
        support="full",
        needs_human=False,
        citation_valid=True,
        generation_error=None,
    )
    defaults.update(overrides)
    return ConfidenceSignals(**defaults)


def test_retrieval_score_at_floor_contributes_nothing():
    low = compute_confidence_score(_signals(retrieval_score=0.75, support=None))
    lower_than_floor = compute_confidence_score(_signals(retrieval_score=0.5, support=None))

    assert low == lower_than_floor == 0.0


def test_retrieval_score_at_or_above_ceiling_is_clamped_to_full_contribution():
    at_ceiling = compute_confidence_score(_signals(retrieval_score=0.90, support=None))
    above_ceiling = compute_confidence_score(_signals(retrieval_score=0.99, support=None))

    # peso de retrieval_score = 0.5 -> contribución máxima = 50 puntos
    assert at_ceiling == above_ceiling == 50.0


def test_support_full_partial_none_ordering():
    full = compute_confidence_score(_signals(support="full"))
    partial = compute_confidence_score(_signals(support="partial"))
    none = compute_confidence_score(_signals(support="none"))

    assert full > partial > none


def test_missing_support_scores_like_none():
    none_score = compute_confidence_score(_signals(support="none"))
    missing_score = compute_confidence_score(_signals(support=None))

    assert none_score == missing_score


def test_matches_manual_weighted_sum_for_a_known_case():
    # retrieval_score=0.825 está a mitad de camino entre floor (0.75) y
    # ceiling (0.90) -> normalizado 0.5. margin=0.025 está a mitad de su
    # ceiling (0.05) -> normalizado 0.5. support="full" -> 1.0.
    score = compute_confidence_score(
        _signals(retrieval_score=0.825, retrieval_margin=0.025, support="full")
    )

    expected = (0.5 * 0.5 + 0.15 * 0.5 + 0.35 * 1.0) * 100
    assert score == round(expected, 2)


def test_score_is_between_0_and_100():
    worst = compute_confidence_score(
        _signals(retrieval_score=0.0, retrieval_margin=0.0, support="none")
    )
    best = compute_confidence_score(
        _signals(retrieval_score=1.0, retrieval_margin=1.0, support="full")
    )

    assert worst == 0.0
    assert best == 100.0
