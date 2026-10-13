"""Honest, repeatable experiments: time actual calls and verify every output.

Generated inputs are isolated from the applicant workspace. No benchmark
numbers are hardcoded, estimated or extrapolated. Each method is warmed,
then timed with perf_counter; algorithm order rotates between repetitions.
"""
from __future__ import annotations

import platform
import random
import statistics
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from numbers import Integral
from time import perf_counter
from typing import Any

import pandas as pd

from algorithms.hashing import build_candidate_index
from algorithms.heap_ranking import top_k_candidates
from algorithms.sorting import SORT_ALGORITHMS, builtin_sort

MAX_BENCHMARK_N = 100000


class BenchmarkVerificationError(RuntimeError):
    """A measured algorithm disagreed with its reference; do not publish results."""


def _validate_repeats(repeats: int) -> None:
    if isinstance(repeats, bool) or not isinstance(repeats, Integral) or not 1 <= repeats <= 31:
        raise ValueError("Repetitions must be an integer between 1 and 31.")


def _measure_methods(methods: Mapping[str, Callable[[], Any]], expected: Any,
                     repeats: int, metadata: Mapping[str, Any]) -> pd.DataFrame:
    """Warm and interleave equivalent methods; verification is outside timing."""
    _validate_repeats(repeats)
    names = list(methods)
    timings: dict[str, list[float]] = defaultdict(list)
    for name in names:
        if methods[name]() != expected:
            raise BenchmarkVerificationError(f"Warm-up verification failed for {name}.")
    for repetition in range(repeats):
        rotation = repetition % len(names)
        for name in names[rotation:] + names[:rotation]:
            started = perf_counter()
            output = methods[name]()
            elapsed_ms = (perf_counter() - started) * 1000.0
            if output != expected:
                raise BenchmarkVerificationError(f"Timed result verification failed for {name}.")
            timings[name].append(elapsed_ms)
    environment = {"measured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "python_version": platform.python_version(), "platform": platform.system()}
    rows = [{**metadata, **environment, "algorithm": name, "median_ms": statistics.median(timings[name]),
             "min_ms": min(timings[name]), "max_ms": max(timings[name]),
             "repetitions": int(repeats), "warmups": 1, "verified": True} for name in names]
    frame = pd.DataFrame(rows)
    first_columns = [column for column in ("algorithm", "n", "k", "returned", "median_ms", "min_ms", "max_ms", "repetitions", "warmups", "verified") if column in frame]
    return frame.loc[:, first_columns + [column for column in frame if column not in first_columns]]


def benchmark_sorting(candidates: Iterable[Mapping[str, Any]], repeats: int = 7,
                      source: str = "Current candidate data", input_order: str = "upload order",
                      seed: int | None = None) -> pd.DataFrame:
    """Measure the three genuine algorithms on identical candidate records."""
    records = list(candidates)
    reference = builtin_sort(records)
    methods = {name: (lambda fn=fn: fn(records)) for name, fn in SORT_ALGORITHMS.items()}
    return _measure_methods(methods, reference, repeats,
                            {"category": "Sorting", "n": len(records), "source": source,
                             "input_order": input_order, "seed": seed})


def benchmark_heap_vs_sort(candidates: Iterable[Mapping[str, Any]], k: int, repeats: int = 7,
                           source: str = "Current candidate data", input_order: str = "upload order",
                           seed: int | None = None) -> pd.DataFrame:
    """Include the same ranked top-K output in both heap and full-sort timings."""
    records = list(candidates)
    # Validate K before slicing: nonintegers and negative values are not accepted.
    top_k_candidates([], k)
    reference = builtin_sort(records)[:k]
    methods = {"Heap top-K": lambda: top_k_candidates(records, k),
               "Full built-in sort + slice": lambda: builtin_sort(records)[:k]}
    return _measure_methods(methods, reference, repeats,
                            {"category": "Top-K", "n": len(records), "k": int(k), "returned": min(len(records), int(k)),
                             "source": source, "input_order": input_order, "seed": seed})


def benchmark_lookup(candidates: Iterable[Mapping[str, Any]], repeats: int = 7,
                     query_count: int = 200, source: str = "Current candidate data",
                     seed: int = 42, input_order: str = "upload order") -> pd.DataFrame:
    """Compare equal batches of dictionary and linear scans, including misses.

    Return batch median ms and derived microseconds/query. Index-build time
    is a separately measured one-off value, never part of lookup latency.
    """
    records = list(candidates)
    if isinstance(query_count, bool) or not isinstance(query_count, Integral) or not 1 <= query_count <= 10000:
        raise ValueError("Query count must be an integer from 1 to 10000.")
    started = perf_counter()
    index = build_candidate_index(records)
    build_ms = (perf_counter() - started) * 1000
    rng = random.Random(seed)
    identifiers = [str(record["candidate_id"]) for record in records]
    queries = [rng.choice(identifiers) if identifiers and position % 5 else f"MISSING-{position}"
               for position in range(query_count)]

    def dict_queries() -> list[str | None]:
        output = []
        for query in queries:
            record = index.lookup(query)
            output.append(str(record["candidate_id"]) if record is not None else None)
        return output

    def linear_queries() -> list[str | None]:
        output = []
        for query in queries:
            record = next((record for record in records if str(record["candidate_id"]) == query), None)
            output.append(str(record["candidate_id"]) if record is not None else None)
        return output

    expected = linear_queries()
    measured = _measure_methods({"Dictionary lookup": dict_queries, "Linear ID scan": linear_queries}, expected, repeats,
                                {"category": "ID lookup", "n": len(records), "query_count": int(query_count),
                                 "index_build_ms": build_ms, "source": source, "input_order": input_order, "seed": int(seed)})
    measured["median_us_per_query"] = measured["median_ms"] * 1000.0 / query_count
    return measured


def generate_benchmark_candidates(n: int, seed: int = 42, input_order: str = "random") -> list[dict[str, Any]]:
    """Seeded numeric ranking inputs for performance experiments, not applicant data.

    Same key/record contract as the real pipeline, but scoring is deliberately
    outside the scope of these algorithm-only experiments. IDs are unique.
    """
    if isinstance(n, bool) or not isinstance(n, Integral) or not 0 <= n <= MAX_BENCHMARK_N:
        raise ValueError(f"N must be an integer from 0 to {MAX_BENCHMARK_N}.")
    if input_order not in {"random", "sorted", "reverse", "many ties"}:
        raise ValueError("Choose random, sorted, reverse, or many ties input order.")
    rng = random.Random(seed)
    records = [{"candidate_id": f"B{position:07d}", "final_score": float(rng.choice([0, 25, 50, 75, 100]))
                if input_order == "many ties" else round(rng.uniform(0, 100), 6),
                "skills": "python; sql" if position % 2 else "python; git", "additional_skills": ""}
               for position in range(n)]
    rng.shuffle(records)
    if input_order == "sorted":
        return builtin_sort(records)
    if input_order == "reverse":
        return list(reversed(builtin_sort(records)))
    return records


def run_generated_benchmarks(sizes: Iterable[int], repeats: int = 5, seed: int = 42,
                             input_order: str = "random", k: int = 25,
                             include_heap: bool = True, include_lookup: bool = True) -> dict[str, pd.DataFrame]:
    """Measure increasing inputs; generate each equivalent dataset only once."""
    selected = sorted(set(sizes))
    if not selected:
        raise ValueError("At least one input size is required.")
    _validate_repeats(repeats)
    sort_tables, heap_tables, lookup_tables = [], [], []
    for size in selected:
        records = generate_benchmark_candidates(size, seed + size, input_order)
        source = "Generated algorithm-only records (not applicant workspace)"
        sort_tables.append(benchmark_sorting(records, repeats, source, input_order, seed + size))
        if include_heap:
            heap_tables.append(benchmark_heap_vs_sort(records, k, repeats, source, input_order, seed + size))
        if include_lookup:
            lookup_tables.append(benchmark_lookup(records, repeats, 100, source, seed + size, input_order))
    return {"sorting": pd.concat(sort_tables, ignore_index=True),
            "heap": pd.concat(heap_tables, ignore_index=True) if heap_tables else pd.DataFrame(),
            "lookup": pd.concat(lookup_tables, ignore_index=True) if lookup_tables else pd.DataFrame()}


def complexity_table() -> pd.DataFrame:
    """Educational complexity, explicitly separate from empirical measurements."""
    rows = [
        ("Merge Sort", "O(N log N)", "O(N log N)", "O(N log N)", "O(N)", "Iterative merge workspace; all keys finite"),
        ("Quick Sort", "O(N log N)", "O(N log N)", "O(N²)", "O(N) copy + O(log N) stack", "Median pivot reduces common pathologies, not worst-case guarantee"),
        ("Python Timsort", "O(N)", "O(N log N)", "O(N log N)", "O(N)", "Adaptive, optimized baseline"),
        ("Heap top-K (1<K≤N)", "O(N + K log K)", "O(N log K + K log K)", "O(N log K + K log K)", "O(K)", "K=0: O(1); K=1: O(N); output ranks only retained K"),
        ("ID dictionary lookup", "O(1)", "O(1)", "O(N)", "O(N) index; O(1) query", "Built-in hash table; collision worst case"),
        ("Inverted skill bucket", "O(1 + M)", "O(1 + M)", "O(T + M)", "O(N + T) index", "Getting bucket average O(1); returning M IDs requires O(M)"),
        ("Skill normalization & match", "O(S + R)", "O(S + R)", "O((S + R)²)", "O(S + R)", "Includes building sets; pathological collision worst case"),
        ("Duplicate-ID detection", "O(N)", "O(N)", "O(N²)", "O(N)", "Hash-group every occurrence, never match only names"),
        ("Linear ID lookup", "O(1)", "O(N)", "O(N)", "O(1)", "Reference scan without a dictionary"),
    ]
    return pd.DataFrame(rows, columns=["Operation", "Best time", "Average time", "Worst time", "Working space", "Notes"])
