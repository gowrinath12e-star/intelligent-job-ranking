"""File loading, schema mapping, missing values and complete rejection reports."""
import io
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

from core.data_loader import ColumnMappingError, DataLoadError, apply_column_mapping, load_applicants
from core.data_validation import SchemaValidationError, validate_applicants
from core.normalization import normalize_identifier


def test_valid_csv(applicant_frame):
    data = applicant_frame.to_csv(index=False).encode("utf-8")
    result = validate_applicants(load_applicants(data, "input.csv"))
    assert result.summary["valid"] == 2
    assert result.summary["invalid"] == 0
    assert result.valid_data.iloc[0].skills == "git; pandas; python; sql"


def test_valid_excel(applicant_frame):
    buffer = io.BytesIO()
    applicant_frame.to_excel(buffer, index=False, engine="openpyxl")
    result = validate_applicants(load_applicants(buffer.getvalue(), "input.xlsx"))
    assert result.summary["valid"] == 2


def test_automatic_heading_mapping(applicant_frame):
    alternate = applicant_frame.rename(columns={"candidate_id": "Applicant ID", "name": "Full Name", "skills": "Technical Skills", "experience_years": "Years of Experience"})
    assert validate_applicants(alternate).summary["valid"] == 2


def test_manual_column_mapping(applicant_frame):
    alternate = applicant_frame.rename(columns={"candidate_id": "identifier_xyz"})
    result = validate_applicants(alternate, {"identifier_xyz": "candidate_id"})
    assert result.summary["valid"] == 2


@pytest.mark.parametrize("column", ["candidate_id", "name", "skills"])
def test_missing_required_columns(applicant_frame, column):
    with pytest.raises(SchemaValidationError, match=column):
        validate_applicants(applicant_frame.drop(columns=[column]))


@pytest.mark.parametrize("value", [-1, 81, "bad", "inf", True, [3]])
def test_invalid_experience(candidate, value):
    result = validate_applicants(pd.DataFrame([{**candidate, "experience_years": value}]))
    assert result.summary["invalid"] == 1
    assert "invalid_experience" in result.issues.code.tolist()
    assert len(result.invalid_data) == 1


@pytest.mark.parametrize("field", ["candidate_id", "application_id"])
def test_duplicate_identifiers_reject_every_occurrence(applicant_frame, field):
    applicant_frame.loc[1, field] = applicant_frame.loc[0, field]
    result = validate_applicants(applicant_frame)
    assert result.summary["invalid"] == 2
    assert result.summary["valid"] == 0
    assert result.summary["duplicate_groups"] == 1
    assert result.duplicates.iloc[0].source_rows == "2; 3"


def test_same_name_is_not_duplicate(applicant_frame):
    applicant_frame.loc[1, "name"] = applicant_frame.loc[0, "name"]
    assert validate_applicants(applicant_frame).summary["valid"] == 2


def test_missing_optional_values_retained(candidate):
    frame = pd.DataFrame([{key: value for key, value in candidate.items() if key not in {"email", "education", "experience_years", "additional_skills", "application_id"}}])
    result = validate_applicants(frame)
    assert result.summary["valid"] == 1
    record = result.records()[0]
    assert record["experience_years"] is None
    assert record["education"] is None
    assert record["application_id"] == "APP-C001"
    assert result.summary["warning_count"] == 5


def test_empty_with_schema():
    result = validate_applicants(pd.DataFrame(columns=["candidate_id", "name", "skills"]))
    assert result.summary["uploaded"] == 0
    assert result.valid_data.empty and result.invalid_data.empty and result.issues.empty


def test_header_only_csv():
    result = validate_applicants(load_applicants(b"candidate_id,name,skills\n", "input.csv"))
    assert result.summary["uploaded"] == 0


def test_mixed_valid_invalid_accounted(applicant_frame):
    applicant_frame.loc[1, "experience_years"] = -1.0
    result = validate_applicants(applicant_frame)
    assert result.summary["uploaded"] == result.summary["valid"] + result.summary["invalid"]
    assert result.summary["valid"] == 1
    assert result.invalid_data.iloc[0].source_row == 3


@pytest.mark.parametrize("value", ["", "has space", "=FORMULA", -2, 1.5, True, None, "x" * 65])
def test_candidate_id_validation(candidate, value):
    result = validate_applicants(pd.DataFrame([{**candidate, "candidate_id": value}]))
    assert result.summary["invalid"] == 1


def test_leading_zero_id_preserved():
    frame = load_applicants(b"candidate_id,name,skills\n001,Synthetic One,python\n", "input.csv")
    assert validate_applicants(frame).records()[0]["candidate_id"] == "001"


def test_long_id_generated_application_is_valid(candidate):
    frame = pd.DataFrame([{**candidate, "candidate_id": "X" * 64, "application_id": None}])
    record = validate_applicants(frame).records()[0]
    assert normalize_identifier(record["application_id"]) == record["application_id"]


def test_optional_provided_invalid_types(candidate):
    frame = pd.DataFrame([{**candidate, "education": 42, "skills": 42, "email": "invalid"}])
    result = validate_applicants(frame)
    assert result.summary["invalid"] == 1
    assert {"invalid_education_type", "invalid_skills_type", "invalid_email"} <= set(result.issues.code)


def test_empty_skills_explicit_warning(candidate):
    result = validate_applicants(pd.DataFrame([{**candidate, "skills": ""}]))
    assert result.summary["valid"] == 1
    assert "missing_skills" in result.issues.code.tolist()


def test_ignore_unrelated_fields(candidate):
    result = validate_applicants(pd.DataFrame([{**candidate, "gender": "irrelevant"}]))
    assert result.ignored_columns == ("gender",)
    assert "gender" not in result.valid_data


def test_mapping_conflicts(applicant_frame):
    with pytest.raises(ColumnMappingError):
        apply_column_mapping(applicant_frame, {"name": "candidate_id"})
    with pytest.raises(ColumnMappingError):
        apply_column_mapping(applicant_frame, {"missing": "name"})


@pytest.mark.parametrize("filename,data", [("bad.xls", b"abc"), ("bad.csv", b""), ("bad.xlsx", b"broken zip"), ("bad.csv", b"\xff"), ("bad.csv", b'a,a\n1,2\n'), ("bad.csv", b'candidate_id,name,skills\nA,"unclosed,python')])
def test_corrupt_unsupported_files(filename, data):
    with pytest.raises(DataLoadError):
        load_applicants(data, filename)


def test_sample_files_have_72_synthetic_records():
    base = Path(__file__).resolve().parents[1] / "data"
    for filename in ["sample_applicants.csv", "sample_applicants.xlsx"]:
        frame = load_applicants(base / filename)
        result = validate_applicants(frame)
        assert result.summary["valid"] == 72
        assert frame.email.str.endswith("@example.test").all()


def test_duplicate_excel_headings_rejected():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['candidate_id', 'name', 'skills', 'skills'])
    sheet.append(['C001', 'Synthetic One', 'python', 'sql'])
    buffer = io.BytesIO()
    workbook.save(buffer)
    with pytest.raises(DataLoadError, match='repeated'):
        load_applicants(buffer.getvalue(), 'duplicate.xlsx')


def test_binary_stream_position_preserved(applicant_frame):
    source = io.BytesIO(applicant_frame.to_csv(index=False).encode())
    source.seek(5)
    loaded = load_applicants(source, 'input.csv')
    assert len(loaded) == 2
    assert source.tell() == 5
