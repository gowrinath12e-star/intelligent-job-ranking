"""Recruiter configuration with atomic, domain-level validation on submission."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.scoring import JobRequirements, ScoringWeights
from ui.components import human_review_note, page_header
from ui.state import flash, get_result, set_requirements


def render() -> None:
    """Render and validate the job-criteria form before publishing changes."""
    page_header("Job configuration", "Define what matters for the role", "Configure job-related criteria, explicit education scores, and a reviewable shortlist policy.")
    current = get_result().requirements
    epoch = st.session_state.jr_form_epoch
    st.info("Matching is deterministic. Required/additional skill names are normalized exactly; there is no external AI, fuzzy inference, or sensitive-feature scoring.")
    with st.form(f"job_requirements_{epoch}"):
        title = st.text_input("Job title", current.title, key=f"job_title_{epoch}")
        left, right = st.columns(2)
        with left:
            required = st.text_area("Required skills", ", ".join(sorted(current.required_skills)), key=f"job_required_{epoch}", help="Separate with commas, semicolons or newlines. Empty disables this component.")
            minimum = st.number_input("Minimum experience (years)", min_value=0.0, max_value=80.0, value=current.minimum_experience, step=.5, key=f"job_min_exp_{epoch}", help="Known experience below this minimum is excluded from automatic suggestions, not from the full ranking. Unknown experience is flagged for review.")
        with right:
            additional = st.text_area("Additional relevant skills", ", ".join(sorted(current.additional_skills)), key=f"job_additional_{epoch}", help="Must not overlap the required list; empty disables this component.")
            use_experience = st.checkbox("Include experience in matching score", value=current.target_experience is not None, key=f"job_exp_enabled_{epoch}")
            target = st.number_input("Target experience (years)", min_value=.1, max_value=80.0, value=current.target_experience or 5.0, step=.5, key=f"job_target_{epoch}", help="Score = min(experience / target, 1) × 100. Ignored if experience scoring is disabled.")
        st.markdown("### Job-related education rubric")
        use_education = st.checkbox("Include education in matching score", value=bool(current.education_rubric), key=f"job_edu_enabled_{epoch}")
        st.caption("Exact normalized label → score. Define only criteria relevant to the role; this is NOT a universal degree hierarchy. Add/delete rows as needed. Leave disabled to exclude education entirely.")
        rubric_data = pd.DataFrame([{"Education label": label, "Score / 100": score} for label, score in current.education_rubric.items()], columns=["Education label", "Score / 100"])
        rubric_editor = st.data_editor(rubric_data, num_rows="dynamic", hide_index=True, width="stretch",
            key=f"job_edu_editor_{epoch}", column_config={"Education label": st.column_config.TextColumn(required=True),
                                                         "Score / 100": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, required=True)})
        unmatched = st.number_input("Score for a PROVIDED education label not in the rubric", min_value=0.0, max_value=100.0, value=current.unmatched_education_score, step=5.0, key=f"job_unmatched_{epoch}", help="Unknown education is different: it receives no score and is excluded with a provisional-evidence flag.")
        st.markdown("### Component weights · must total 100%")
        cols = st.columns(4)
        values: dict[str, float] = {}
        for col, component, label in zip(cols, ("required_skills", "experience", "education", "additional_skills"), ("Required skills %", "Experience %", "Education %", "Additional skills %")):
            with col:
                values[component] = st.number_input(label, min_value=0.0, max_value=100.0, value=getattr(current.weights, component), step=1.0, key=f"job_weight_{component}_{epoch}")
        st.caption("Disabled components are excluded and the remaining weights renormalized. At least one configured component needs a positive weight. Unknown candidate experience/education also causes visible, candidate-specific renormalization.")
        st.markdown("### Shortlist policy")
        a, b, c = st.columns(3)
        with a:
            k = st.number_input("Number to suggest (K)", min_value=0, max_value=1000000, value=current.shortlist_k, step=1, key=f"job_k_{epoch}")
        with b:
            use_threshold = st.checkbox("Require a minimum matching score", value=current.minimum_score is not None, key=f"job_threshold_enabled_{epoch}")
        with c:
            threshold = st.number_input("Minimum score / 100", min_value=0.0, max_value=100.0, value=current.minimum_score if current.minimum_score is not None else 60.0, step=1.0, key=f"job_threshold_{epoch}")
        submitted = st.form_submit_button("Save criteria & recalculate rankings", type="primary", width="stretch")
        if submitted:
            try:
                rubric: dict[str, float] = {}
                normalized_labels: set[str] = set()
                if use_education:
                    from core.normalization import is_missing, normalize_education
                    for row in rubric_editor.to_dict("records"):
                        if is_missing(row["Education label"]) and is_missing(row["Score / 100"]):
                            continue
                        label = normalize_education(row["Education label"])
                        if label is None or is_missing(row["Score / 100"]):
                            raise ValueError("Every education-rubric row needs a label and a numeric score.")
                        if label in normalized_labels:
                            raise ValueError("Education rubric has duplicate normalized labels: " + label)
                        normalized_labels.add(label)
                        rubric[label] = float(row["Score / 100"])
                    if not rubric:
                        raise ValueError("Provide at least one education-rubric row, or disable education scoring.")
                config = JobRequirements(title, required, additional, minimum, target if use_experience else None,
                                         rubric, unmatched, ScoringWeights(**values), int(k), threshold if use_threshold else None)
                set_requirements(config)
                flash("Job criteria saved and actual scores recalculated. Existing manual review decisions were retained—review them against the updated criteria.")
                st.rerun()
            except (ValueError, TypeError) as exc:
                st.error(str(exc))
                st.caption("The saved criteria and active rankings were not changed.")
    with st.expander("Current effective job weights"):
        st.dataframe(pd.DataFrame([{"Component": key.replace("_", " ").title(), "Configured %": current.weights.as_dict()[key], "Effective job %": value}
                                   for key, value in current.effective_job_weights().items()]), hide_index=True, width="stretch")
    if st.button("Restore example Python Developer criteria"):
        set_requirements(JobRequirements())
        st.session_state.jr_form_epoch += 1
        flash("Example criteria restored. Manual review decisions are still available.")
        st.rerun()
    human_review_note()
