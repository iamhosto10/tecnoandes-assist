from app.rag.retrieval import reciprocal_rank_fusion


def test_item_ranked_first_in_both_lists_wins():
    vector_ranked = [1, 2, 3]
    fulltext_ranked = [1, 3, 2]

    scores = reciprocal_rank_fusion([vector_ranked, fulltext_ranked], k=60)

    assert max(scores, key=scores.get) == 1


def test_score_matches_the_1_over_k_plus_rank_formula():
    scores = reciprocal_rank_fusion([[10, 20, 30]], k=60)

    assert scores[10] == 1 / 61  # rank 1
    assert scores[20] == 1 / 62  # rank 2
    assert scores[30] == 1 / 63  # rank 3


def test_item_only_in_one_list_only_gets_that_lists_contribution():
    vector_ranked = [1, 2]
    fulltext_ranked = [2, 3]

    scores = reciprocal_rank_fusion([vector_ranked, fulltext_ranked], k=60)

    assert scores[1] == 1 / 61  # solo aparece en vector_ranked, rank 1
    assert scores[3] == 1 / 62  # solo aparece en fulltext_ranked, rank 2
    assert scores[2] == 1 / 62 + 1 / 61  # aparece en ambas: rank 2 y rank 1


def test_agreement_between_methods_beats_a_single_top_rank():
    # 100 es #1 pero solo en la búsqueda vectorial; 999 es #2 en AMBAS.
    # RRF premia la coincidencia entre métodos por encima de un golpe de
    # suerte en uno solo, así que 999 debería ganar.
    vector_ranked = [100, 999]
    fulltext_ranked = [42, 999]

    scores = reciprocal_rank_fusion([vector_ranked, fulltext_ranked], k=60)

    assert scores[999] > scores[100]


def test_empty_input_returns_empty_scores():
    assert reciprocal_rank_fusion([]) == {}
    assert reciprocal_rank_fusion([[], []]) == {}
