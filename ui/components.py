"""Reusable, accessible Streamlit presentation components (no external assets)."""
from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

TEAL = "#087F8C"
NAVY = "#192B40"
GOLD = "#DDA349"
PALETTE = [TEAL, "#6C86BC", GOLD, "#B7C9D5", "#76BDA7"]

STYLE = """
<style>
.stApp { background: #F5F7FB; }
[data-testid="stAppDeployButton"] { display:none; }
.st-key-dashboard_distribution, .st-key-dashboard_coverage, .st-key-dashboard_top, .st-key-dashboard_job { background:white; border-radius:12px; }
.block-container { max-width: 1480px; padding: 4.1rem 2.4rem 3rem; }
h1,h2,h3 { letter-spacing: -.035em; color: #192B40; }
h1 { font-size: 2.15rem !important; font-weight: 750 !important; }
h2 { font-size: 1.35rem !important; } h3 { font-size: 1.08rem !important; }
p,li { line-height: 1.55; }
[data-testid="stSidebar"] { background:#FFFFFF; border-right: 1px solid #E3EAF0; }
[data-testid="stSidebar"] .block-container { padding:1.5rem 1.2rem; }
[data-testid="stSidebar"] [role="radiogroup"] { gap:.12rem; }
[data-testid="stSidebar"] [role="radiogroup"] label { width:100%; padding:.46rem .65rem; border-radius:.55rem; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background:#E7F4F4; color:#087F8C; }
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display:none; }
[data-testid="stSidebar"] hr { margin:.7rem 0; }
[data-testid="stMetric"] { background:white; border:1px solid #E1E8EF; padding:1rem; border-radius:12px; }
[data-testid="stDataFrame"] { border-radius:10px; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius:12px; }
.stButton button, .stDownloadButton button { border-radius:8px; font-weight:600; }
[data-testid="stForm"] { background:white; border:1px solid #E1E8EF; border-radius:12px; padding:1.2rem; }
.brand { display:flex; align-items:center; gap:.65rem; margin:.4rem 0 1.6rem; }
.brandmark { width:36px; height:36px; color:white; background:#087F8C; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:25px; }
.brandname { color:#192B40; font-size:1.05rem; font-weight:750; line-height:1.3; }
.brandsub { font-size:.68rem; font-weight:600; letter-spacing:.14em; color:#7E8C9C; text-transform:uppercase; }
.kicker { font-size:.68rem; color:#7B8A9B; font-weight:700; letter-spacing:.14em; text-transform:uppercase; margin-bottom:.45rem; }
.headerline { display:flex; justify-content:space-between; align-items:center; gap:12px; }
.headerline h1 { margin:0; padding:0 0 .35rem; }
.subtitle { color:#738196; font-size:.91rem; margin:0 0 1.4rem; }
.badge { display:inline-block; background:#E8F5F1; color:#207B62; border:1px solid #CDE8DC; border-radius:25px; padding:.32rem .7rem; font-size:.72rem; font-weight:600; }
.metric-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin:.25rem 0 1.6rem; }
.metric-card { background:white; border:1px solid #E1E8EF; border-radius:12px; padding:1rem 1.1rem; position:relative; }
.metric-label { color:#788799; font-size:.69rem; letter-spacing:.065em; text-transform:uppercase; font-weight:650; }
.metric-value { color:#192B40; font-size:1.9rem; font-weight:750; letter-spacing:-.045em; margin:.32rem 0 .1rem; }
.metric-card.accent { background:#087F8C; border-color:#087F8C; }
.metric-card.accent .metric-label,.metric-card.accent .metric-value,.metric-card.accent .metric-note { color:white; }
.metric-note { color:#8B99AA; font-size:.68rem; }
.chip { display:inline-block; font-size:.73rem; border:1px solid #D9E4EC; background:#F2F5F9; color:#4C637A; border-radius:6px; padding:.25rem .55rem; margin:.18rem .22rem .18rem 0; }
.chip.match { background:#E6F4EF; border-color:#CEE7DA; color:#207B62; }
.chip.missing { background:#FFF2EB; border-color:#F5DECE; color:#A5683A; }
.human-note { border-left:3px solid #83B9BE; background:#EAF4F6; color:#486676; border-radius:0 8px 8px 0; padding:.65rem .9rem; font-size:.78rem; margin:1rem 0; }
.dataset-box { background:#F5F8FA; border:1px solid #E1E8EF; border-radius:10px; padding:.85rem; font-size:.76rem; color:#65788C; }
.dataset-box strong { color:#192B40; }
@media(max-width:1100px) { .metric-grid {grid-template-columns:repeat(3,1fr);} }
@media(max-width:650px) { .block-container {padding:1.25rem 1rem;} .metric-grid {grid-template-columns:repeat(2,1fr);} .headerline {align-items:flex-start;flex-direction:column;} }
</style>
"""


def install_style() -> None:
    st.markdown(STYLE, unsafe_allow_html=True)


def page_header(section: str, title: str, subtitle: str) -> None:
    """Escape dynamic text before passing it to the HTML presentation layer."""
    label = "Synthetic demo" if st.session_state.get("jr_dataset_name") == "Synthetic sample · 72 applicants" else "Local workspace"
    st.markdown(f'<div class="kicker">JOB MATCH STUDIO / {html.escape(section)}</div>'
                f'<div class="headerline"><h1>{html.escape(title)}</h1><span class="badge">● {html.escape(label)}</span></div>'
                f'<p class="subtitle">{html.escape(subtitle)}</p>', unsafe_allow_html=True)


