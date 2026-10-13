"""Searchable rankings, complete explanations, comparisons and review management."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from algorithms.sorting import SORT_ALGORITHMS
from core.scoring import COMPONENTS, COMPONENT_LABELS
from core.shortlisting import REVIEW_STATUSES, ReviewDecision, update_review_decision
from ui.components import PALETTE, candidate_label, candidate_table, chart_style, human_review_note, metric_cards, page_header, score_breakdown
from ui.state import flash, get_result, require_candidates, save_reviews, set_ranking_algorithm, set_requirements
from utils.exports import csv_bytes, ranked_frame


def filter_candidates(prefix: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter the display only; ordinal rank and original score never change."""
    result = get_result()
    a, b, c = st.columns([1.5, 1.5, 1])
    with a:
        search = st.text_input("Search name or candidate ID", placeholder="e.g. C001 or Synthetic Applicant", key=f"{prefix}_search")
    with b:
        choices = sorted(result.requirements.required_skills or result.index.skill_to_candidate_ids)
        skills = st.multiselect("Filter required skills", choices, key=f"{prefix}_skills")
    with c:
        min_experience = st.number_input("Display minimum years", min_value=0.0, max_value=80.0, value=0.0, step=.5, key=f"{prefix}_exp")
    a, b, c = st.columns(3)
    with a:
        skill_mode = st.radio("Skill filter rule", ["All selected", "Any selected"], horizontal=True, key=f"{prefix}_skill_mode")
    with b:
        include_unknown = st.checkbox("Include unknown experience", value=True, key=f"{prefix}_unknown")
    with c:
        evidence = st.selectbox("Evidence status", ["All", "Complete", "Provisional", "Unscored"], key=f"{prefix}_evidence")
    allowed = result.index.with_skills(skills, "all" if skill_mode == "All selected" else "any")
    needle = search.strip().lower()
    filtered = []
    for record in records:
        experience = record.get("experience_years")
        if record["candidate_id"] not in allowed:
            continue
        if needle and needle not in record["candidate_id"].lower() and needle not in record.get("name", "").lower():
            continue
        if experience is None and not include_unknown:
            continue
        if experience is not None and experience < min_experience:
            continue
        if evidence != "All" and record["score_status"] != evidence:
            continue
        filtered.append(record)
    st.caption(f"Showing {len(filtered)} of {len(records)} records. Filters affect this view, not scores, ranks or saved shortlist decisions.")
    return filtered


def render_ranking() -> None:
    """Render searchable ranks, explained scores and candidate comparisons."""
    page_header("Applicant analysis", "Rank, explain, compare", "Deterministic ranking with evidence you can inspect, not a black-box recommendation.")
    if not require_candidates():
        return
    result = get_result()
    a, b = st.columns([2, 1])
    with a:
        algorithm = st.selectbox("Active ranking algorithm", list(SORT_ALGORITHMS), index=list(SORT_ALGORITHMS).index(result.algorithm), key="ranking_algorithm_choice")
        if algorithm != result.algorithm:
            set_ranking_algorithm(algorithm)
            flash(f"Ranking updated with {algorithm}; output verified against the built-in reference.")
            st.rerun()
    with b:
        st.download_button("Download full ranking · CSV", csv_bytes(ranked_frame(result.ranked_candidates)), "ranked_applicants.csv", "text/csv", on_click="ignore", width="stretch")
    st.caption("Sort key: descending matching score, then ascending lexical candidate ID. Unscored records remain visible after the numeric ranking.")
    tabs = st.tabs(["All applicants", "Score explanation", "Compare applicants"])
    with tabs[0]:
        filtered = filter_candidates("rank", result.ranked_candidates)
        candidate_table(filtered, height=430)
        if not filtered:
            st.info("No applicants match the display filters. Clear a filter to broaden the view.")
    with tabs[1]:
        identifiers = [record["candidate_id"] for record in result.ranked_candidates]
        identifier = st.selectbox("Inspect an applicant", identifiers, format_func=lambda value: candidate_label(result.index.lookup(value)), key="ranking_details_id")
        with st.container(border=True):
            score_breakdown(result.index.lookup(identifier))
    with tabs[2]:
        render_comparison()
    human_review_note()


def render_comparison() -> None:
    """Compare two to five selected candidates without changing their scores."""
    result = get_result()
    identifiers = [record["candidate_id"] for record in result.ranked_candidates]
    selected = st.multiselect("Choose two to five applicants", identifiers, default=identifiers[:2], max_selections=5,
                             format_func=lambda value: candidate_label(result.index.lookup(value)), key="comparison_ids")
    if len(selected) < 2:
        st.info("Select at least two applicants to compare their job-criteria evidence.")
        return
    records = [result.index.lookup(identifier) for identifier in selected]
    candidate_table(records)
    comparisons = []
    for record in records:
        for component in COMPONENTS:
            score = record["component_scores"][component]
            if score is not None:
                comparisons.append({"Candidate ID": record["candidate_id"], "Component": COMPONENT_LABELS[component], "Score": score})
    if comparisons:
        figure = px.bar(pd.DataFrame(comparisons), x="Component", y="Score", color="Candidate ID", barmode="group", color_discrete_sequence=PALETTE)
        figure.update_yaxes(range=[0, 100])
        st.plotly_chart(chart_style(figure, 330), width="stretch")
    st.caption("Missing components have no bar, not a zero-height bar. Different effective weights on provisional scores can make scores less comparable.")
    detail = {record["candidate_id"]: {
        "Matching score": record["final_score"], "Evidence status": record["score_status"],
        "Experience gate": record["eligibility_status"], "Education label": record.get("education") or "Unknown",
        "Matched required skills": ", ".join(record["matched_required_skills"]),
        "Missing required skills": ", ".join(record["missing_required_skills"]),
        "Effective weights (%)": "; ".join(f"{COMPONENT_LABELS[key]}: {weight:.1f}" for key, weight in record["effective_weights"].items()),
        "Review note": record.get("review_note", ""),
    } for record in records}
    st.dataframe(pd.DataFrame(detail).astype(str), width="stretch")


