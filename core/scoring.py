"""Transparent job-criteria matching, without an AI model or sensitive features."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from numbers import Real
from typing import Any, Mapping

from core.data_validation import MAX_EXPERIENCE_YEARS
from core.normalization import is_missing, normalize_education, normalize_skills

COMPONENTS = ("required_skills", "experience", "education", "additional_skills")
COMPONENT_LABELS = {
    "required_skills": "Required skills", "experience": "Experience",
    "education": "Education", "additional_skills": "Additional skills",
}
DEFAULT_EDUCATION_RUBRIC = {
    "b.tech computer science": 100.0,
    "b.e. computer science": 100.0,
    "mca": 100.0,
    "m.sc computer science": 95.0,
    "b.sc computer science": 85.0,
    "diploma computer science": 60.0,
}


def _finite_number(value: Any, label: str, lower: float, upper: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label} must be a number.")
    number = float(value)
    if not math.isfinite(number) or not lower <= number <= upper:
        raise ValueError(f"{label} must be finite and between {lower:g} and {upper:g}.")
    return number


@dataclass(frozen=True)
class ScoringWeights:
    """Configured percentages must sum to 100, even for disabled components."""

    required_skills: float = 50.0
    experience: float = 25.0
    education: float = 15.0
    additional_skills: float = 10.0

    def __post_init__(self) -> None:
        for component in COMPONENTS:
            number = _finite_number(getattr(self, component), f"{COMPONENT_LABELS[component]} weight", 0, 100)
            object.__setattr__(self, component, number)
        if not math.isclose(sum(self.as_dict().values()), 100.0, abs_tol=1e-8, rel_tol=0):
            raise ValueError("Configured scoring weights must sum to exactly 100%.")

    def as_dict(self) -> dict[str, float]:
        """Return named percentages for explanations and exports."""
        return {component: getattr(self, component) for component in COMPONENTS}


@dataclass(frozen=True)
class JobRequirements:
    """Job-related configuration; education rubric uses exact normalized labels."""

    title: str = "Python Developer"
    required_skills: frozenset[str] | str = field(default_factory=lambda: frozenset({"python", "sql", "pandas", "git"}))
    additional_skills: frozenset[str] | str = field(default_factory=lambda: frozenset({"django", "fastapi", "docker", "aws"}))
    minimum_experience: float = 2.0
    target_experience: float | None = 5.0
    education_rubric: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_EDUCATION_RUBRIC))
    unmatched_education_score: float = 0.0
    weights: ScoringWeights = field(default_factory=ScoringWeights)
    shortlist_k: int = 10
    minimum_score: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Job title must be non-empty text.")
        object.__setattr__(self, "title", self.title.strip())
        required = normalize_skills(self.required_skills)
        additional = normalize_skills(self.additional_skills)
        if required & additional:
            raise ValueError("Required and additional skill lists must not overlap: " + ", ".join(sorted(required & additional)))
        object.__setattr__(self, "required_skills", required)
        object.__setattr__(self, "additional_skills", additional)
        minimum = _finite_number(self.minimum_experience, "Minimum experience", 0, MAX_EXPERIENCE_YEARS)
        object.__setattr__(self, "minimum_experience", minimum)
        if self.target_experience is not None:
            target = _finite_number(self.target_experience, "Target experience", 0.001, MAX_EXPERIENCE_YEARS)
            if minimum > target:
                raise ValueError("Minimum experience must not exceed target experience.")
            object.__setattr__(self, "target_experience", target)
        if not isinstance(self.education_rubric, Mapping):
            raise ValueError("Education rubric must map text labels to scores.")
        rubric: dict[str, float] = {}
        for label, score in self.education_rubric.items():
            normalized = normalize_education(label)
            if normalized is None or normalized in rubric:
                raise ValueError("Education rubric labels must be non-empty and unique after normalization.")
            rubric[normalized] = _finite_number(score, "Education rubric score", 0, 100)
        object.__setattr__(self, "education_rubric", rubric)
        object.__setattr__(self, "unmatched_education_score", _finite_number(self.unmatched_education_score, "Unmatched education score", 0, 100))
        if not isinstance(self.weights, ScoringWeights):
            raise ValueError("weights must be a validated ScoringWeights object.")
        if isinstance(self.shortlist_k, bool) or not isinstance(self.shortlist_k, int) or self.shortlist_k < 0:
            raise ValueError("Shortlist count must be a non-negative integer.")
        if self.minimum_score is not None:
            object.__setattr__(self, "minimum_score", _finite_number(self.minimum_score, "Minimum score", 0, 100))
        if not any(self.configured_components()[key] and self.weights.as_dict()[key] > 0 for key in COMPONENTS):
            raise ValueError("Configure at least one scoring component with a positive weight.")

    def configured_components(self) -> dict[str, bool]:
        """Missing job components are excluded, not counted as candidate failures."""
        return {"required_skills": bool(self.required_skills), "experience": self.target_experience is not None,
                "education": bool(self.education_rubric), "additional_skills": bool(self.additional_skills)}

    def effective_job_weights(self) -> dict[str, float]:
        """Renormalize only configured, positive-weight components to 100%."""
        raw = self.weights.as_dict()
        active = self.configured_components()
        total = sum(raw[key] for key in COMPONENTS if active[key])
        return {key: (100 * raw[key] / total if active[key] else 0.0) for key in COMPONENTS}


def score_candidate(candidate: Mapping[str, Any], requirements: JobRequirements) -> dict[str, Any]:
    """Return an explained score, preserving the original record without mutation.

    The final score is a weighted SUM, not a product. Unknown experience or
    education is unavailable (None); available candidate components are
    renormalized. Such a score is provisional and not directly comparable
    with complete evidence. With no observed positive-weight components,
    the candidate is explicitly unscored instead of assigned an invented 0.
    """
    skills = normalize_skills(candidate.get("skills")) | normalize_skills(candidate.get("additional_skills"))
    required = requirements.required_skills
    additional = requirements.additional_skills
    matched_required = skills & required
    matched_additional = skills & additional
    experience_raw = candidate.get("experience_years")
    if is_missing(experience_raw):
        experience = None
    else:
        if isinstance(experience_raw, str):
            try:
                experience_raw = float(experience_raw)
            except ValueError as exc:
                raise ValueError("Experience must be numeric; validate the candidate before scoring.") from exc
        experience = _finite_number(experience_raw, "Candidate experience", 0, MAX_EXPERIENCE_YEARS)
    education = normalize_education(candidate.get("education"))
    component_scores: dict[str, float | None] = {
        "required_skills": 100.0 * len(matched_required) / len(required) if required else None,
        "experience": min(100.0, 100.0 * experience / requirements.target_experience)
                      if experience is not None and requirements.target_experience is not None else None,
        "education": requirements.education_rubric.get(education, requirements.unmatched_education_score)
                     if education is not None and requirements.education_rubric else None,
        "additional_skills": 100.0 * len(matched_additional) / len(additional) if additional else None,
    }
    configured = requirements.configured_components()
    configured_weights = requirements.weights.as_dict()
    observed = {key: configured[key] and component_scores[key] is not None and configured_weights[key] > 0 for key in COMPONENTS}
    available_weight = sum(configured_weights[key] for key in COMPONENTS if observed[key])
    effective_weights = {key: 100.0 * configured_weights[key] / available_weight if observed[key] and available_weight else 0.0
                         for key in COMPONENTS}
    contributions = {key: component_scores[key] * effective_weights[key] / 100.0 if observed[key] else None for key in COMPONENTS}
    missing_components = [key for key in COMPONENTS if configured[key] and configured_weights[key] > 0 and component_scores[key] is None]
    notes: list[str] = []
    statuses: dict[str, str] = {}
    for key in COMPONENTS:
        if not configured[key]:
            statuses[key] = "Not configured — excluded"
        elif configured_weights[key] == 0:
            statuses[key] = "Zero weight — excluded"
        elif component_scores[key] is None:
            statuses[key] = "Unknown information — excluded, score provisional"
        else:
            statuses[key] = "Observed"
    if not available_weight:
        final_score = None
        score_status = "Unscored"
        notes.append("No observed positive-weight components. This candidate is retained for review but cannot enter numeric ranking.")
    else:
        final_score = round(sum(value for value in contributions.values() if value is not None), 6)
        final_score = max(0.0, min(100.0, final_score))
        score_status = "Provisional" if missing_components else "Complete"
    if missing_components:
        notes.append("Unknown " + ", ".join(COMPONENT_LABELS[key].lower() for key in missing_components) + "; available weights were renormalized. Human review is required; missing values were not treated as zero.")
    if experience is None and requirements.minimum_experience > 0:
        eligibility = "Experience unknown — review required"
        eligible = final_score is not None
        notes.append("Minimum experience cannot be verified. This record is not silently excluded and may enter the suggested review shortlist.")
    elif experience is not None and experience < requirements.minimum_experience:
        eligibility = "Below minimum experience"
        eligible = False
        notes.append(f"Known experience {experience:g} years is below the configured minimum of {requirements.minimum_experience:g}; excluded from automatic suggestions, still visible and manually reviewable.")
    else:
        eligibility = "Meets minimum experience" if experience is not None else "No minimum experience gate"
        eligible = final_score is not None
    if education is not None and requirements.education_rubric:
        if education in requirements.education_rubric:
            education_reason = f"Exact normalized rubric match: '{education}' → {component_scores['education']:g}/100."
        else:
            education_reason = f"Provided education '{education}' has no rubric entry → configured unmatched-label score {requirements.unmatched_education_score:g}/100."
    elif not requirements.education_rubric:
        education_reason = "No education rubric configured; education is not scored."
    else:
        education_reason = "Education not supplied; score unavailable, not zero."
    notes.append("Matching scores reflect only the configured job criteria, not predicted job performance or an automated hiring decision.")
    return {
        **dict(candidate), "experience_years": experience, "education": education,
        "normalized_skills": sorted(skills),
        "matched_required_skills": sorted(matched_required), "missing_required_skills": sorted(required - skills),
        "matched_additional_skills": sorted(matched_additional), "missing_additional_skills": sorted(additional - skills),
        **{key + "_score": value for key, value in component_scores.items()},
        "component_scores": component_scores, "component_statuses": statuses,
        "configured_weights": configured_weights, "effective_weights": effective_weights,
        "weighted_contributions": contributions, "final_score": final_score,
        "score_status": score_status, "missing_components": missing_components,
        "automatic_eligible": eligible, "eligibility_status": eligibility,
        "education_reason": education_reason, "scoring_notes": notes,
    }
