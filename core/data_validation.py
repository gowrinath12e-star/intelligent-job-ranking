"""Row-level validation with complete issue and rejected-record reporting."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from algorithms.hashing import duplicate_identifier_positions
from core.data_loader import CANONICAL_COLUMNS, REQUIRED_COLUMNS, apply_column_mapping
from core.normalization import is_missing, normalize_education, normalize_identifier, skill_text

MAX_EXPERIENCE_YEARS = 80.0
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ISSUE_COLUMNS = ["source_row", "candidate_id", "severity", "field", "code", "message"]
DUPLICATE_COLUMNS = ["identifier_type", "identifier", "source_rows", "candidate_ids", "occurrences"]
VALID_COLUMNS = list(CANONICAL_COLUMNS) + ["source_row", "validation_warnings"]


class SchemaValidationError(ValueError):
    """Required headings are missing; no rows can be validated yet."""


@dataclass
class ValidationResult:
    """All accepted/rejected rows, messages, and real cleaning statistics."""

    valid_data: pd.DataFrame
    invalid_data: pd.DataFrame
    issues: pd.DataFrame
    duplicates: pd.DataFrame
    summary: dict[str, int]
    cleaning_summary: pd.DataFrame
    ignored_columns: tuple[str, ...] = ()

    def records(self) -> list[dict[str, Any]]:
        """Convert Pandas missing scalars back to None for the scoring engine."""
        return self.valid_data.astype(object).where(pd.notna(self.valid_data), None).to_dict("records")


def validate_applicants(frame: pd.DataFrame, column_mapping: Mapping[str, str] | None = None) -> ValidationResult:
    """Validate without silently dropping, deduplicating, or imputing records.

    Candidate ID, name and skills headings are required. A blank skills cell
    is an empty set (reported as a warning). Experience/education remain
    unknown when absent. All rows in an ambiguous duplicate-ID group are
    rejected; identical names alone NEVER identify duplicate people.
    """
    mapped = apply_column_mapping(frame, column_mapping)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(mapped.columns))
    if missing_columns:
        raise SchemaValidationError("Missing required columns: " + ", ".join(missing_columns) + ". Use column mapping or correct the file.")
    ignored = tuple(str(column) for column in mapped.columns if column not in CANONICAL_COLUMNS)
    original_rows = mapped.to_dict("records")
    for column in CANONICAL_COLUMNS:
        if column not in mapped:
            mapped[column] = None
    cleaned: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    row_errors: dict[int, list[str]] = defaultdict(list)
    row_warnings: dict[int, list[str]] = defaultdict(list)
    cleaning: Counter[str] = Counter()

    def add_issue(position: int, field: str, code: str, message: str, severity: str = "error") -> None:
        issues.append({"source_row": position + 2, "candidate_id": cleaned[position].get("candidate_id", ""),
                       "severity": severity, "field": field, "code": code, "message": message})
        (row_errors if severity == "error" else row_warnings)[position].append(message)

    for position, raw in enumerate(mapped.to_dict("records")):
        record: dict[str, Any] = {column: None for column in CANONICAL_COLUMNS}
        record["source_row"] = position + 2
        cleaned.append(record)
        try:
            record["candidate_id"] = normalize_identifier(raw["candidate_id"])
            if str(raw["candidate_id"]) != record["candidate_id"]:
                cleaning["Candidate identifiers normalized"] += 1
        except ValueError as exc:
            add_issue(position, "candidate_id", "invalid_candidate_id", f"Candidate ID: {exc}")
        name = raw["name"]
        if is_missing(name) or not isinstance(name, str):
            add_issue(position, "name", "missing_or_invalid_name", "Name must be non-empty text; it is not used for scoring.")
        else:
            record["name"] = name.strip()
            if record["name"] != name:
                cleaning["Names trimmed"] += 1
        email = raw["email"]
        if is_missing(email):
            add_issue(position, "email", "missing_email", "Email is missing; the record remains valid and contact information is not scored.", "warning")
        elif not isinstance(email, str) or not EMAIL_PATTERN.fullmatch(email.strip()):
            add_issue(position, "email", "invalid_email", "Provided email is not a valid email address; correct it or leave the optional cell blank.")
        else:
            record["email"] = email.strip()
        for field in ("skills", "additional_skills"):
            try:
                record[field] = skill_text(raw[field])
                if is_missing(raw[field]):
                    add_issue(position, field, "missing_skills", f"{field.replace('_', ' ').title()} not supplied; interpreted as an explicitly reported empty skill set.", "warning")
                elif str(raw[field]) != record[field]:
                    cleaning["Skill cells normalized / deduplicated"] += 1
            except ValueError as exc:
                add_issue(position, field, "invalid_skills_type", str(exc))
        experience = raw["experience_years"]
        if is_missing(experience):
            add_issue(position, "experience_years", "missing_experience", "Experience is unknown, not zero. A configured experience score will be marked unavailable.", "warning")
        else:
            try:
                if isinstance(experience, bool) or isinstance(experience, (dict, list, tuple, set)):
                    raise ValueError
                years = float(experience)
                if not math.isfinite(years) or not 0 <= years <= MAX_EXPERIENCE_YEARS:
                    raise ValueError
                record["experience_years"] = years
                if not isinstance(experience, (int, float)):
                    cleaning["Experience values converted to numeric"] += 1
            except (TypeError, ValueError, OverflowError):
                add_issue(position, "experience_years", "invalid_experience", f"Experience must be a finite number from 0 to {MAX_EXPERIENCE_YEARS:g} years, or blank if unknown.")
        try:
            record["education"] = normalize_education(raw["education"])
            if record["education"] is None:
                add_issue(position, "education", "missing_education", "Education is unknown, not zero. A configured education score will be marked unavailable.", "warning")
            elif record["education"] != raw["education"]:
                cleaning["Education labels normalized"] += 1
        except ValueError as exc:
            add_issue(position, "education", "invalid_education_type", str(exc))
        application = raw["application_id"]
        if is_missing(application):
            if record["candidate_id"]:
                identifier = record["candidate_id"]
                if len(identifier) > 60:
                    from hashlib import sha256
                    identifier = sha256(identifier.encode("utf-8")).hexdigest()[:32]
                record["application_id"] = "APP-" + identifier
                cleaning["Application identifiers generated"] += 1
                add_issue(position, "application_id", "generated_application_id", f"Missing optional application ID: generated {record['application_id']} from candidate ID.", "warning")
        else:
            try:
                record["application_id"] = normalize_identifier(application)
            except ValueError as exc:
                add_issue(position, "application_id", "invalid_application_id", f"Application ID: {exc}")

    duplicate_rows: list[dict[str, Any]] = []
    for field in ("candidate_id", "application_id"):
        for identifier, positions in duplicate_identifier_positions(cleaned, field).items():
            source_rows = [position + 2 for position in positions]
            candidate_ids = [cleaned[position].get("candidate_id") or "(invalid ID)" for position in positions]
            duplicate_rows.append({"identifier_type": field, "identifier": identifier,
                                   "source_rows": "; ".join(map(str, source_rows)),
                                   "candidate_ids": "; ".join(candidate_ids), "occurrences": len(positions)})
            for position in positions:
                add_issue(position, field, "duplicate_" + field,
                          f"Duplicate {field}: {identifier}; all occurrences at rows {source_rows} require resolution.")
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for position, record in enumerate(cleaned):
        record["validation_warnings"] = " | ".join(row_warnings.get(position, []))
        if position in row_errors:
            rejected.append({**original_rows[position], "source_row": position + 2,
                             "validation_errors": " | ".join(row_errors[position])})
        else:
            accepted.append(record)
    invalid_columns = list(frame.rename(columns=column_mapping or {}).columns)
    for extra in ["source_row", "validation_errors"]:
        if extra not in invalid_columns:
            invalid_columns.append(extra)
    valid_frame = pd.DataFrame(accepted, columns=VALID_COLUMNS)
    invalid_frame = pd.DataFrame(rejected) if rejected else pd.DataFrame(columns=invalid_columns)
    summary = {"uploaded": len(frame), "valid": len(accepted), "invalid": len(rejected),
               "records_with_warnings": len(row_warnings),
               "error_count": sum(issue["severity"] == "error" for issue in issues),
               "warning_count": sum(issue["severity"] == "warning" for issue in issues),
               "duplicate_groups": len(duplicate_rows)}
    cleaning_frame = pd.DataFrame([{"action": action, "affected_cells_or_records": count}
                                   for action, count in sorted(cleaning.items())],
                                  columns=["action", "affected_cells_or_records"])
    return ValidationResult(valid_frame, invalid_frame, pd.DataFrame(issues, columns=ISSUE_COLUMNS),
                            pd.DataFrame(duplicate_rows, columns=DUPLICATE_COLUMNS), summary, cleaning_frame, ignored)
