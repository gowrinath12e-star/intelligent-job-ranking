"""Streamlit entry point. Business logic lives in core/, algorithms/ and utils/."""
from __future__ import annotations

import html

import streamlit as st

from ui import pages_about, pages_candidates, pages_dashboard, pages_labs, pages_performance, pages_reports, pages_requirements, pages_upload
from ui.components import install_style
from ui.state import SAMPLE_PATH, flash, get_result, go_to, import_dataset, initialize_workspace, show_flash_messages
from core.data_loader import load_applicants

PAGES = {
    "Dashboard": pages_dashboard.render,
    "Upload Applicants": pages_upload.render,
    "Job Requirements": pages_requirements.render,
    "Candidate Ranking": pages_candidates.render_ranking,
    "Shortlist Management": pages_candidates.render_shortlist,
    "Sorting Laboratory": pages_labs.render_sorting,
    "Heap Laboratory": pages_labs.render_heap,
    "Hashing Laboratory": pages_labs.render_hashing,
    "Performance Analysis": pages_performance.render,
    "Export Reports": pages_reports.render,
    "About Project": pages_about.render,
}


def main() -> None:
    st.set_page_config(page_title="Job Match Studio · Python & DSA", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
    install_style()
    initialize_workspace()
    with st.sidebar:
        st.markdown('<div class="brand"><div class="brandmark">◈</div><div><div class="brandname">Job Match Studio</div><div class="brandsub">Recruitment × DSA</div></div></div>', unsafe_allow_html=True)
        st.caption("WORKSPACE")
        page = st.radio("Page navigation", list(PAGES), key="jr_page", label_visibility="collapsed")
        st.divider()
        result = get_result()
        st.markdown(f'<div class="dataset-box"><strong>ACTIVE DATASET</strong><br>{html.escape(st.session_state.jr_dataset_name)}<br><br>'
                    f'{result.validation.summary["valid"]} valid applicants · {len(result.shortlist)} on review shortlist<br>'
                    f'<strong>{html.escape(result.requirements.title)}</strong></div>', unsafe_allow_html=True)
        if st.button("Reload synthetic sample", width="stretch"):
            import_dataset(load_applicants(SAMPLE_PATH), None, "Synthetic sample · 72 applicants")
            flash("Sample reloaded. Your criteria were kept; dataset-specific review decisions were reset.")
            st.rerun()
        st.caption("LOCAL-FIRST · NO AI API\n\nFor classroom demonstration and human review, not automated hiring.")
    show_flash_messages()
    PAGES[page]()


if __name__ == "__main__":
    main()
