"""Real sorting implementations must agree with the baseline and not mutate."""
import copy
import random

import pytest

from algorithms.sorting import builtin_sort, merge_sort, quick_sort

ALGORITHMS = [merge_sort, quick_sort, builtin_sort]


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("records", [[], [{"candidate_id": "A", "final_score": 0}]])
def test_empty_single(algorithm, records):
    output = algorithm(records)
    assert output == records
    assert output is not records


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("input_order", ["original", "sorted", "reverse"])
def test_reference_agreement(algorithm, algorithm_candidates, input_order):
    records = algorithm_candidates
    if input_order == "sorted":
        records = builtin_sort(records)
    if input_order == "reverse":
        records = list(reversed(builtin_sort(records)))
    original = copy.deepcopy(records)
    assert algorithm(records) == builtin_sort(records)
    assert records == original


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_tied_scores_lexical_id(algorithm):
    data = [{"candidate_id": identifier, "final_score": 80} for identifier in ["C2", "C10", "C1"]]
    assert [record["candidate_id"] for record in algorithm(data)] == ["C1", "C10", "C2"]


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_identical_keys_do_not_compare_payloads(algorithm):
    records = [{"candidate_id": "A", "final_score": 50, "payload": {"a": []}},
               {"candidate_id": "A", "final_score": 50, "payload": {"b": {}}}]
    assert algorithm(records) == records


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("score", [None, float("nan"), float("inf"), "not numeric", True])
def test_invalid_score_rejected(algorithm, score):
    with pytest.raises(ValueError):
        algorithm([{"candidate_id": "A", "final_score": score}])


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_missing_id_rejected(algorithm):
    with pytest.raises(ValueError):
        algorithm([{"final_score": 10}])


@pytest.mark.parametrize("seed", range(8))
def test_seeded_equivalence(seed):
    rng = random.Random(seed)
    data = [{"candidate_id": f"C{index:05d}", "final_score": rng.choice([-30, 0, 50, 100])} for index in range(500)]
    rng.shuffle(data)
    assert merge_sort(data) == quick_sort(data) == builtin_sort(data)


def test_large_ordered_inputs_avoid_recursion_limit():
    records = [{"candidate_id": f"C{index:05d}", "final_score": float(index)} for index in range(6000)]
    reference = builtin_sort(records)
    assert quick_sort(records) == merge_sort(records) == reference
    assert quick_sort(reference) == reference
    assert quick_sort(reversed(reference)) == reference


def test_iterables_supported(algorithm_candidates):
    assert merge_sort(iter(algorithm_candidates)) == builtin_sort(algorithm_candidates)
    assert quick_sort(iter(algorithm_candidates)) == builtin_sort(algorithm_candidates)
