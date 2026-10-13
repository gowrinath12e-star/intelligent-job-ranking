"""End-to-end service tests use real sample input and manual-review refreshes."""
from dataclasses import replace
from pathlib import Path

import pandas as pd

from core.data_loader import load_applicants
from core.ranking import rank_applicants, refresh_review
from core.scoring import JobRequirements, ScoringWeights
from core.shortlisting import ReviewDecision


def test_three_algorithms_same_pipeline(applicant_frame):
    results = [rank_applicants(applicant_frame, algorithm=name) for name in ["Merge Sort", "Quick Sort", "Python built-in"]]
    identifiers = [[record["candidate_id"] for record in result.ranked_candidates] for result in results]
    assert identifiers[0] == identifiers[1] == identifiers[2]


def test_actual_sample_pipeline():
    path = Path(__file__).resolve().parents[1] / "data" / "sample_applicants.csv"
    result = rank_applicants(load_applicants(path))
    assert len(result.ranked_candidates) == 72
    assert len(result.shortlist) == 10
    assert result.index.lookup("C004")["score_status"] == "Provisional"
    assert result.index.with_skills("python; sql")
    assert result.scored_candidates[0]["final_score"] == 100


def test_review_refresh_preserves_scores_and_rank(applicant_frame):
    result = rank_applicants(applicant_frame, replace(JobRequirements(), shortlist_k=1))
    before = [(record["candidate_id"], record["rank"], record["final_score"]) for record in result.ranked_candidates]
    updated = refresh_review(result, {"C002": ReviewDecision("Shortlisted", "Reviewed project evidence")})
    assert [(record["candidate_id"], record["rank"], record["final_score"]) for record in updated.ranked_candidates] == before
    assert len(updated.shortlist) == 2
    assert result.index.lookup("C002")["review_status"] == "Automatic"


def test_unscored_applicants_are_visible(candidate):
    job = JobRequirements(required_skills="", additional_skills="", education_rubric={},
                          weights=ScoringWeights(0, 100, 0, 0))
    result = rank_applicants(pd.DataFrame([{**candidate, "experience_years": None}]), job)
    assert len(result.ranked_candidates) == 1
    assert result.ranked_candidates[0]["rank"] is None
    assert result.scored_candidates == []
    assert result.shortlist == []


def test_empty_pipeline():
    result = rank_applicants(pd.DataFrame(columns=["candidate_id", "name", "skills"]))
    assert result.ranked_candidates == []
    assert result.shortlist == []
    assert result.index.candidates_by_id == {}
