"""Practical dictionary/set indexing for validated applicant records.

Built-in hash tables give O(1) average lookup and O(N) worst-case lookup.
No custom hash function or name-based identity matching is used.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from core.normalization import is_missing, normalize_identifier, normalize_skills


@dataclass
class CandidateIndex:
    """Candidate dictionary plus an inverted skill → set-of-candidate-IDs index."""

    candidates_by_id: dict[str, Mapping[str, Any]]
    skill_to_candidate_ids: dict[str, set[str]]

    def lookup(self, candidate_id: str) -> Mapping[str, Any] | None:
        """Average O(1) ID retrieval; None if a well-formed ID is not found."""
        return self.candidates_by_id.get(str(candidate_id).strip())

    def with_skills(self, skills: str | Iterable[str], mode: str = "all") -> set[str]:
        """Combine real inverted-index sets, with explicit empty-filter semantics.

        An empty skill filter returns all candidate IDs. Unknown skills have
        an empty bucket. 'all' intersects; 'any' unions. Returned sets are
        copies, so UI filters cannot accidentally mutate the index.
        """
        if mode not in {"all", "any"}:
            raise ValueError("Skill filter mode must be 'all' or 'any'.")
        requested = normalize_skills(skills)
        if not requested:
            return set(self.candidates_by_id)
        buckets = [self.skill_to_candidate_ids.get(skill, set()) for skill in sorted(requested)]
        if mode == "any":
            return set().union(*buckets)
        smallest = min(buckets, key=len)
        result = set(smallest)
        for bucket in buckets:
            result.intersection_update(bucket)
        return result


def build_candidate_index(candidates: Iterable[Mapping[str, Any]]) -> CandidateIndex:
    """O(N + total skill tokens) average build time, linear stored references."""
    candidates_by_id: dict[str, Mapping[str, Any]] = {}
    skill_to_ids: dict[str, set[str]] = defaultdict(set)
    for candidate in candidates:
        identifier = normalize_identifier(candidate.get("candidate_id"))
        if identifier in candidates_by_id:
            raise ValueError(f"Duplicate candidate ID {identifier}; resolve validation before building the index.")
        candidates_by_id[identifier] = candidate
        skills = normalize_skills(candidate.get("skills")) | normalize_skills(candidate.get("additional_skills"))
        for skill in skills:
            skill_to_ids[skill].add(identifier)
    return CandidateIndex(candidates_by_id, dict(skill_to_ids))


def skill_match(candidate_skills: str | Iterable[str] | None, required_skills: str | Iterable[str] | None) -> tuple[set[str], set[str]]:
    """Return (intersection, required-minus-candidate) using set hashing."""
    candidate_set, required_set = normalize_skills(candidate_skills), normalize_skills(required_skills)
    return set(candidate_set & required_set), set(required_set - candidate_set)


def duplicate_identifier_positions(candidates: Iterable[Mapping[str, Any]], field: str) -> dict[str, list[int]]:
    """Report EVERY position in each duplicate group, ignoring blank optional IDs.

    This operation drives row validation as well as the Hashing Laboratory.
    One hash-based pass: O(N) average time; O(N) additional space.
    """
    groups: dict[str, list[int]] = defaultdict(list)
    for position, candidate in enumerate(candidates):
        value = candidate.get(field)
        if not is_missing(value):
            groups[str(value).strip()].append(position)
    return {identifier: positions for identifier, positions in groups.items() if len(positions) > 1}


def duplicate_application_ids(candidates: Iterable[Mapping[str, Any]]) -> dict[str, list[int]]:
    """Hash-based duplicate application-ID detection (zero-based positions)."""
    return duplicate_identifier_positions(candidates, "application_id")
