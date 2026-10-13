"""Hash maps and sets drive lookup, skill filters and duplicate detection."""
import pytest

from algorithms.hashing import build_candidate_index, duplicate_application_ids, duplicate_identifier_positions, skill_match
from core.normalization import normalize_skills


def test_existing_missing_lookup(applicant_frame):
    records = applicant_frame.to_dict("records")
    index = build_candidate_index(records)
    assert index.lookup(" C001 ") is records[0]
    assert index.lookup("MISSING") is None


def test_skill_intersection_and_difference():
    matched, missing = skill_match(" Python; SQL; Python ", ["python", "pandas", "sql"])
    assert matched == {"python", "sql"}
    assert missing == {"pandas"}


@pytest.mark.parametrize("skills", [None, "", [], set(), frozenset()])
def test_empty_skill_collections(skills):
    assert normalize_skills(skills) == frozenset()
    assert skill_match(skills, ["python"]) == (set(), {"python"})


def test_normalize_delimiters_and_multiword():
    assert normalize_skills(" Python ,SQL|machine   learning\npython; ") == {"python", "sql", "machine learning"}


def test_inverted_all_any_filters(applicant_frame):
    index = build_candidate_index(applicant_frame.to_dict("records"))
    assert index.with_skills("python; pandas", "all") == {"C001"}
    assert index.with_skills("sql; unknown", "any") == {"C001", "C002"}
    assert index.with_skills("unknown", "all") == set()
    assert index.with_skills([]) == {"C001", "C002"}
    assert index.with_skills("docker") == {"C001", "C002"}
    with pytest.raises(ValueError):
        index.with_skills("python", "invalid")


def test_returned_skill_set_cannot_mutate_index(applicant_frame):
    index = build_candidate_index(applicant_frame.to_dict("records"))
    ids = index.with_skills("python")
    ids.clear()
    assert len(index.with_skills("python")) == 2


def test_duplicate_application_ids():
    records = [{"application_id": " A1 "}, {"application_id": "A2"}, {"application_id": "A1"}, {"application_id": None}, {}]
    assert duplicate_application_ids(records) == {"A1": [0, 2]}
    assert duplicate_identifier_positions(records, "candidate_id") == {}


def test_duplicate_candidate_index_rejected(candidate):
    with pytest.raises(ValueError, match="Duplicate"):
        build_candidate_index([candidate, dict(candidate)])


def test_empty_index():
    index = build_candidate_index([])
    assert index.lookup("A") is None
    assert index.with_skills([]) == set()
    assert duplicate_application_ids([]) == {}


@pytest.mark.parametrize("skills", [42, {"python": 1}, ["python", 4]])
def test_invalid_skill_types(skills):
    with pytest.raises(ValueError):
        normalize_skills(skills)
