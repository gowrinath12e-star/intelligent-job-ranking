"""Sorting, heap and hashing experiments linked to the real ranking workflow."""
from __future__ import annotations

from time import perf_counter

import pandas as pd
import plotly.express as px
import streamlit as st

from algorithms.heap_ranking import top_k_candidates
from algorithms.sorting import SORT_ALGORITHMS, builtin_sort
from ui.components import PALETTE, candidate_table, chart_style, page_header, score_breakdown
from ui.state import get_result, require_candidates
from utils.exports import csv_bytes
from utils.performance import benchmark_heap_vs_sort, benchmark_lookup, benchmark_sorting, complexity_table, run_generated_benchmarks


def render_sorting() -> None:
    """Run actual sorting implementations on current numeric applicants."""
    page_header("DSA / sorting", "Sorting laboratory", "Divide, partition, and compare. Each implementation follows one deterministic ranking contract.")
    if not require_candidates(numeric_only=True):
        return
    result = get_result()
    records = result.source_order_candidates()
    a, b = st.columns([2, 1])
    with a:
        algorithm = st.selectbox("Algorithm to run", list(SORT_ALGORITHMS), key="sort_lab_algorithm")
    with b:
        repeats = st.number_input("Timing repetitions", min_value=3, max_value=21, value=7, step=2, key="sort_lab_repeats")
    st.caption(f"Input: {len(records):,} scored applicants in original upload order. Data loading/scoring and reference generation are outside the timing interval; key extraction and output allocation are inside.")
    a, b = st.columns(2)
    with a:
        if st.button("Run selected sort & verify", type="primary", width="stretch"):
            started = perf_counter()
            output = SORT_ALGORITHMS[algorithm](records)
            elapsed = (perf_counter() - started) * 1000
            verified = output == builtin_sort(records)
            st.session_state.jr_sort_lab_output = {"algorithm": algorithm, "output": output, "elapsed_ms": elapsed, "verified": verified}
    with b:
        if st.button("Compare all three on this dataset", width="stretch"):
            st.session_state.jr_current_sort_benchmark = benchmark_sorting(records, int(repeats), source=f"Current dataset: {st.session_state.jr_dataset_name}")
    output = st.session_state.get("jr_sort_lab_output")
    if output:
        st.success(f"{output['algorithm']}: {output['elapsed_ms']:.4f} ms (single run). Reference agreement: {output['verified']}.") if output["verified"] else st.error("Reference mismatch. Do not use these rankings.")
        candidate_table(output["output"], height=300)
    measured = st.session_state.get("jr_current_sort_benchmark")
    if measured is not None:
        st.subheader("Current-data timing comparison")
        render_timing_bars(measured)
    with st.expander("Benchmark increasing generated input sizes", expanded=False):
        generated_controls("sort", include_heap=False)
    with st.expander("How the sorting algorithms work"):
        st.markdown("**Merge Sort:** start with singleton runs and repeatedly merge two ordered runs. No recursion limit; O(N log N) in all cases.\n\n**Quick Sort:** median-of-three pivot, real three-way partitioning, and an explicit stack processing small partitions first. It avoids Python recursion depth, but adversarial inputs can still take O(N²).\n\n**Python built-in:** Timsort is an optimized, adaptive baseline; often fast, especially for ordered data. The observed winner depends on input, implementation and environment.")
        st.dataframe(complexity_table().iloc[:3], hide_index=True, width="stretch")


