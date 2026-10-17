import pytest
from pathlib import Path
from modules.audit_logic import parse_transcript, compute_gpa, AuditParsingError

@pytest.fixture
def fixture_dir():
    return Path(__file__).parent / "fixtures"

def test_1_parse_transcript_fixture(fixture_dir):
    transcript_path = fixture_dir / "sample_cs_sophomore.txt"
    text = transcript_path.read_text()
    courses = parse_transcript(text)
    assert len(courses) == 10
    assert courses[0]["code"] == "MATH 140"
    assert courses[0]["credits"] == 4.0
    assert courses[0]["grade"] == "A"

def test_2_compute_gpa_fixture(fixture_dir):
    transcript_path = fixture_dir / "sample_cs_sophomore.txt"
    courses = parse_transcript(transcript_path.read_text())
    gpa = compute_gpa(courses)
    assert gpa == 3.77

def test_3_grade_forgiveness_repeat():
    text = "MATH 140 - Calc - 3.0 - F\nMATH 140 - Calc - 3.0 - A"
    courses = parse_transcript(text)
    assert len(courses) == 1
    assert courses[0]["grade"] == "A"
    assert compute_gpa(courses) == 4.00

def test_4_transfer_credits_excluded_from_gpa():
    text = "MATH 140 - Calc - 4.0 - A\nPHYS 211 - Physics - 3.0 - TR"
    courses = parse_transcript(text)
    gpa = compute_gpa(courses)
    total_credits = sum(c["credits"] for c in courses)
    assert gpa == 4.00
    assert total_credits == 7.0

def test_5_missing_gpa_line_computed():
    text = "CHEM 110 - Chem - 4.0 - B"
    courses = parse_transcript(text)
    assert compute_gpa(courses) == 3.00