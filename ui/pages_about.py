"""Presentation context and concise educational explanations inside the app."""
from __future__ import annotations

import streamlit as st

from ui.components import human_review_note, page_header
from utils.performance import complexity_table


def render() -> None:
    """Explain project architecture, DSA applications, demo steps and limits."""
    page_header("Project notes", "Practical recruitment. Real DSA.", "A Python mini project built to make sorting, heaps, and hashing visible in a useful workflow.")
    st.subheader("Intelligent Job Applicant Ranking and Shortlisting System Using Python and Data Structures and Algorithms")
    st.write("This offline-capable application validates applicant tables, computes transparent job-criteria matching scores, ranks applicants and builds a human-review shortlist. 'Intelligent' means deterministic criteria matching and efficient data structures—not an external AI model.")
    a, b, c = st.columns(3)
    with a:
        with st.container(border=True):
            st.subheader("01 / Sorting")
            st.write("Merge Sort merges ordered subproblems. Quick Sort partitions around a pivot. Both rank actual applicant records and are verified against Python's built-in baseline.")
    with b:
        with st.container(border=True):
            st.subheader("02 / Heap")
            st.write("A bounded min-heap retains the best K applicants after explicit eligibility gates. Its root is the worst retained applicant; better arrivals replace it.")
    with c:
        with st.container(border=True):
            st.subheader("03 / Hashing")
            st.write("Dictionaries map candidate IDs to records. An inverted skill index uses sets for fast filtering, and hash-based grouping finds duplicate application IDs.")
    st.code("CSV / XLSX → map headings → validate every row\n             → normalize skills → explain scores\n             → heap suggestions + deterministic sorting\n             → ID / skill indexes → human review → exports", language="text")
    st.markdown("### Matching score, not predicted performance")
    st.latex(r"\mathrm{Match}=\sum_{i\in\mathrm{observed}}\mathrm{component}_i\times\frac{\mathrm{effective\ weight}_i}{100}")
    st.write("Each component is 0–100. Missing job components are excluded; unknown candidate experience/education also excludes those components and marks the result provisional. If no weighted evidence is available, the record stays visible as unscored. Blank skill cells are reported as empty sets. No names, emails, photographs, protected personal characteristics or other irrelevant sensitive inputs influence scores.")
    st.warning("Provisional scores can overstate apparent matches because evidence is incomplete. The system keeps these visible and flags them; a human must assess comparability, missing evidence and suitability.")
    st.dataframe(complexity_table(), hide_index=True, width="stretch")
    st.markdown("### Suggested faculty demonstration")
    st.markdown("1. Open Dashboard and explain that metrics come from the 72-row synthetic CSV.\n2. Upload a modified sample; introduce a duplicate application ID and invalid experience, then inspect all errors.\n3. Change required skills/weights and show a score explanation.\n4. Verify Merge Sort and Quick Sort against the same built-in reference.\n5. Set K=3 in Heap Laboratory; compare results and real timings.\n6. Retrieve a candidate by ID and intersect two skill buckets.\n7. Save a manual decision with a reason; show that score and rank stay unchanged.\n8. Run increasing-size benchmarks and export the shortlist, validation, explanation and benchmark reports.")
    st.markdown("### Scope & limitations")
    st.write("Session state is browser-session memory, not a database: refreshing/restarting may reset data. Normal page navigation preserves it. Skills and education use exact normalized labels, not fuzzy semantics. There is no resume parser, authentication, persistent audit log, automated hiring, legal/fairness certification or external AI integration. A custom hash table is optional and intentionally omitted; the core uses real built-in dict/set hashing.")
    st.caption("Technology: Python 3.11+, Pandas, Streamlit, heapq, dict/set, perf_counter, Plotly, OpenPyXL and Pytest. No paid API or cloud credentials are required.")
    human_review_note()
