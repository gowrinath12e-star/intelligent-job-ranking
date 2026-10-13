"""Strict CSV/Excel loading and transparent, user-adjustable column mapping."""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import BinaryIO, Mapping
from zipfile import BadZipFile

import pandas as pd

CANONICAL_COLUMNS = (
    "candidate_id", "name", "email", "skills", "experience_years",
    "education", "additional_skills", "application_id",
)
REQUIRED_COLUMNS = ("candidate_id", "name", "skills")
MAX_FILE_BYTES = 20 * 1024 * 1024
ALIASES = {
    "candidate_id": ("candidate_id", "candidate_identifier", "candidateid", "applicant_id", "applicantid", "id"),
    "name": ("name", "candidate_name", "applicant_name", "full_name"),
    "email": ("email", "email_address", "e_mail"),
    "skills": ("skills", "skill", "technical_skills", "primary_skills"),
    "experience_years": ("experience_years", "years_of_experience", "experience", "exp", "work_experience"),
    "education": ("education", "qualification", "degree", "highest_qualification"),
    "additional_skills": ("additional_skills", "other_skills", "optional_skills", "relevant_skills"),
    "application_id": ("application_id", "applicationid", "application_identifier", "application_number"),
}


class DataLoadError(ValueError):
    """The file could not be loaded safely as a supported table."""


class ColumnMappingError(ValueError):
    """A column mapping is ambiguous or references an unknown column."""


def normalize_column_name(column: object) -> str:
    """Make headings comparable without modifying candidate cell values."""
    return re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower()).strip("_")


def suggest_column_mapping(columns: list[str]) -> dict[str, str]:
    """Suggest source-heading → canonical-heading mappings; users can override."""
    mapping: dict[str, str] = {}
    for column in columns:
        normalized = normalize_column_name(column)
        for canonical, alternatives in ALIASES.items():
            if normalized in alternatives:
                mapping[column] = canonical
                break
    return mapping


def apply_column_mapping(frame: pd.DataFrame, mapping: Mapping[str, str] | None = None) -> pd.DataFrame:
    """Return a copy; reject mappings that would overwrite or merge columns."""
    if frame.columns.duplicated().any():
        raise ColumnMappingError("Repeated source column headings are ambiguous. Rename them in the file.")
    selected = suggest_column_mapping(list(frame.columns)) if mapping is None else dict(mapping)
    unknown = set(selected) - set(frame.columns)
    if unknown:
        raise ColumnMappingError(f"Unknown source columns: {', '.join(sorted(unknown))}.")
    if any(target not in CANONICAL_COLUMNS for target in selected.values()):
        raise ColumnMappingError("Mapping targets must be one of the documented applicant fields.")
    names = [selected.get(column, column) for column in frame.columns]
    if len(names) != len(set(names)):
        raise ColumnMappingError("Two source columns map to the same field. Choose a unique source for each field.")
    return frame.rename(columns=selected).copy(deep=True)


def _read_bytes(source: str | Path | bytes | BinaryIO) -> bytes:
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.stat().st_size > MAX_FILE_BYTES:
            raise DataLoadError("File exceeds the 20 MB upload limit.")
        return path.read_bytes()
    if isinstance(source, bytes):
        return source
    position = source.tell() if hasattr(source, "tell") else None
    if hasattr(source, "seek"):
        source.seek(0)
    data = source.read(MAX_FILE_BYTES + 1)
    if position is not None and hasattr(source, "seek"):
        source.seek(position)
    if not isinstance(data, bytes):
        raise DataLoadError("Expected a binary file. Upload a CSV or .xlsx file.")
    return data


def load_applicants(source: str | Path | bytes | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """Load UTF-8 CSV or modern Excel without skipping malformed rows.

    Legacy .xls is intentionally not supported (it would require another
    dependency). Only the first worksheet is read; IDs stay as text where
    the source stores them as text. No upload is written to disk.
    """
    name = filename or (str(source) if isinstance(source, (str, Path)) else getattr(source, "name", ""))
    extension = Path(name).suffix.lower()
    if extension not in {".csv", ".xlsx"}:
        raise DataLoadError("Supported formats are .csv and .xlsx. Save legacy .xls as .xlsx first.")
    try:
        raw = _read_bytes(source)
        if len(raw) > MAX_FILE_BYTES:
            raise DataLoadError("File exceeds the 20 MB upload limit.")
        if not raw:
            raise DataLoadError("The uploaded file is empty. Include a header row.")
        if extension == ".csv":
            frame = pd.read_csv(io.BytesIO(raw), dtype=object, encoding="utf-8-sig", keep_default_na=False)
        else:
            with pd.ExcelFile(io.BytesIO(raw), engine="openpyxl") as workbook:
                if not workbook.book.worksheets:
                    raise DataLoadError("The Excel workbook has no worksheets.")
                header = next(workbook.book.worksheets[0].iter_rows(min_row=1, max_row=1, values_only=True), ())
                headings = [str(value) for value in header if value is not None]
                if len(headings) != len(set(headings)):
                    raise DataLoadError("The Excel header contains repeated column names.")
                frame = pd.read_excel(workbook, dtype=object, keep_default_na=False)
    except (OSError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError, BadZipFile, ValueError) as exc:
        if isinstance(exc, DataLoadError):
            raise
        raise DataLoadError(f"Could not read {extension} file: {exc}. CSV files must use UTF-8 encoding.") from exc
    if len(set(frame.columns)) != len(frame.columns):
        raise DataLoadError("The file has ambiguous repeated headings.")
    # Pandas may suffix repeated CSV headings, so check the literal header too.
    if extension == ".csv":
        import csv
        header = next(csv.reader(io.StringIO(raw.decode("utf-8-sig"))), [])
        if len(header) != len(set(header)):
            raise DataLoadError("The CSV header contains repeated column names.")
    return frame
