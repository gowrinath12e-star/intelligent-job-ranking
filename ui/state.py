"""One session-scoped workspace; ordinary navigation never erases input."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pandas as pd
import streamlit as st

from core.data_loader import load_applicants
from core.data_validation import ValidationResult, validate_applicants
from core.ranking import RankingResult, rank_validated, refresh_review
from core.scoring import JobRequirements
from core.shortlisting import ReviewDecision

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = PROJECT_ROOT / "data" / "sample_applicants.csv"


def initialize_workspace() -> None:
    """Initialize only once per browser session, using real sample-file data."""
    if "jr_requirements" not in st.session_state:
        st.session_state.jr_requirements = JobRequirements()
        st.session_state.jr_algorithm = "Merge Sort"
        st.session_state.jr_decisions = {}
        st.session_state.jr_dataset_version = 0
        st.session_state.jr_form_epoch = 0
        st.session_state.jr_flash = []
        import_dataset(load_applicants(SAMPLE_PATH), None, "Synthetic sample · 72 applicants")
    if "jr_next_page" in st.session_state:
        st.session_state.jr_page = st.session_state.pop("jr_next_page")


def import_dataset(frame: pd.DataFrame, mapping: Mapping[str, str] | None, name: str) -> ValidationResult:
    """Atomically accept a new validated file; reset cross-dataset review choices."""
    validation = validate_applicants(frame, mapping)
    result = rank_validated(validation, st.session_state.jr_requirements, st.session_state.jr_algorithm)
    st.session_state.jr_validation = validation
    st.session_state.jr_result = result
    st.session_state.jr_dataset_name = name
    st.session_state.jr_decisions = {}
    st.session_state.jr_dataset_version += 1
    clear_current_measurements()
    return validation


def set_requirements(requirements: JobRequirements) -> None:
    """Save only valid configurations; retain manual decisions with visible flags."""
    result = rank_validated(st.session_state.jr_validation, requirements,
                            st.session_state.jr_algorithm, st.session_state.jr_decisions)
    st.session_state.jr_requirements = requirements
    st.session_state.jr_result = result
    st.session_state.jr_form_epoch += 1
    clear_current_measurements()


def set_ranking_algorithm(algorithm: str) -> None:
    result = rank_validated(st.session_state.jr_validation, st.session_state.jr_requirements,
                            algorithm, st.session_state.jr_decisions)
    st.session_state.jr_algorithm = algorithm
    st.session_state.jr_result = result


def save_reviews(decisions: Mapping[str, ReviewDecision]) -> None:
    """Update only review fields, not criteria, matching scores or ordinal ranks."""
    result = refresh_review(st.session_state.jr_result, decisions)
    st.session_state.jr_decisions = dict(decisions)
    st.session_state.jr_result = result


def clear_current_measurements() -> None:
    for key in ("jr_current_sort_benchmark", "jr_current_heap_benchmark", "jr_current_lookup_benchmark",
                "jr_sort_lab_output", "jr_heap_lab_output", "jr_hash_lookup_id"):
        st.session_state.pop(key, None)


def get_result() -> RankingResult:
    return st.session_state.jr_result


def go_to(page: str) -> None:
    st.session_state.jr_next_page = page
    st.rerun()


def flash(message: str, kind: str = "success") -> None:
    st.session_state.jr_flash.append((kind, message))


def show_flash_messages() -> None:
    for kind, message in st.session_state.jr_flash:
        getattr(st, kind)(message)
    st.session_state.jr_flash = []


def require_candidates(numeric_only: bool = False) -> bool:
    """Every page has a navigable empty state rather than a widget crash."""
    result = get_result()
    candidates = result.scored_candidates if numeric_only else result.ranked_candidates
    if candidates:
        return True
    st.info("No numeric matching scores are available." if numeric_only else "No validated applicants are available yet.")
    if result.validation.summary["invalid"]:
        st.warning(f"{result.validation.summary['invalid']} rejected records need correction. See Upload Applicants → Validation issues.")
    if st.button("Open applicant upload", key="empty_upload"):
        go_to("Upload Applicants")
    return False
