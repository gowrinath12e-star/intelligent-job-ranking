"""Working report downloads; all bytes are generated from session data."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.components import human_review_note, page_header
from ui.state import get_result
from utils.exports import breakdown_frame, csv_bytes, excel_bytes, ranked_frame, requirements_frame, validation_issues_frame, validation_workbook


def benchmark_reports() -> pd.DataFrame:
    """Combine only actually executed benchmark tables, with source labels."""
    frames = []
    for key in ("jr_current_sort_benchmark", "jr_current_heap_benchmark", "jr_current_lookup_benchmark", "jr_generated_sort_benchmark", "jr_generated_heap_benchmark", "jr_generated_lookup_benchmark"):
        frame = st.session_state.get(key)
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def render() -> None:
    """Render purpose-limited CSV/Excel downloads from current session data."""
    page_header("Downloads", "Export a review-ready report", "Portable CSV and Excel reports from the current dataset, criteria, decisions, and measured benchmarks.")
    result = get_result()
    ranking = ranked_frame(result.ranked_candidates)
    shortlist = ranked_frame(result.shortlist)
    criteria = requirements_frame(result.requirements)
    breakdown = breakdown_frame(result.ranked_candidates)
    a, b = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            st.subheader("Complete candidate ranking")
            st.caption(f"{len(ranking)} valid records · ordered numeric ranks followed by explicit unscored records")
            st.download_button("Ranked list · CSV", csv_bytes(ranking), "ranked_applicants.csv", "text/csv", on_click="ignore", width="stretch")
            st.download_button("Ranked list · Excel", excel_bytes({"Candidate ranking": ranking, "Job criteria": criteria}), "ranked_applicants.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore", width="stretch")
        with st.container(border=True):
            st.subheader("Candidate score explanations")
            st.caption("One row per candidate per component: matched skills, missing skills, effective weights, contribution and reason.")
            st.download_button("Score breakdown · CSV", csv_bytes(breakdown), "candidate_score_breakdown.csv", "text/csv", on_click="ignore", width="stretch")
            st.download_button("Score breakdown · Excel", excel_bytes({"Score explanations": breakdown, "Job criteria": criteria}), "candidate_score_breakdown.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore", width="stretch")
    with b:
        with st.container(border=True):
            st.subheader("Final review shortlist")
            st.caption(f"{len(shortlist)} records · saved human overrides included · matching scores kept separate")
            st.download_button("Shortlist · CSV", csv_bytes(shortlist), "review_shortlist.csv", "text/csv", on_click="ignore", width="stretch")
            st.download_button("Shortlist · Excel", excel_bytes({"Review shortlist": shortlist, "Job criteria": criteria}), "review_shortlist.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore", width="stretch")
        with st.container(border=True):
            st.subheader("Validation & cleaning")
            st.caption(f"{result.validation.summary['invalid']} invalid rows · {result.validation.summary['warning_count']} warning messages · duplicate groups included")
            st.download_button("Validation issues · CSV", csv_bytes(validation_issues_frame(result.validation)), "validation_issues.csv", "text/csv", on_click="ignore", width="stretch")
            st.download_button("Complete validation · Excel", validation_workbook(result.validation), "data_validation_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore", width="stretch")
    with st.container(border=True):
        st.subheader("Algorithm benchmark report")
        benchmarks = benchmark_reports()
        if benchmarks.empty:
            st.info("No benchmark has run in this session yet. Run one in a DSA laboratory or Performance Analysis; measured values will then be available here.")
        else:
            st.dataframe(benchmarks, hide_index=True, width="stretch")
            a, b = st.columns(2)
            with a:
                st.download_button("Measured benchmarks · CSV", csv_bytes(benchmarks), "algorithm_benchmarks.csv", "text/csv", on_click="ignore", width="stretch")
            with b:
                st.download_button("Measured benchmarks · Excel", excel_bytes({"Benchmarks": benchmarks}), "algorithm_benchmarks.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore", width="stretch")
    st.caption("Standard analytics exports exclude email and arbitrary source columns. Correction downloads on the Upload page contain only known applicant fields needed to repair invalid rows. Spreadsheet formula prefixes in text are escaped on export.")
    human_review_note()
