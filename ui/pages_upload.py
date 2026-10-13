"""Two-step file ingestion: preview/map first, validate/replace explicitly."""
from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from core.data_loader import CANONICAL_COLUMNS, REQUIRED_COLUMNS, ColumnMappingError, DataLoadError, load_applicants, suggest_column_mapping
from core.data_validation import SchemaValidationError
from ui.components import metric_cards, page_header
from ui.state import SAMPLE_PATH, flash, get_result, import_dataset
from utils.exports import csv_bytes, validation_workbook


def render() -> None:
    """Render the upload/mapping workflow and complete validation reports."""
    page_header("Data workspace", "Upload & validate applicants", "CSV or Excel in, traceable validation out. No rejected row is silently discarded.")
    left, right = st.columns([2, 1], gap="large")
    with right:
        with st.container(border=True):
            st.subheader("A dataset to start with")
            st.write("72 synthetic applicants, varied skills and experience, and a few deliberately unknown optional values.")
            st.download_button("Download sample CSV", SAMPLE_PATH.read_bytes(), "sample_applicants.csv", "text/csv", on_click="ignore", width="stretch")
            if st.button("Load the synthetic sample", width="stretch"):
                import_dataset(load_applicants(SAMPLE_PATH), None, "Synthetic sample · 72 applicants")
                flash("Synthetic sample loaded. Review choices were reset; your job criteria were retained.")
                st.rerun()
            st.caption("Required headings: candidate_id, name, skills. Optional: email, experience_years, education, additional_skills, application_id.")
    with left:
        uploaded = st.file_uploader("Choose an applicant file", type=["csv", "xlsx"], help="UTF-8 CSV or modern .xlsx, up to 20 MB. First Excel worksheet only. Uploads are processed in memory.")
        st.caption("Importing replaces the active dataset and resets its review decisions. Requirements stay unchanged. Only explicitly mapped applicant fields affect processing.")
        if uploaded is not None:
            raw_bytes = uploaded.getvalue()
            signature = hashlib.sha256(raw_bytes).hexdigest()
            try:
                if st.session_state.get("jr_pending_signature") != signature:
                    st.session_state.jr_pending_frame = load_applicants(raw_bytes, uploaded.name)
                    st.session_state.jr_pending_signature = signature
                pending = st.session_state.jr_pending_frame
                st.caption(f"Loaded for preview: {len(pending):,} rows · {len(pending.columns)} source columns · not yet imported")
                st.dataframe(pending.head(10).fillna("").astype(str), hide_index=True, width="stretch")
                suggestions = suggest_column_mapping(list(pending.columns))
                with st.form("column_mapping_" + signature[:12]):
                    st.subheader("Map your columns")
                    selected: dict[str, str] = {}
                    duplicate_sources: list[str] = []
                    columns = st.columns(2)
                    options = ["(not supplied)"] + list(pending.columns)
                    for position, canonical in enumerate(CANONICAL_COLUMNS):
                        source = next((column for column, target in suggestions.items() if target == canonical), "(not supplied)")
                        label = canonical + (" *" if canonical in REQUIRED_COLUMNS else "")
                        with columns[position % 2]:
                            choice = st.selectbox(label, options, index=options.index(source), key=f"mapping_{signature[:12]}_{canonical}")
                        if choice != "(not supplied)":
                            if choice in selected:
                                duplicate_sources.append(choice)
                            selected[choice] = canonical
                    submitted = st.form_submit_button("Validate & import applicants", type="primary", width="stretch")
                    if submitted:
                        if duplicate_sources:
                            st.error("Choose each source column once. Repeated selections: " + ", ".join(duplicate_sources))
                        else:
                            # Ignore unselected canonical headings too, otherwise a
                            # '(not supplied)' selection could secretly use a column.
                            subset = pending.loc[:, list(selected)].copy()
                            if not len(subset.columns):
                                raise SchemaValidationError("Map the three required columns before importing.")
                            result = import_dataset(subset, selected, uploaded.name)
                            flash(f"Import complete: {result.summary['valid']} valid, {result.summary['invalid']} invalid out of {result.summary['uploaded']} rows. See the issue report below.")
                            st.rerun()
            except (DataLoadError, ColumnMappingError, SchemaValidationError) as exc:
                st.error(str(exc))
                st.caption("The previous active dataset has not been replaced.")
    st.divider()
    result = get_result()
    validation = result.validation
    st.subheader("Current validation report")
    st.caption(st.session_state.jr_dataset_name)
    metric_cards([
        ("Uploaded rows", str(validation.summary["uploaded"]), "Header not counted"),
        ("Valid records", str(validation.summary["valid"]), "Accepted for transparent scoring"),
        ("Invalid records", str(validation.summary["invalid"]), "Rejected rows preserved in the report"),
        ("Warnings", str(validation.summary["warning_count"]), "Missing information and cleaning notes"),
        ("Duplicate groups", str(validation.summary["duplicate_groups"]), "IDs, never names"),
    ], accent_index=1)
    tabs = st.tabs(["Validated preview", "Validation issues", "Invalid records", "Cleaning & duplicate IDs"])
    with tabs[0]:
        st.dataframe(validation.valid_data, hide_index=True, width="stretch")
        st.caption("Missing experience/education stay unknown. Missing optional application IDs are deterministically generated and reported.")
    with tabs[1]:
        severity = st.selectbox("Issue severity", ["All", "error", "warning"])
        issues = validation.issues if severity == "All" else validation.issues.loc[validation.issues.severity == severity]
        if issues.empty:
            st.success("No issues in this selection.")
        st.dataframe(issues, hide_index=True, width="stretch")
        st.download_button("Download validation workbook", validation_workbook(validation), "data_validation_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore")
    with tabs[2]:
        # Purpose-limited correction report: NEVER include arbitrary uploaded
        # columns (they could be sensitive and are not used by this application).
        known = [column for column in list(CANONICAL_COLUMNS) + ["source_row", "validation_errors"] if column in validation.invalid_data.columns]
        invalid = validation.invalid_data.loc[:, known]
        if invalid.empty:
            st.success("No invalid records. All loaded rows were accounted for.")
        else:
            st.error(f"{len(invalid)} records were not ranked. Correct the listed errors and re-upload the file.")
        st.dataframe(invalid.fillna("").astype(str), hide_index=True, width="stretch")
        st.download_button("Download rejected rows for correction", csv_bytes(invalid), "invalid_records_for_correction.csv", "text/csv", on_click="ignore")
    with tabs[3]:
        st.markdown("**Actual cleaning operations**")
        st.dataframe(validation.cleaning_summary, hide_index=True, width="stretch")
        st.markdown("**Duplicate identifier groups**")
        st.dataframe(validation.duplicates, hide_index=True, width="stretch")
        if validation.ignored_columns:
            st.info("Ignored unmapped/extra columns: " + ", ".join(validation.ignored_columns) + ". They are not used for scores or standard exports.")
    with st.expander("Start an empty workspace"):
        confirmed = st.checkbox("I understand this clears the current applicant data and review decisions.")
        if st.button("Clear applicant dataset", disabled=not confirmed):
            import_dataset(pd.DataFrame(columns=REQUIRED_COLUMNS), None, "Empty workspace")
            flash("Applicant dataset cleared. Load the sample or import a file when ready.", "info")
            st.rerun()
