"""Heap selection is bounded, deterministic, and equivalent to a full-sort prefix."""
import copy
import random

import pytest

from algorithms.heap_ranking import top_k_candidates
from algorithms.sorting import builtin_sort


@pytest.mark.parametrize("k", [0, 1, 2, 5, 10])
def test_empty(k):
    assert top_k_candidates([], k) == []


@pytest.mark.parametrize("k", [0, 1, 2, 5, 10])
def test_k_boundaries(algorithm_candidates, k):
    original = copy.deepcopy(algorithm_candidates)
    assert top_k_candidates(algorithm_candidates, k) == builtin_sort(algorithm_candidates)[:k]
    assert algorithm_candidates == original


@pytest.mark.parametrize("k", [-1, -5])
def test_negative_k(k):
    with pytest.raises(ValueError):
        top_k_candidates([], k)


@pytest.mark.parametrize("k", [True, False, 1.5, "2", None])
def test_noninteger_k(k):
    with pytest.raises(TypeError):
        top_k_candidates([], k)


def test_dict_payload_never_compared():
    records = [{"candidate_id": "SAME", "final_score": 90, "payload": {str(index): []}} for index in range(5)]
    assert top_k_candidates(records, 3) == records[:3]


def test_ties_retain_smallest_identifiers():
    records = [{"candidate_id": identifier, "final_score": 100} for identifier in ["Z", "B", "C", "A"]]
    assert [record["candidate_id"] for record in top_k_candidates(records, 2)] == ["A", "B"]


@pytest.mark.parametrize("seed", range(8))
def test_seeded_top_k_equivalence(seed):
    rng = random.Random(seed)
    data = [{"candidate_id": f"C{index:04d}", "final_score": rng.choice([0, 50, 100])} for index in range(150)]
    rng.shuffle(data)
    for k in [0, 1, 3, 20, 150, 151]:
        assert top_k_candidates(iter(data), k) == builtin_sort(data)[:k]


def test_zero_k_does_not_consume_stream():
    def stream():
        raise AssertionError("K=0 should return before consuming input")
        yield {}
    assert top_k_candidates(stream(), 0) == []
