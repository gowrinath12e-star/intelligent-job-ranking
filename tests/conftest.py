"""Synthetic fixtures only; no real personal information."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def algorithm_candidates():
    return [
        {"candidate_id": "C003", "final_score": 75.0, "payload": {"unorderable": []}},
        {"candidate_id": "C001", "final_score": 100.0},
        {"candidate_id": "C004", "final_score": 0.0},
        {"candidate_id": "C002", "final_score": 75.0},
        {"candidate_id": "C005", "final_score": -5.0},
    ]


@pytest.fixture
def candidate():
    return {"candidate_id": "C001", "name": "Synthetic Applicant 001", "email": "one@example.test",
            "skills": "Python; SQL; Pandas; Git", "experience_years": 5.0,
            "education": "B.Tech Computer Science", "additional_skills": "Django; FastAPI; Docker; AWS", "application_id": "A001"}


@pytest.fixture
def applicant_frame(candidate):
    second = {**candidate, "candidate_id": "C002", "name": "Synthetic Applicant 002", "email": "two@example.test",
              "experience_years": 2.0, "skills": "Python; SQL", "additional_skills": "Docker", "application_id": "A002"}
    return pd.DataFrame([candidate, second])