def metric_cards(items: Sequence[tuple[str, str, str]], accent_index: int = 2) -> None:
    cards = "".join(f'<div class="metric-card {"accent" if position == accent_index else ""}">'
                    f'<div class="metric-label">{html.escape(label)}</div><div class="metric-value">{html.escape(value)}</div>'
                    f'<div class="metric-note">{html.escape(note)}</div></div>'
                    for position, (label, value, note) in enumerate(items))
    st.markdown('<div class="metric-grid">' + cards + '</div>', unsafe_allow_html=True)


def chips(skills: Sequence[str], kind: str = "") -> None:
    if not skills:
        st.caption("None")
        return
    st.markdown("".join(f'<span class="chip {html.escape(kind)}">{html.escape(skill)}</span>' for skill in skills), unsafe_allow_html=True)


def human_review_note() -> None:
    st.markdown('<div class="human-note"><strong>Decision support, not a hiring decision.</strong> '
                'Scores match the configured job criteria—not predicted performance. Review missing evidence and recruiter notes. '
                'The system does not guarantee unbiased or legally compliant hiring.</div>', unsafe_allow_html=True)


def chart_style(figure: go.Figure, height: int = 290) -> go.Figure:
    figure.update_layout(template="plotly_white", height=height,
                         margin=dict(l=15, r=15, t=25, b=25),
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(family="Arial, sans-serif", color="#52687D", size=12),
                         colorway=PALETTE, legend=dict(orientation="h", y=-.15, x=0))
    figure.update_xaxes(gridcolor="#EBF0F5", zeroline=False)
    figure.update_yaxes(gridcolor="#EBF0F5", zeroline=False)
    return figure


def candidate_table(candidates: Sequence[Mapping[str, Any]], key: str | None = None, height: int | None = None) -> None:
    """Focused view; source contact information never appears in analytics tables."""
    columns = ["Rank", "Candidate ID", "Applicant", "Match score", "Evidence", "Experience (yrs)",
               "Required skills matched", "Shortlisted", "Review status"]
    data = pd.DataFrame([{
        "Rank": record.get("rank"), "Candidate ID": record["candidate_id"], "Applicant": record.get("name", ""),
        "Match score": record.get("final_score"), "Evidence": record.get("score_status", ""),
        "Experience (yrs)": record.get("experience_years"),
        "Required skills matched": ", ".join(record.get("matched_required_skills", [])),
        "Shortlisted": record.get("is_shortlisted", False), "Review status": record.get("review_status", "Automatic"),
    } for record in candidates], columns=columns)
    options: dict[str, Any] = dict(hide_index=True, width="stretch",
        column_config={"Rank": st.column_config.NumberColumn(format="%d", width="small"),
                       "Match score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.2f", width="medium"),
                       "Experience (yrs)": st.column_config.NumberColumn(format="%.1f"),
                       "Shortlisted": st.column_config.CheckboxColumn()})
    if key:
        options["key"] = key
    if height:
        options["height"] = height
    st.dataframe(data, **options)


def candidate_label(record: Mapping[str, Any]) -> str:
    score = f"{record['final_score']:.2f}" if record.get("final_score") is not None else "Unscored"
    return f"{record['candidate_id']} · {record.get('name', '')} · {score}"


def score_breakdown(record: Mapping[str, Any]) -> None:
    """Explain every component and the exact candidate-specific weight changes."""
    from core.scoring import COMPONENTS, COMPONENT_LABELS
    st.subheader(f"{record.get('name', 'Candidate')} · {record['candidate_id']}")
    a, b, c = st.columns(3)
    a.metric("Matching score", f"{record['final_score']:.2f} / 100" if record['final_score'] is not None else "Unavailable")
    b.metric("Evidence status", record["score_status"])
    c.metric("Experience", f"{record['experience_years']:g} years" if record.get("experience_years") is not None else "Unknown")
    st.caption(record["eligibility_status"] + " · Review status: " + record.get("review_status", "Automatic"))
    left, right = st.columns(2)
    with left:
        st.markdown("**Matched required skills**")
        chips(record["matched_required_skills"], "match")
        st.markdown("**Matched additional skills**")
        chips(record["matched_additional_skills"], "match")
    with right:
        st.markdown("**Missing required skills**")
        chips(record["missing_required_skills"], "missing")
        st.markdown("**Missing additional skills**")
        chips(record["missing_additional_skills"], "missing")
    rows = [{"Component": COMPONENT_LABELS[component], "Score / 100": record["component_scores"][component],
             "Configured weight %": record["configured_weights"][component],
             "Effective weight %": record["effective_weights"][component],
             "Contribution": record["weighted_contributions"][component],
             "Status": record["component_statuses"][component]} for component in COMPONENTS]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Final score = sum of component score × effective weight / 100. Stored to 6 decimals; displayed to 2.")
    st.info(record["education_reason"])
    for note in record["scoring_notes"][:-1]:
        st.warning(note) if record["score_status"] != "Complete" else st.caption(note)
    if record.get("validation_warnings"):
        with st.expander("Source-data warnings"):
            for warning in record["validation_warnings"].split(" | "):
                st.write("• " + warning)
    if record.get("shortlist_reason"):
        st.caption("Shortlist assessment: " + record["shortlist_reason"])
