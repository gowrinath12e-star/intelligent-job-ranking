"""Recruitment overview; every metric and chart uses the active dataset."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.analytics import score_distribution
from ui.components import TEAL, candidate_table, chart_style, chips, human_review_note, metric_cards, page_header
from ui.state import get_result, go_to, require_candidates


def render() -> None:
    """Render all data-derived overview metrics, charts and criteria summaries."""
    page_header("Overview", "Your recruitment overview", "A clear view of the applicant pool, criteria matches, and human-review shortlist.")
    result = get_result()
    validation = result.validation.summary
    scores = [candidate["final_score"] for candidate in result.scored_candidates]
    average = sum(scores) / len(scores) if scores else None
    highest = max(scores) if scores else None
    metric_cards([
        ("Applicants", f"{validation['uploaded']:,}", "Rows in the current file"),
        ("Validated", f"{validation['valid']:,}", f"{validation['invalid']} rejected · all reported"),
        ("Shortlisted", f"{len(result.shortlist):,}", f"{result.requirements.shortlist_k} requested · reviewable"),
        ("Average match", f"{average:.2f}" if average is not None else "—", f"Across {len(scores)} scored applicants"),
        ("Highest match", f"{highest:.2f}" if highest is not None else "—", "Job-criteria score / 100"),
    ])
    if not require_candidates():
        human_review_note()
        return
    left, right = st.columns([1.8, 1], gap="large")
    with left:
        with st.container(border=True, key="dashboard_distribution"):
            st.subheader("Matching-score distribution")
            st.caption("Actual scored applicants · fixed 10-point bins · provisional evidence included")
            if scores:
                bins = score_distribution(scores)
                figure = go.Figure(go.Bar(x=bins.bin_center, y=bins.applicants, width=8,
                                         customdata=bins.score_range, marker_color=TEAL,
                                         hovertemplate="Score range: %{customdata}<br>Applicants: %{y}<extra></extra>"))
                figure.update_layout(bargap=.16, xaxis_title="Job-criteria matching score", yaxis_title="Applicants")
                figure.update_xaxes(range=[0, 100])
                st.plotly_chart(chart_style(figure, 260), width="stretch", config={"displayModeBar": False})
            else:
                st.info("All valid records have unknown weighted evidence; no score distribution can be calculated.")
    with right:
        with st.container(border=True, key="dashboard_coverage"):
            st.subheader("Shortlist coverage")
            selected = len(result.shortlist)
            other = validation["valid"] - selected
            figure = go.Figure(go.Pie(labels=["Shortlisted", "Not shortlisted"], values=[selected, other], hole=.76,
                                    marker=dict(colors=[TEAL, "#DFE7EF"]), textinfo="none",
                                    hovertemplate="%{label}: %{value}<extra></extra>"))
            figure.update_layout(annotations=[dict(text=f"<b>{selected}</b><br>shortlisted", x=.5, y=.5,
                                                   showarrow=False, font=dict(size=20, color="#192B40"))])
            st.plotly_chart(chart_style(figure, 260), width="stretch", config={"displayModeBar": False})
    left, right = st.columns([1.8, 1], gap="large")
    with left:
        with st.container(border=True, key="dashboard_top"):
            col_title, col_action = st.columns([3, 1])
            with col_title:
                st.subheader("Top-ranked applicants")
                st.caption(f"{result.algorithm} · descending score, then candidate ID")
            with col_action:
                if st.button("View all →", width="stretch"):
                    go_to("Candidate Ranking")
            candidate_table(result.scored_candidates[:6], height=255)
    with right:
        with st.container(border=True, key="dashboard_job"):
            st.subheader(result.requirements.title)
            st.caption("CURRENT JOB REQUIREMENTS")
            st.markdown("**Required skills**")
            chips(sorted(result.requirements.required_skills))
            st.markdown("**Additional skills**")
            chips(sorted(result.requirements.additional_skills))
            minimum = result.requirements.minimum_experience
            target = result.requirements.target_experience
            st.caption(f"Minimum: {minimum:g} years · Target: {target:g} years" if target is not None else f"Minimum: {minimum:g} years · Experience scoring disabled")
            threshold = result.requirements.minimum_score
            st.caption(f"Threshold: {threshold:g}/100" if threshold is not None else "No minimum matching-score threshold")
            if st.button("Edit requirements", width="stretch"):
                go_to("Job Requirements")
    provisional = sum(candidate["score_status"] == "Provisional" for candidate in result.ranked_candidates)
    unscored = len(result.ranked_candidates) - len(scores)
    if provisional or unscored:
        st.warning(f"Evidence needs review: {provisional} provisional scores and {unscored} unscored records. Unknown information is not treated as zero; available weights are renormalized.")
    with st.expander("Full requirements and evidence summary"):
        from utils.exports import requirements_frame
        st.dataframe(requirements_frame(result.requirements), hide_index=True, width="stretch")
        st.dataframe(pd.DataFrame([{"Evidence status": status, "Applicants": sum(candidate['score_status'] == status for candidate in result.ranked_candidates)}
                                   for status in ("Complete", "Provisional", "Unscored")]), hide_index=True)
    human_review_note()
