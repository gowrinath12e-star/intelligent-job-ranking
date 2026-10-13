"""Benchmarks must execute, verify, and expose measured statistics."""
import pytest

from utils.performance import benchmark_heap_vs_sort, benchmark_lookup, benchmark_sorting, generate_benchmark_candidates, run_generated_benchmarks


def test_sorting_actual_measurements():
    data = generate_benchmark_candidates(40)
    result = benchmark_sorting(data, repeats=3)
    assert len(result) == 3
    assert result.verified.all()
    assert (result.median_ms > 0).all()
    assert (result.min_ms <= result.median_ms).all()
    assert (result.median_ms <= result.max_ms).all()
    assert set(result.repetitions) == {3}


@pytest.mark.parametrize("k", [0, 1, 10, 100])
def test_heap_benchmark(k):
    result = benchmark_heap_vs_sort(generate_benchmark_candidates(40), k, repeats=2)
    assert result.verified.all()
    assert set(result.returned) == {min(40, k)}


def test_lookup_batch_measurements():
    result = benchmark_lookup(generate_benchmark_candidates(40), repeats=3, query_count=20)
    assert result.verified.all()
    assert (result.index_build_ms > 0).all()
    assert result.median_us_per_query.tolist() == pytest.approx((result.median_ms * 1000 / 20).tolist())


@pytest.mark.parametrize("order", ["random", "sorted", "reverse", "many ties"])
def test_generated_repeatable_input(order):
    assert generate_benchmark_candidates(60, 17, order) == generate_benchmark_candidates(60, 17, order)


def test_increasing_suite_executes_all():
    tables = run_generated_benchmarks([10, 30], repeats=2, k=5)
    assert len(tables["sorting"]) == 6
    assert len(tables["heap"]) == len(tables["lookup"]) == 4
    assert all(table.verified.all() for table in tables.values())


def test_invalid_parameters():
    with pytest.raises(ValueError):
        benchmark_sorting([], repeats=0)
    with pytest.raises(ValueError):
        run_generated_benchmarks([])
    with pytest.raises(ValueError):
        generate_benchmark_candidates(-1)
