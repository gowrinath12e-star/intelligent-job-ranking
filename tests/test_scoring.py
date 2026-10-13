"""Transparent scoring, explicit unknown evidence and defensible configuration."""
import copy
from dataclasses import replace

import pytest

from core.scoring import JobRequirements, ScoringWeights, score_candidate


def test_all_required_matched(candidate):
    result = score_candidate(candidate, JobRequirements())
    assert result["required_skills_score"] == 100
    assert result["final_score"] == 100
    assert result["score_status"] == "Complete"
    assert result["missing_required_skills"] == []
    assert sum(result["effective_weights"].values()) == 100


@pytest.mark.parametrize("skills,expected", [("java; excel", 0), ("python; sql", 50), ("python", 25)])
def test_none_partial_matches(candidate, skills, expected):
    candidate.update(skills=skills, additional_skills="")
    assert score_candidate(candidate, JobRequirements())["required_skills_score"] == expected


def test_skill_normalization_duplicates(candidate):
    candidate["skills"] = " python , PYTHON;sql|PANDAS\ngit "
    assert score_candidate(candidate, JobRequirements())["required_skills_score"] == 100


def test_skills_in_either_column_count(candidate):
    candidate.update(skills="python; sql", additional_skills="pandas; git; django")
    result = score_candidate(candidate, JobRequirements())
    assert result["required_skills_score"] == 100
    assert result["additional_skills_score"] == 25


def test_missing_experience_not_zero(candidate):
    candidate["experience_years"] = None
    result = score_candidate(candidate, JobRequirements())
    assert result["experience_score"] is None
    assert result["experience_years"] is None
    assert result["effective_weights"]["experience"] == 0
    assert result["effective_weights"]["required_skills"] == pytest.approx(50 / 75 * 100)
    assert result["final_score"] == 100
    assert result["score_status"] == "Provisional"
    assert result["automatic_eligible"] is True
    assert "unknown" in result["eligibility_status"].lower()


def test_missing_education_not_zero(candidate):
    candidate["education"] = ""
    result = score_candidate(candidate, JobRequirements())
    assert result["education_score"] is None
    assert result["effective_weights"]["education"] == 0
    assert result["score_status"] == "Provisional"
    assert "not zero" in result["education_reason"]


def test_missing_optional_job_components(candidate):
    job = replace(JobRequirements(), additional_skills="", education_rubric={}, target_experience=None)
    result = score_candidate(candidate, job)
    assert result["final_score"] == 100
    assert result["effective_weights"]["required_skills"] == 100
    assert result["score_status"] == "Complete"
    assert result["additional_skills_score"] is None
    assert result["education_score"] is None


def test_no_required_component(candidate):
    job = replace(JobRequirements(), required_skills="")
    result = score_candidate(candidate, job)
    assert result["required_skills_score"] is None
    assert result["effective_weights"]["required_skills"] == 0
    assert result["final_score"] == 100


def test_no_observed_weighted_information(candidate):
    job = JobRequirements(required_skills="", additional_skills="", education_rubric={}, minimum_experience=0,
                          weights=ScoringWeights(0, 100, 0, 0))
    result = score_candidate({**candidate, "experience_years": None}, job)
    assert result["final_score"] is None
    assert result["score_status"] == "Unscored"
    assert not result["automatic_eligible"]


def test_known_zero_experience_is_observed(candidate):
    result = score_candidate({**candidate, "experience_years": 0}, JobRequirements())
    assert result["experience_score"] == 0
    assert result["effective_weights"]["experience"] == 25
    assert result["score_status"] == "Complete"
    assert not result["automatic_eligible"]


@pytest.mark.parametrize("years,score", [(1.0, 20), (5.0, 100), (10.0, 100)])
def test_experience_normalization_cap(candidate, years, score):
    assert score_candidate({**candidate, "experience_years": years}, JobRequirements())["experience_score"] == score


def test_education_configurable_exact_rubric(candidate):
    job = replace(JobRequirements(), education_rubric={"custom qualification": 70}, unmatched_education_score=20)
    result = score_candidate(candidate, job)
    assert result["education_score"] == 20
    assert "no rubric entry" in result["education_reason"]
    result = score_candidate({**candidate, "education": " Custom Qualification "}, job)
    assert result["education_score"] == 70
    assert "Exact" in result["education_reason"]


@pytest.mark.parametrize("weights", [(-1, 26, 65, 10), (101, 0, 0, -1), (float("nan"), 25, 15, 10), (True, 25, 15, 59), ("50", 25, 15, 10)])
def test_invalid_weights(weights):
    with pytest.raises(ValueError):
        ScoringWeights(*weights)


@pytest.mark.parametrize("weights", [(50, 25, 15, 5), (0, 0, 0, 0), (50, 30, 20, 10)])
def test_weights_must_sum_100(weights):
    with pytest.raises(ValueError, match="100"):
        ScoringWeights(*weights)


@pytest.mark.parametrize("kwargs", [
    {"title": " "}, {"minimum_experience": -1}, {"target_experience": 0}, {"minimum_experience": 6, "target_experience": 5},
    {"shortlist_k": -1}, {"shortlist_k": True}, {"shortlist_k": 1.5}, {"minimum_score": 101},
    {"additional_skills": "python"}, {"education_rubric": {"mca": 150}}, {"education_rubric": {"MCA": 100, "mca": 80}},
    {"unmatched_education_score": -1}, {"required_skills": "", "additional_skills": "", "target_experience": None, "education_rubric": {}},
])
def test_invalid_job_configuration(kwargs):
    with pytest.raises(ValueError):
        replace(JobRequirements(), **kwargs)


def test_correct_score_explanation(candidate):
    record = {**candidate, "skills": "python; sql", "additional_skills": "docker", "experience_years": 2,
              "education": "B.Sc Computer Science"}
    result = score_candidate(record, JobRequirements())
    assert result["matched_required_skills"] == ["python", "sql"]
    assert result["missing_required_skills"] == ["git", "pandas"]
    assert result["final_score"] == pytest.approx(25 + 10 + 12.75 + 2.5)
    assert sum(value for value in result["weighted_contributions"].values() if value is not None) == pytest.approx(result["final_score"])
    assert result["configured_weights"] == {"required_skills": 50, "experience": 25, "education": 15, "additional_skills": 10}


def test_scoring_nonmutation_and_irrelevant_fields(candidate):
    original = copy.deepcopy(candidate)
    baseline = score_candidate(candidate, JobRequirements())
    changed = {**candidate, "name": "Different Display Label", "email": "different@example.test",
               "age": 60, "gender": "not scored", "religion": "not scored", "photo": "not used"}
    result = score_candidate(changed, JobRequirements())
    assert result["final_score"] == baseline["final_score"]
    assert candidate == original


@pytest.mark.parametrize("skills,experience,education", [("", 0, "unmatched"), ("python", 1, "mca"), ("python; sql; pandas; git", 80, "MCA"), ("", None, None)])
def test_score_range_and_determinism(candidate, skills, experience, education):
    candidate.update(skills=skills, experience_years=experience, education=education)
    first = score_candidate(candidate, JobRequirements())
    assert 0 <= first["final_score"] <= 100
    assert first == score_candidate(candidate, JobRequirements())