def render_shortlist() -> None:
    """Render heap suggestions, explicit review overrides and shortlist exports."""
    page_header("Recruiter review", "A shortlist you can review", "Heap-generated suggestions and recruiter decisions are separate, traceable fields.")
    result = get_result()
    policy = result.requirements
    with st.expander("Adjust shortlist policy", expanded=False):
        with st.form("shortlist_policy"):
            a, b, c = st.columns(3)
            with a:
                k = st.number_input("Suggested shortlist size K", min_value=0, max_value=1000000, value=policy.shortlist_k, step=1)
            with b:
                use_threshold = st.checkbox("Apply matching-score threshold", value=policy.minimum_score is not None)
            with c:
                threshold = st.number_input("Threshold / 100", min_value=0.0, max_value=100.0, value=policy.minimum_score if policy.minimum_score is not None else 60.0, step=1.0)
            if st.form_submit_button("Apply shortlist policy", type="primary"):
                set_requirements(replace(policy, shortlist_k=int(k), minimum_score=threshold if use_threshold else None))
                st.session_state.jr_form_epoch += 1
                flash("Shortlist policy updated. Manual overrides were preserved; their matching scores were not changed.")
                st.rerun()
    if not require_candidates():
        return
    candidates = result.ranked_candidates
    suggestions = sum(record["suggested_shortlist"] for record in candidates)
    manual = sum(record["review_status"] != "Automatic" for record in candidates)
    flagged = sum(record["score_status"] != "Complete" or "unknown" in record["eligibility_status"].lower() for record in result.shortlist)
    metric_cards([
        ("Requested K", str(policy.shortlist_k), "Eligible automatic suggestions"),
        ("Heap suggestions", str(suggestions), "After experience and score gates"),
        ("Review shortlist", str(len(result.shortlist)), "Includes saved manual decisions"),
        ("Manual decisions", str(manual), "Notes required for every override"),
        ("Evidence flags", str(flagged), "Shortlisted records needing review"),
    ])
    if len(result.shortlist) > policy.shortlist_k:
        st.info("The review shortlist exceeds K because of explicit manual inclusions. K caps automatic suggestions only.")
    if flagged:
        st.warning(f"{flagged} shortlisted records need evidence review. Provisional scores or unknown minimum experience are not verified qualifications.")
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        st.subheader("Current review shortlist")
        if result.shortlist:
            candidate_table(result.shortlist, height=370)
        else:
            st.info("The review shortlist is empty. Change K, lower the threshold, or record an explicit manual inclusion.")
        st.download_button("Export review shortlist · CSV", csv_bytes(ranked_frame(result.shortlist)), "review_shortlist.csv", "text/csv", on_click="ignore", width="stretch")
    with right:
        st.subheader("Record a review decision")
        ids = [record["candidate_id"] for record in candidates]
        identifier = st.selectbox("Candidate to review", ids, format_func=lambda value: candidate_label(result.index.lookup(value)), key=f"review_candidate_{st.session_state.jr_dataset_version}")
        record = result.index.lookup(identifier)
        decision = st.session_state.jr_decisions.get(identifier, ReviewDecision())
        st.caption(record["eligibility_status"] + " · " + record["score_status"] + " evidence")
        version = st.session_state.jr_dataset_version
        with st.form(f"review_form_{version}_{identifier}"):
            status = st.selectbox("Recruiter review status", list(REVIEW_STATUSES), index=REVIEW_STATUSES.index(decision.status), key=f"review_status_{version}_{identifier}")
            note = st.text_area("Review note / reason", value=decision.note, max_chars=2000, key=f"review_note_{version}_{identifier}", help="Required for manual inclusion, exclusion or review hold. Scores never change because of a review choice.")
            if st.form_submit_button("Save review decision", type="primary", width="stretch"):
                try:
                    decisions = update_review_decision(st.session_state.jr_decisions, identifier, status, note)
                    save_reviews(decisions)
                    flash("Review decision saved. Matching score and original rank were not altered.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        st.caption("Automatic uses the heap suggestion. Needs review places the record on hold (not on the final review shortlist). Manual inclusions can bypass gates, but are labelled and require a reason.")
    with st.expander("All candidate review assessments"):
        filtered = filter_candidates("shortlist_all", candidates)
        st.dataframe(ranked_frame(filtered), hide_index=True, width="stretch")
    with st.expander("Reset manual decisions"):
        confirmed = st.checkbox("I want to remove every manual status and review note.")
        if st.button("Return all candidates to Automatic", disabled=not confirmed):
            save_reviews({})
            # Remove per-candidate editor state so prior decisions cannot leak
            # back into a newly reset form on ordinary reruns.
            for key in list(st.session_state):
                if key.startswith(("review_status_", "review_note_")):
                    del st.session_state[key]
            flash("All manual decisions reset. The shortlist now reflects the heap suggestions.")
            st.rerun()
    human_review_note()
