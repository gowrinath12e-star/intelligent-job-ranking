"""Genuine Merge/Quick Sort and a common deterministic ranking contract.

Order: descending finite final_score, ascending string candidate_id. Ties
with the same ID retain source order. Functions return a new list and never
modify candidate dictionaries or the caller's list.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any, Callable

Candidate = Mapping[str, Any]
RankKey = tuple[float, str]


def ranking_key(candidate: Candidate) -> RankKey:
    """Lower keys rank better; accepts negative scores for algorithm exercises."""
    score = candidate.get("final_score")
    if isinstance(score, bool):
        raise ValueError("final_score must be a finite number, not a boolean.")
    try:
        numeric_score = float(score)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("final_score must be a finite number.") from exc
    if not math.isfinite(numeric_score):
        raise ValueError("final_score must be a finite number.")
    if "candidate_id" not in candidate or candidate["candidate_id"] is None or not str(candidate["candidate_id"]).strip():
        raise ValueError("A non-empty candidate_id is required for deterministic tie-breaking.")
    return (-numeric_score, str(candidate["candidate_id"]))


def merge_sort(candidates: Iterable[Candidate]) -> list[Candidate]:
    """Bottom-up divide-and-conquer Merge Sort, with O(n) merge workspace.

    Singleton runs are repeatedly merged into runs of length 2, 4, 8, ... .
    This is genuine Merge Sort, expressed iteratively to avoid recursion.
    Best/average/worst time O(n log n); total additional storage O(n).
    """
    records = list(candidates)
    size = len(records)
    entries = [(ranking_key(record), record) for record in records]
    if size < 2:
        return records
    workspace: list[Any] = [None] * size
    width = 1
    while width < size:
        for start in range(0, size, 2 * width):
            middle = min(start + width, size)
            end = min(start + 2 * width, size)
            left, right, destination = start, middle, start
            while left < middle and right < end:
                # <= preserves source order for identical score+ID keys.
                if entries[left][0] <= entries[right][0]:
                    workspace[destination] = entries[left]
                    left += 1
                else:
                    workspace[destination] = entries[right]
                    right += 1
                destination += 1
            while left < middle:
                workspace[destination] = entries[left]
                left += 1
                destination += 1
            while right < end:
                workspace[destination] = entries[right]
                right += 1
                destination += 1
        entries, workspace = workspace, entries
        width *= 2
    return [entry[1] for entry in entries]


def _median_of_three(a: tuple[float, str, int], b: tuple[float, str, int], c: tuple[float, str, int]) -> tuple[float, str, int]:
    """Find a median pivot using comparisons, not a sorting-library shortcut."""
    if a < b:
        return b if b < c else (c if a < c else a)
    return a if a < c else (c if b < c else b)


def quick_sort(candidates: Iterable[Candidate]) -> list[Candidate]:
    """Iterative median-of-three, three-way partition Quick Sort.

    Each partition divides keys into <pivot, =pivot and >pivot regions.
    Smaller partitions are processed first, keeping pending stack O(log n).
    Median pivots reduce common sorted-input problems, but worst-case time
    is STILL O(n²); best/average O(n log n). The copied/keyed records occupy
    O(n) space. Original input positions decorate keys to preserve stability
    even if a standalone caller repeats the same candidate ID and score.
    """
    entries = [(ranking_key(record) + (position,), record) for position, record in enumerate(candidates)]
    if len(entries) < 2:
        return [entry[1] for entry in entries]
    pending: list[tuple[int, int]] = [(0, len(entries) - 1)]
    while pending:
        lower, upper = pending.pop()
        while lower < upper:
            midpoint = lower + (upper - lower) // 2
            pivot = _median_of_three(entries[lower][0], entries[midpoint][0], entries[upper][0])
            smaller, current, greater = lower, lower, upper
            while current <= greater:
                key = entries[current][0]
                if key < pivot:
                    entries[smaller], entries[current] = entries[current], entries[smaller]
                    smaller += 1
                    current += 1
                elif key > pivot:
                    entries[current], entries[greater] = entries[greater], entries[current]
                    greater -= 1
                else:
                    current += 1
            left = (lower, smaller - 1)
            right = (greater + 1, upper)
            left_size = left[1] - left[0] + 1
            right_size = right[1] - right[0] + 1
            if left_size < right_size:
                if right_size > 1:
                    pending.append(right)
                lower, upper = left
            else:
                if left_size > 1:
                    pending.append(left)
                lower, upper = right
    return [entry[1] for entry in entries]


def builtin_sort(candidates: Iterable[Candidate]) -> list[Candidate]:
    """Python Timsort reference; adaptive O(n) best, O(n log n) worst/average."""
    return sorted(candidates, key=ranking_key)


SORT_ALGORITHMS: dict[str, Callable[[Iterable[Candidate]], list[Candidate]]] = {
    "Merge Sort": merge_sort, "Quick Sort": quick_sort, "Python built-in": builtin_sort,
}