def render_heap() -> None:
    """Experiment with bounded-heap top-K selection against full sorting."""
    page_header("DSA / priority queue", "Heap laboratory", "Retain only the best K while scanning N applicants, then rank the retained subset.")
    if not require_candidates(numeric_only=True):
        return
    result = get_result()
    records = result.source_order_candidates()
    a, b, c = st.columns(3)
    with a:
        k = st.number_input("Candidates to request (K)", min_value=0, max_value=max(1000, len(records) * 2), value=min(result.requirements.shortlist_k, max(1000, len(records) * 2)), step=1, key="heap_lab_k")
    with b:
        repeats = st.number_input("Timing repetitions", min_value=3, max_value=21, value=7, step=2, key="heap_lab_repeats")
    with c:
        apply_gates = st.checkbox("Apply active shortlist eligibility gates", value=False, help="Include known-minimum-experience and matching-score gates. Unknown experience remains flagged, not silently excluded.")
    if apply_gates:
        records = [record for record in records if record["automatic_eligible"]
                   and (result.requirements.minimum_score is None or record["final_score"] >= result.requirements.minimum_score)]
    st.caption(f"Applicants scanned: {len(records):,} · requested K: {int(k)} · expected output: {min(int(k), len(records)):,}. Laboratory output is an experiment; it does not overwrite recruiter decisions.")
    if st.button("Select top K, compare & verify", type="primary"):
        output = top_k_candidates(records, int(k))
        measurements = benchmark_heap_vs_sort(records, int(k), int(repeats), source=f"Current dataset: {st.session_state.jr_dataset_name}; gates={apply_gates}")
        st.session_state.jr_heap_lab_output = {"candidates": output, "k": int(k), "n": len(records), "verified": output == builtin_sort(records)[:int(k)]}
        st.session_state.jr_current_heap_benchmark = measurements
    output = st.session_state.get("jr_heap_lab_output")
    if output:
        st.success(f"Heap result verified: {output['verified']} · {len(output['candidates'])} returned from N={output['n']}, K={output['k']}.")
        candidate_table(output["candidates"], height=300)
    measured = st.session_state.get("jr_current_heap_benchmark")
    if measured is not None:
        render_timing_bars(measured)
    st.info("A heap is useful when K is much smaller than N, only top-K results are needed, or applicants arrive as a stream. Full sorting is useful for the entire ranking or many later rank queries. CPython's optimized sort can still beat a Python heap on some measured inputs; asymptotics are not a speed guarantee.")
    st.markdown("**Heap invariant:** the root is the worst of the current best K. A better incoming applicant replaces the root. Reversed rank keys preserve score-descending/ID-ascending ties; dictionaries are never compared.")
    st.caption("Heap scan: O(N log K), plus O(K log K) to rank the retained output. O(K) working heap space; K=1 is O(N), K=0 returns immediately, K>N retains at most N. Invalid negative/noninteger/boolean K is rejected by the reusable function.")


def render_hashing() -> None:
    """Demonstrate the live ID/skill indexes and duplicate-identifier report."""
    page_header("DSA / dictionaries & sets", "Hashing laboratory", "Instant ID lookup, inverted skill indexes, and set intersections—all used by the application.")
    result = get_result()
    if require_candidates():
        left, right = st.columns([1, 1.4], gap="large")
        with left:
            with st.form("hash_lookup"):
                candidate_id = st.text_input("Candidate ID to retrieve", value=result.ranked_candidates[0]["candidate_id"])
                submitted = st.form_submit_button("Look up candidate", type="primary", width="stretch")
            if submitted:
                st.session_state.jr_hash_lookup_id = candidate_id.strip()
            lookup_id = st.session_state.get("jr_hash_lookup_id")
            if lookup_id:
                record = result.index.lookup(lookup_id)
                if record is None:
                    st.warning(f"No candidate found with ID '{lookup_id}'. Dictionary.get returned None.")
                else:
                    st.success(f"Found {record['candidate_id']} with one dictionary lookup (average O(1)).")
            skills = st.multiselect("Skills to search", sorted(result.index.skill_to_candidate_ids), default=["python"] if "python" in result.index.skill_to_candidate_ids else [], key="hash_skills")
            mode = st.radio("Combine skill buckets", ["All skills (intersection)", "Any skill (union)"], key="hash_mode")
            matches = result.index.with_skills(skills, "all" if mode.startswith("All") else "any")
            st.caption(f"{len(matches)} candidates found. An empty filter returns the entire validated pool. The bucket dictionary access is O(1) average; returning/combining IDs also costs time proportional to the set sizes.")
            st.code("candidate = candidates_by_id.get(candidate_id)\nmatched = candidate_skills & required_skills\nmissing = required_skills - candidate_skills", language="python")
        with right:
            matches_ordered = [record for record in result.ranked_candidates if record["candidate_id"] in matches]
            candidate_table(matches_ordered, height=340)
            if lookup_id and (record := result.index.lookup(lookup_id)):
                with st.expander("Retrieved record: skill match and score explanation", expanded=False):
                    score_breakdown(record)
        with st.expander("Inspect the inverted index"):
            st.dataframe(pd.DataFrame([{"Normalized skill": skill, "Candidate count": len(ids), "Candidate IDs": ", ".join(sorted(ids))}
                                       for skill, ids in sorted(result.index.skill_to_candidate_ids.items())]), hide_index=True, width="stretch")
        if st.button("Measure dictionary vs linear ID lookup"):
            st.session_state.jr_current_lookup_benchmark = benchmark_lookup(result.ranked_candidates, repeats=7, query_count=200, source=f"Current dataset: {st.session_state.jr_dataset_name}")
        measured = st.session_state.get("jr_current_lookup_benchmark")
        if measured is not None:
            st.subheader("Measured batch of equivalent ID queries")
            render_timing_bars(measured)
            st.caption("Index-build time is reported separately, outside lookup timing. Each method receives the same seeded query list including missing IDs; reported latency is a batch median, not a fabricated single-lookup value.")
    st.subheader("Duplicate-identifier report")
    if result.validation.duplicates.empty:
        st.success("No duplicate candidate or application IDs in the active input.")
    st.dataframe(result.validation.duplicates, hide_index=True, width="stretch")
    st.caption("Detection uses one dictionary pass. All ambiguous occurrences are reported and rejected before ID indexing. Names are never used to deduplicate applicants. Hash lookups are O(1) average, but can degrade to O(N) under worst-case collisions.")


