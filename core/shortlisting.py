"""Heap-generated review suggestions and separate, explicit recruiter decisions."""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from algorithms.heap_ranking import top_k_candidates
from algorithms.sorting import builtin_sort

REVIEW_STATUSES = ("Automatic", "Shortlisted", "Not shortlisted", "Needs review")


@dataclass(frozen=True)
class ReviewDecision:
    """An auditable review choice; never changes the matching score."""

    status: str = "Automatic"
    note: str = ""

    def __post_init__(self) -> None:
        if self.status not in REVIEW_STATUSES:
            raise ValueError("Unknown review status.")
        if not isinstance(self.note, str):
            raise ValueError("Review note must be text.")
        object.__setattr__(self, "note", self.note.strip())
        if len(self.note) > 2000:
            raise ValueError("Review notes must be at most 2,000 characters.")
        if self.status != "Automatic" and not self.note:
            raise ValueError("Record a review note/reason for a manual status change.")


def update_review_decision(decisions: Mapping[str, ReviewDecision], candidate_id: str, status: str, note: str = "") -> dict[str, ReviewDecision]:
    """Copy-on-update: do not mutate earlier decisions or candidate scores."""
    if not str(candidate_id).strip():
        raise ValueError("A candidate ID is required.")
    updated = dict(decisions)
    updated[str(candidate_id)] = ReviewDecision(status, note)
    return updated


def apply_shortlisting(candidates: Iterable[Mapping[str, Any]], k: int,
                       minimum_score: float | None = None,
                       decisions: Mapping[str, ReviewDecision] | None = None) -> list[dict[str, Any]]:
    """Generate real heap suggestions, then apply overrides without changing scores.

    Known experience below the job minimum is ineligible for automatic
    suggestions. Unknown experience is retained and flagged for human review.
    Candidates without an available numeric score cannot be auto-selected.
    Manual inclusion can exceed K, bypass gates, or include an unscored record;
    this is visible in source/reason fields and always requires a review note.
    Output preserves caller order; get_shortlist provides deterministic order.
    """
    records = list(candidates)
    if minimum_score is not None:
        if isinstance(minimum_score, bool):
            raise ValueError("Minimum score must be a finite number from 0 to 100.")
        try:
            minimum_score = float(minimum_score)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Minimum score must be a finite number from 0 to 100.") from exc
        if not math.isfinite(minimum_score) or not 0 <= minimum_score <= 100:
            raise ValueError("Minimum score must be a finite number from 0 to 100.")
    # Generator keeps heap selection's O(K) working-space benefit.
    qualifying = (candidate for candidate in records
                  if candidate.get("final_score") is not None
                  and candidate.get("automatic_eligible", True)
                  and (minimum_score is None or candidate["final_score"] >= minimum_score))
    suggested_ids = {str(candidate["candidate_id"]) for candidate in top_k_candidates(qualifying, k)}
    reviews = decisions or {}
    result: list[dict[str, Any]] = []
    for candidate in records:
        identifier = str(candidate["candidate_id"])
        suggested = identifier in suggested_ids
        decision = reviews.get(identifier, ReviewDecision())
        if candidate.get("final_score") is None:
            automatic_reason = "Unscored: no observed weighted evidence. Retained for human review."
        elif not candidate.get("automatic_eligible", True):
            automatic_reason = str(candidate.get("eligibility_status", "Does not meet the configured experience minimum"))
        elif minimum_score is not None and candidate["final_score"] < minimum_score:
            automatic_reason = f"Matching score below the {minimum_score:g} threshold."
        elif not suggested:
            automatic_reason = f"Outside the eligible top {k}; record remains visible."
        else:
            automatic_reason = f"Heap top-{k} suggestion after minimum-experience and score gates."
            if candidate.get("score_status") == "Provisional" or "unknown" in str(candidate.get("eligibility_status", "")).lower():
                automatic_reason += " Incomplete information: human review required."
        if decision.status == "Shortlisted":
            selected, source = True, "Manual inclusion"
            reason = "Recruiter override: " + decision.note + " | Automatic assessment: " + automatic_reason
        elif decision.status in {"Not shortlisted", "Needs review"}:
            selected, source = False, "Manual exclusion" if decision.status == "Not shortlisted" else "Review hold"
            reason = "Recruiter decision: " + decision.note + " | Automatic assessment: " + automatic_reason
        else:
            selected, source, reason = suggested, "Automatic suggestion" if suggested else "Not suggested", automatic_reason
        result.append({**dict(candidate), "suggested_shortlist": suggested, "is_shortlisted": selected,
                       "review_status": decision.status, "review_note": decision.note,
                       "shortlist_source": source, "shortlist_reason": reason})
    return result


def get_shortlist(candidates: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Numeric shortlist in rank order, with manual unscored inclusions last."""
    selected = [candidate for candidate in candidates if candidate.get("is_shortlisted", False)]
    scored = builtin_sort(candidate for candidate in selected if candidate.get("final_score") is not None)
    unscored = sorted((candidate for candidate in selected if candidate.get("final_score") is None), key=lambda candidate: str(candidate["candidate_id"]))
    return scored + unscored
