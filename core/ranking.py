"""Reusable orchestration: validation → scoring → heap shortlist → sort → hash."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

import pandas as pd

from algorithms.hashing import CandidateIndex, build_candidate_index
from algorithms.sorting import SORT_ALGORITHMS, builtin_sort
from core.data_validation import ValidationResult, validate_applicants
from core.scoring import JobRequirements, score_candidate
from core.shortlisting import ReviewDecision, apply_shortlisting, get_shortlist


@dataclass
class RankingResult:
    """A coherent dataset snapshot; ID index references the explained records."""

    validation: ValidationResult
    requirements: JobRequirements
    ranked_candidates: list[dict[str, Any]]
    index: CandidateIndex
    algorithm: str

    @property
    def scored_candidates(self) -> list[dict[str, Any]]:
        """Numeric records only, never inventing scores for unknown evidence."""
        return [record for record in self.ranked_candidates if record["final_score"] is not None]

    @property
    def shortlist(self) -> list[Mapping[str, Any]]:
        """Final reviewable shortlist, ordered deterministically."""
        return get_shortlist(self.ranked_candidates)

    def source_order_candidates(self) -> list[dict[str, Any]]:
        """The same numeric dataset in upload order for fair lab comparisons."""
        return sorted(self.scored_candidates, key=lambda record: record.get("source_row", 0))


def rank_validated(validation: ValidationResult, requirements: JobRequirements,
                   algorithm: str = "Merge Sort",
                   decisions: Mapping[str, ReviewDecision] | None = None) -> RankingResult:
    """Score once, heap-select actual suggestions, and verify the selected sort."""
    if algorithm not in SORT_ALGORITHMS:
        raise ValueError("Choose Merge Sort, Quick Sort or Python built-in.")
    scored = [score_candidate(record, requirements) for record in validation.records()]
    reviewed = apply_shortlisting(scored, requirements.shortlist_k, requirements.minimum_score, decisions)
    sortable = [record for record in reviewed if record["final_score"] is not None]
    ordered = SORT_ALGORITHMS[algorithm](sortable)
    if [record["candidate_id"] for record in ordered] != [record["candidate_id"] for record in builtin_sort(sortable)]:
        raise RuntimeError(f"{algorithm} failed reference verification; rankings were not published.")
    ranked = [{**record, "rank": rank} for rank, record in enumerate(ordered, start=1)]
    unscored = sorted((record for record in reviewed if record["final_score"] is None), key=lambda record: record["candidate_id"])
    ranked.extend({**record, "rank": None} for record in unscored)
    return RankingResult(validation, requirements, ranked, build_candidate_index(ranked), algorithm)


def rank_applicants(frame: pd.DataFrame, requirements: JobRequirements | None = None,
                    column_mapping: Mapping[str, str] | None = None,
                    algorithm: str = "Merge Sort",
                    decisions: Mapping[str, ReviewDecision] | None = None) -> RankingResult:
    """Public pipeline usable without Streamlit, paid APIs or cloud services."""
    validation = validate_applicants(frame, column_mapping)
    return rank_validated(validation, requirements or JobRequirements(), algorithm, decisions)


def refresh_review(result: RankingResult, decisions: Mapping[str, ReviewDecision]) -> RankingResult:
    """Apply saved decisions without recalculating matching scores or ranks."""
    reviewed = apply_shortlisting(result.ranked_candidates, result.requirements.shortlist_k,
                                 result.requirements.minimum_score, decisions)
    return replace(result, ranked_candidates=reviewed, index=build_candidate_index(reviewed))