def render_timing_bars(measured: pd.DataFrame) -> None:
    """Show verified median runtimes, raw statistics and a working CSV download."""
    figure = px.bar(measured, x="algorithm", y="median_ms", color="algorithm", color_discrete_sequence=PALETTE,
                    labels={"algorithm": "Algorithm", "median_ms": "Median measured runtime (ms)"},
                    hover_data=["n", "repetitions", "min_ms", "max_ms", "verified"])
    figure.update_layout(showlegend=False)
    st.plotly_chart(chart_style(figure, 280), width="stretch")
    st.dataframe(measured, hide_index=True, width="stretch")
    st.download_button("Download these measurements · CSV", csv_bytes(measured), "benchmark_measurements.csv", "text/csv", on_click="ignore", key="measure_download_" + str(measured.algorithm.iloc[0]))


def generated_controls(prefix: str, include_heap: bool = True) -> None:
    """Shared real benchmark controls; all measurements persist for export."""
    with st.form(f"generated_benchmark_{prefix}"):
        sizes = st.multiselect("Input sizes (N)", [100, 500, 1000, 2500, 5000, 10000, 25000], default=[100, 1000, 5000], key=f"{prefix}_sizes")
        a, b, c = st.columns(3)
        with a:
            repeats = st.number_input("Repetitions per method", min_value=3, max_value=15, value=5, step=2, key=f"{prefix}_gen_repeats")
        with b:
            order = st.selectbox("Input order", ["random", "sorted", "reverse", "many ties"], key=f"{prefix}_order")
        with c:
            seed = st.number_input("Reproducible seed", min_value=0, max_value=999999, value=42, step=1, key=f"{prefix}_seed")
        k = st.number_input("Top-K for heap comparison", min_value=0, max_value=1000, value=25, step=1, key=f"{prefix}_gen_k") if include_heap else 25
        submitted = st.form_submit_button("Run measured benchmarks", type="primary", width="stretch")
    if submitted:
        if not sizes:
            st.error("Choose at least one input size.")
        else:
            with st.spinner("Generating equivalent inputs, warming methods, measuring repetitions and verifying results…"):
                tables = run_generated_benchmarks(sizes, int(repeats), int(seed), order, int(k), include_heap=include_heap, include_lookup=include_heap)
            st.session_state.jr_generated_sort_benchmark = tables["sorting"]
            if include_heap:
                st.session_state.jr_generated_heap_benchmark = tables["heap"]
                st.session_state.jr_generated_lookup_benchmark = tables["lookup"]
            else:
                st.session_state.pop("jr_generated_heap_benchmark", None)
                st.session_state.pop("jr_generated_lookup_benchmark", None)
            st.success("Measurements complete. Data generation and reference construction were excluded from algorithm timing.")
    for key, title in (("jr_generated_sort_benchmark", "Sorting scalability"), ("jr_generated_heap_benchmark", "Heap vs full sort scalability"), ("jr_generated_lookup_benchmark", "Hash vs linear lookup scalability")):
        if not include_heap and key != "jr_generated_sort_benchmark":
            continue
        measured = st.session_state.get(key)
        if measured is not None and not measured.empty:
            st.subheader(title)
            y = "median_us_per_query" if key.endswith("lookup_benchmark") else "median_ms"
            label = "Median per query (µs)" if y == "median_us_per_query" else "Median measured runtime (ms)"
            figure = px.line(measured, x="n", y=y, color="algorithm", markers=True, color_discrete_sequence=PALETTE,
                             labels={"n": "Applicants (N)", y: label, "algorithm": "Method"}, hover_data=["input_order", "seed", "repetitions", "verified"])
            st.plotly_chart(chart_style(figure, 320), width="stretch")
            st.dataframe(measured, hide_index=True, width="stretch")
