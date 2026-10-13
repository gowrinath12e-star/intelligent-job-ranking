"""Streaming top-K selection with heapq and the same sorting tie-break rule."""
from __future__ import annotations

import heapq
from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Integral

from algorithms.sorting import Candidate, RankKey, ranking_key


@dataclass(frozen=True)
class _HeapEntry:
    """Reverse key order so the WORST retained candidate is the heap root.

    Only the numeric/string key and unique input position are compared.
    Arbitrary candidate dictionaries never enter heap comparisons.
    """

    key: RankKey
    position: int
    candidate: Candidate

    def __lt__(self, other: _HeapEntry) -> bool:
        return (self.key, self.position) > (other.key, other.position)


def top_k_candidates(candidates: Iterable[Candidate], k: int) -> list[Candidate]:
    """Keep at most K candidates in a min-heap, then rank ONLY those K.

    Negative K raises ValueError; booleans/non-integers raise TypeError.
    K=0 returns []; K>N returns all N in deterministic rank order.
    Time O(N log K + K log K), conventionally O(N log K) for 1<K<=N;
    K=1 costs O(N). Working heap storage O(min(K,N)), excluding output.
    """
    if isinstance(k, bool) or not isinstance(k, Integral):
        raise TypeError("K must be an integer, not a boolean, string or float.")
    if k < 0:
        raise ValueError("K must be non-negative.")
    if k == 0:
        return []
    heap: list[_HeapEntry] = []
    for position, candidate in enumerate(candidates):
        entry = _HeapEntry(ranking_key(candidate), position, candidate)
        if len(heap) < k:
            heapq.heappush(heap, entry)
        elif (entry.key, entry.position) < (heap[0].key, heap[0].position):
            heapq.heapreplace(heap, entry)
    # A sort of K retained entries is needed for ranked output, not a full N sort.
    return [entry.candidate for entry in sorted(heap, key=lambda item: (item.key, item.position))]
