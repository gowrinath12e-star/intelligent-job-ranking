"""Purpose-limited, spreadsheet-safe CSV/Excel downloads produced in memory."""
from __future__ import annotations

import io
import json
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd
from openpyxl.styles import Font, PatternFill

from core.data_validation import ValidationResult
from core.scoring import COMPONENTS, COMPONENT_LABELS, JobRequirements

RANKED_FIELDS = {
    "rank": "Rank", "candidate_id": "Candidate ID", "name": "Display name",
    "final_score": "Job-criteria matching score (0-100)", "score_status": "Evidence status",
    "experience_years": "Experience (years)", "education": "Education label",
    "matched_required_skills": "Matched required skills", "missing_required_skills": "Missing required skills",
    "matched_additional_skills": "Matched additional skills", "eligibility_status": "Experience gate / review flag",
    "suggested_shortlist": "Heap suggestion", "is_shortlisted": "On review shortlist",
    "review_status": "Recruiter status", "review_note": "Review note",
    "shortlist_source": "Shortlist source", "shortlist_reason": "Shortlist reason",
}


def _cell(value: Any) -> Any:
    if isinstance(value, (list, tuple, set, frozenset)):
        return "; ".join(str(item) for item in sorted(value, key=str))
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return value


def spreadsheet_safe(frame: pd.DataFrame) -> pd.DataFrame:
    """Escape user-controlled formula prefixes in STRING cells, not numbers.

    A leading apostrophe neutralizes =,+,-,@, tab and carriage-return payloads.
    This is a deliberate export-only transformation, never a scoring change.
    """
    result = frame.copy()
    for column in result.columns:
        result[column] = result[column].map(_cell)
        result[column] = result[column].map(
            lambda value: "'" + value if isinstance(value, str)
            and (value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@"))) else value
        )
    return result


def ranked_frame(candidates: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Report only ranking/review fields, deliberately excluding contact emails."""
    return pd.DataFrame([{heading: _cell(candidate.get(field)) for field, heading in RANKED_FIELDS.items()}
                         for candidate in candidates], columns=list(RANKED_FIELDS.values()))


def breakdown_frame(candidates: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """One row per candidate/component, including renormalization and reasons."""
    columns = ["Rank", "Candidate ID", "Component", "Component score (0-100)", "Configured weight (%)",
               "Effective candidate weight (%)", "Contribution (points)", "Component status",
               "Matched required skills", "Missing required skills", "Education explanation",
               "Final matching score", "Evidence status", "Scoring notes"]
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        for component in COMPONENTS:
            rows.append({"Rank": candidate.get("rank"), "Candidate ID": candidate["candidate_id"],
                         "Component": COMPONENT_LABELS[component],
                         "Component score (0-100)": candidate["component_scores"][component],
                         "Configured weight (%)": candidate["configured_weights"][component],
                         "Effective candidate weight (%)": candidate["effective_weights"][component],
                         "Contribution (points)": candidate["weighted_contributions"][component],
                         "Component status": candidate["component_statuses"][component],
                         "Matched required skills": _cell(candidate["matched_required_skills"]),
                         "Missing required skills": _cell(candidate["missing_required_skills"]),
                         "Education explanation": candidate["education_reason"] if component == "education" else "",
                         "Final matching score": candidate["final_score"], "Evidence status": candidate["score_status"],
                         "Scoring notes": " | ".join(candidate["scoring_notes"])})
    return pd.DataFrame(rows, columns=columns)


def requirements_frame(requirements: JobRequirements) -> pd.DataFrame:
    """A compact reproducibility sheet describing the job configuration."""
    settings: dict[str, Any] = {
        "Job title": requirements.title, "Required skills": _cell(requirements.required_skills),
        "Additional skills": _cell(requirements.additional_skills), "Minimum experience": requirements.minimum_experience,
        "Target experience": requirements.target_experience, "Education rubric": _cell(dict(requirements.education_rubric)),
        "Unmatched education score": requirements.unmatched_education_score,
        "Configured weights (%)": _cell(requirements.weights.as_dict()),
        "Effective job weights (%)": _cell(requirements.effective_job_weights()),
        "Requested shortlist K": requirements.shortlist_k, "Score threshold": requirements.minimum_score,
        "Scoring rule": "Weighted sum; unknown experience/education excluded and observed weights renormalized; score provisional.",
        "Tie-break": "Descending matching score, then ascending lexical candidate ID.",
        "Purpose": "Human-review job-criteria matching; not predicted performance or automatic hiring.",
    }
    return pd.DataFrame([{"Setting": key, "Value": str(value) if value is not None else "Not configured"} for key, value in settings.items()])


def csv_bytes(frame: pd.DataFrame) -> bytes:
    """UTF-8 BOM CSV (Excel-friendly), with no artificial index column."""
    return spreadsheet_safe(frame).to_csv(index=False, lineterminator="\n").encode("utf-8-sig")


def excel_bytes(sheets: Mapping[str, pd.DataFrame]) -> bytes:
    """Create a styled modern .xlsx workbook; caller controls included sheets."""
    if not sheets:
        raise ValueError("At least one report sheet is required.")
    # Validate BEFORE opening the writer: failing inside its context manager
    # could attempt to save a workbook with no visible sheets and mask errors.
    used_names: set[str] = set()
    for name in sheets:
        if not name or len(name) > 31 or any(character in name for character in "[]:*?/\\") or name.lower() in used_names:
            raise ValueError("Excel sheet names must be unique, non-empty, valid, and at most 31 characters.")
        used_names.add(name.lower())
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            spreadsheet_safe(frame).to_excel(writer, sheet_name=name, index=False)
            sheet = writer.sheets[name]
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for cell in sheet[1]:
                cell.fill = PatternFill("solid", fgColor="087F8C")
                cell.font = Font(color="FFFFFF", bold=True)
            for column in sheet.columns:
                width = min(55, max(14, max(len(str(cell.value or "")) for cell in list(column)[:100]) + 2))
                sheet.column_dimensions[column[0].column_letter].width = width
    return buffer.getvalue()


def validation_issues_frame(validation: ValidationResult) -> pd.DataFrame:
    """Issues include IDs and source rows, not raw names/contact details."""
    return validation.issues.copy()


def validation_workbook(validation: ValidationResult) -> bytes:
    """Complete validation report without exporting ignored/sensitive columns.

    Correctable rejected rows can be downloaded separately in the Upload
    page, limited to known applicant fields plus errors. This workbook is
    intentionally issue-only (no extra source columns or contact details).
    """
    summary = pd.DataFrame([{"Metric": key, "Count": value} for key, value in validation.summary.items()])
    return excel_bytes({"Summary": summary, "Issues": validation_issues_frame(validation),
                        "Duplicate IDs": validation.duplicates, "Cleaning": validation.cleaning_summary})
