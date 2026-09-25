from app.review.gaps import _cluster_questions


class _FakeEmbeddingProvider:
    """Devuelve vectores fijos por texto — no descarga ningún modelo real,
    así este test corre sin internet."""

    dimensions = 3

    def __init__(self, vectors: dict[str, list[float]]):
        self._vectors = vectors

    def embed_query(self, text: str) -> list[float]:
        return self._vectors[text]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vectors[t] for t in texts]

    def count_tokens(self, text: str) -> int:
        return len(text.split())


def test_near_identical_vectors_cluster_together():
    provider = _FakeEmbeddingProvider(
        {
            "venden bicicletas?": [1.0, 0.0, 0.0],
            "tienen bicicletas de montaña?": [0.99, 0.01, 0.0],
            "cual es el horario?": [0.0, 1.0, 0.0],
        }
    )
    questions = ["venden bicicletas?", "tienen bicicletas de montaña?", "cual es el horario?"]

    groups = _cluster_questions(questions, provider, distance_threshold=0.15)

    groups_as_sets = sorted((sorted(g) for g in groups), key=len)
    assert groups_as_sets == [[2], [0, 1]]


def test_distant_vectors_do_not_cluster():
    provider = _FakeEmbeddingProvider(
        {
            "pregunta a": [1.0, 0.0, 0.0],
            "pregunta b": [0.0, 1.0, 0.0],
        }
    )
    questions = ["pregunta a", "pregunta b"]

    groups = _cluster_questions(questions, provider, distance_threshold=0.15)

    assert sorted(sorted(g) for g in groups) == [[0], [1]]


def test_single_question_is_its_own_group():
    provider = _FakeEmbeddingProvider({"sola": [1.0, 0.0, 0.0]})

    groups = _cluster_questions(["sola"], provider, distance_threshold=0.15)

    assert groups == [[0]]


def test_empty_input_returns_no_groups():
    provider = _FakeEmbeddingProvider({})

    assert _cluster_questions([], provider, distance_threshold=0.15) == []


def test_stricter_threshold_can_split_a_looser_group():
    provider = _FakeEmbeddingProvider(
        {
            "a": [1.0, 0.0, 0.0],
            "b": [0.9, 0.436, 0.0],  # a bit further from "a" than in the near-identical test
        }
    )
    questions = ["a", "b"]

    loose = _cluster_questions(questions, provider, distance_threshold=0.3)
    strict = _cluster_questions(questions, provider, distance_threshold=0.05)

    assert len(loose) == 1
    assert len(strict) == 2
