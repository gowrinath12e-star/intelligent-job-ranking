"""Review status remains independent of matching scores and rank order."""
import copy

import pytest

from algorithms.sorting import builtin_sort
from core.shortlisting import ReviewDecision, apply_shortlisting, get_shortlist, update_review_decision


@pytest.mark.parametrize("k", [0, 1, 3, 5, 10])
def test_normal_top_k(algorithm_candidates, k):
    records = apply_shortlisting(algorithm_candidates, k)
    assert get_shortlist(records) == [record for record in builtin_sort(records)[:k]]


def test_threshold_filtering(algorithm_candidates):
    records = apply_shortlisting(algorithm_candidates, 10, minimum_score=75)
    assert [record["candidate_id"] for record in get_shortlist(records)] == ["C001", "C002", "C003"]


def test_no_qualifying_candidates():
    records = apply_shortlisting([{"candidate_id": "A", "final_score": 20}], 3, 80)
    assert get_shortlist(records) == []
    assert "below" in records[0]["shortlist_reason"]


def test_below_minimum_gate_is_explicit():
    records = [{"candidate_id": "A", "final_score": 100, "automatic_eligible": False, "eligibility_status": "Below minimum experience"},
               {"candidate_id": "B", "final_score": 90, "automatic_eligible": True}]
    output = apply_shortlisting(records, 1)
    assert get_shortlist(output)[0]["candidate_id"] == "B"
    assert output[0]["shortlist_reason"] == "Below minimum experience"


def test_manual_status_changes_no_mutation(algorithm_candidates):
    original = copy.deepcopy(algorithm_candidates)
    decisions = update_review_decision({}, "C005", "Shortlisted", "Relevant project reviewed manually")
    decisions = update_review_decision(decisions, "C001", "Not shortlisted", "Application withdrawn")
    output = apply_shortlisting(algorithm_candidates, 1, decisions=decisions)
    assert [record["candidate_id"] for record in get_shortlist(output)] == ["C005"]
    assert next(record for record in output if record["candidate_id"] == "C005")["final_score"] == -5
    assert algorithm_candidates == original


def test_manual_hold_not_on_shortlist(algorithm_candidates):
    decisions = {"C001": ReviewDecision("Needs review", "Verify experience evidence")}
    output = apply_shortlisting(algorithm_candidates, 1, decisions=decisions)
    assert get_shortlist(output) == []
    assert next(record for record in output if record["candidate_id"] == "C001")["suggested_shortlist"]


def test_manual_inclusions_can_exceed_k(algorithm_candidates):
    decisions = {"C005": ReviewDecision("Shortlisted", "Reviewed exception")}
    assert len(get_shortlist(apply_shortlisting(algorithm_candidates, 1, decisions=decisions))) == 2


def test_unscored_retained_and_manual_inclusion():
    records = [{"candidate_id": "UNKNOWN", "final_score": None, "score_status": "Unscored"}]
    output = apply_shortlisting(records, 5)
    assert len(output) == 1 and not output[0]["is_shortlisted"]
    manual = apply_shortlisting(records, 0, decisions={"UNKNOWN": ReviewDecision("Shortlisted", "Request missing evidence in review")})
    assert get_shortlist(manual)[0]["final_score"] is None


def test_deterministic_output(algorithm_candidates):
    expected = [record["candidate_id"] for record in get_shortlist(apply_shortlisting(algorithm_candidates, 3))]
    actual = [record["candidate_id"] for record in get_shortlist(apply_shortlisting(reversed(algorithm_candidates), 3))]
    assert actual == expected


@pytest.mark.parametrize("threshold", [-1, 101, float("nan"), "bad", True])
def test_invalid_threshold(threshold):
    with pytest.raises(ValueError):
        apply_shortlisting([], 1, threshold)


@pytest.mark.parametrize("status,note", [("Shortlisted", ""), ("Not shortlisted", ""), ("Needs review", " "), ("unknown", "reason"), ("Automatic", "x" * 2001)])
def test_invalid_review_decision(status, note):
    with pytest.raises(ValueError):
        ReviewDecision(status, note)


def test_updates_copy_decisions():
    original = {}
    changed = update_review_decision(original, "C001", "Shortlisted", "A recorded reason")
    assert original == {} and changed["C001"].note == "A recorded reason"
    reverted = update_review_decision(changed, "C001", "Automatic")
    assert reverted["C001"].status == "Automatic"
