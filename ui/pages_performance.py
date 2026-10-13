"""Separate theoretical analysis and empirically measured execution times."""
from __future__ import annotations

import streamlit as st

from ui.components import page_header
from ui.pages_labs import generated_controls, render_timing_bars
from ui.state import get_result, require_candidates
from utils.performance import benchmark_heap_vs_sort, benchmark_lookup, benchmark_sorting, complexity_table


def render() -> None:
    """Render measured comparisons separately from theoretical complexity."""
    page_header("DSA / performance", "Measure. Compare. Understand.", "Theoretical growth rates explain scalability; measured runtime describes this implementation on this machine.")
    tabs = st.tabs(["Current dataset", "Increasing input sizes", "Complexity & methodology"])
    with tabs[0]:
        if require_candidates(numeric_only=True):
            result = get_result()
            st.caption(f"{len(result.scored_candidates)} numeric candidates · upload-order input · active criteria: {result.requirements.title}")
            with st.form("current_performance_form"):
                a, b = st.columns(2)
                with a:
                    repeats = st.number_input("Timed repetitions", min_value=3, max_value=21, value=7, step=2)
                with b:
                    k = st.number_input("Top-K comparison size", min_value=0, max_value=1000000, value=result.requirements.shortlist_k, step=1)
                if st.form_submit_button("Measure all current-data algorithms", type="primary"):
                    records = result.source_order_candidates()
                    source = f"Current dataset: {st.session_state.jr_dataset_name}"
                    with st.spinner("Measuring real equivalent inputs and verifying outputs…"):
                        st.session_state.jr_current_sort_benchmark = benchmark_sorting(records, int(repeats), source=source)
                        st.session_state.jr_current_heap_benchmark = benchmark_heap_vs_sort(records, int(k), int(repeats), source=source)
                        st.session_state.jr_current_lookup_benchmark = benchmark_lookup(result.ranked_candidates, int(repeats), 200, source=source)
            for key, title in (("jr_current_sort_benchmark", "Sorting comparison"), ("jr_current_heap_benchmark", "Heap vs full sorting"), ("jr_current_lookup_benchmark", "Dictionary vs linear ID lookup")):
                measured = st.session_state.get(key)
                if measured is not None:
                    st.subheader(title)
                    render_timing_bars(measured)
            if st.session_state.get("jr_current_sort_benchmark") is None:
                st.info("No current-data measurement yet. Run the benchmark above; charts will use its actual results.")
    with tabs[1]:
        st.caption("Generated lab records use the same final_score/candidate_id ranking contract. They are separate from applicant dashboard data and never enter a recruiter shortlist. Seeds make inputs reproducible; runtimes are not expected to repeat exactly.")
        generated_controls("performance", include_heap=True)
    with tabs[2]:
        st.subheader("Theoretical complexity")
        st.dataframe(complexity_table(), hide_index=True, width="stretch")
        st.markdown("""
**N** = candidates, **K** = retained candidates, **T** = total normalized skill tokens,
**S/R** = candidate/required skill counts, **M** = IDs returned from a skill bucket.

**What the experiments measure**
- One warm-up per method, then 3–21 actual timed repetitions (generated suite: up to 15).
- `time.perf_counter()` measures each algorithm call. Reported statistic: **median**, with min/max and repetition count.
- Methods are rotated in order between repetitions. They receive equivalent, unmodified records with the same tie-break keys.
- File I/O, data generation, scoring, baseline construction and correctness checks are **outside** timed regions.
- Key extraction, heap/sort work and output allocation are **inside**. No timing values are fabricated or extrapolated.
- Hash tests use the same seeded batch of successful and missing-ID queries; index build time is measured separately.
- Every timed result must equal the reference, otherwise a benchmark fails visibly rather than publishing a success.

**Why runtime and Big-O differ**
Big-O describes growth and ignores constants. Python bytecode, optimized C implementations,
input order, K/N, cache behavior, memory allocation and background load change observed
milliseconds. A faster result for one size does not establish a universal winner.
Very small inputs can be dominated by timer/call overhead; repeat measurements and inspect
larger inputs. Space figures are theoretical; this project does not claim empirical peak-memory measurements.
        """)
