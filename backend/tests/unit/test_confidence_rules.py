from app.confidence.rules import decide_routing
from app.confidence.signals import ConfidenceSignals

# Los umbrales por defecto (ver .env.example) son low=40, high=75.


def _signals(**overrides) -> ConfidenceSignals:
    defaults = dict(
        retrieval_score=0.9,
        retrieval_margin=0.05,
        support="full",
        needs_human=False,
        citation_valid=True,
        generation_error=None,
    )
    defaults.update(overrides)
    return ConfidenceSignals(**defaults)


def test_rule_1_needs_human_wins_even_with_a_perfect_score():
    result = decide_routing(_signals(needs_human=True), confidence_score=100.0)

    assert result.decision == "escalate"
    assert result.rule == "needs_human"


def test_rule_1_beats_generation_error():
    # needs_human se evalúa aunque también haya un error técnico: el orden
    # de las reglas importa y needs_human va primero.
    result = decide_routing(
        _signals(needs_human=True, generation_error="anthropic_api_error: boom"),
        confidence_score=0.0,
    )

    assert result.decision == "escalate"


def test_rule_2_generation_error_goes_to_review():
    result = decide_routing(
        _signals(generation_error="anthropic_api_error: timeout"), confidence_score=100.0
    )

    assert result.decision == "review"
    assert result.rule == "generation_error"


def test_rule_2_invalid_citation_goes_to_review():
    result = decide_routing(_signals(citation_valid=False), confidence_score=100.0)

    assert result.decision == "review"
    assert result.rule == "invalid_citation"


def test_rule_3_support_none_goes_to_review_regardless_of_score():
    result = decide_routing(_signals(support="none"), confidence_score=100.0)

    assert result.decision == "review"
    assert result.rule == "no_support"


def test_rule_4_support_partial_warns_regardless_of_score():
    result = decide_routing(_signals(support="partial"), confidence_score=100.0)

    assert result.decision == "warn"
    assert result.rule == "partial_support"


def test_rule_5_low_score_goes_to_review():
    result = decide_routing(_signals(support="full"), confidence_score=39.9)

    assert result.decision == "review"
    assert result.rule == "low_score"


def test_rule_6_mid_score_warns():
    result = decide_routing(_signals(support="full"), confidence_score=40.0)

    assert result.decision == "warn"
    assert result.rule == "mid_score"

    result_upper_edge = decide_routing(_signals(support="full"), confidence_score=74.9)
    assert result_upper_edge.decision == "warn"


def test_rule_7_high_score_responds_direct():
    result = decide_routing(_signals(support="full"), confidence_score=75.0)

    assert result.decision == "direct"
    assert result.rule == "high_score"
