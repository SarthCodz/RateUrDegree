# tests/test_runner.py
import pytest
import time
from unittest.mock import patch, MagicMock
from modules.audit_logic import (
    parse_transcript, compute_gpa, rank_from_gpa,
    build_prompt, extract_rank, run_gemini_audit, AuditParsingError
)
from google.genai.errors import ServerError, APIError

# ── FIXTURES ──────────────────────────────────────────────────────────────────

SIMPLE_TRANSCRIPT = """
MATH 140 - Calculus I - 4.0 - A
MATH 141 - Calculus II - 4.0 - A
CMPSC 121 - Intro Programming - 3.0 - A
CMPSC 122 - Intermediate Programming - 3.0 - A
PHYS 211 - Physics Mechanics - 4.0 - B+
ENGL 15 - Rhetoric - 3.0 - A
STAT 200 - Statistics - 3.0 - B
IST 110 - Info Systems - 3.0 - A-
ECON 102 - Economics - 3.0 - B+
CMPSC 132 - Data Structures - 3.0 - A
"""
# Hand calc: exclude nothing
# A=4.0, A=4.0, A=4.0, A=4.0, B+=3.3, A=4.0, B=3.0, A-=3.7, B+=3.3, A=4.0
# points: 16+16+12+12+13.2+12+9+11.1+9.9+12 = 123.2
# credits: 4+4+3+3+4+3+3+3+3+3 = 33
# GPA: 123.2/33 = 3.733... → round 2dp = 3.73

# ── PARSE_TRANSCRIPT ──────────────────────────────────────────────────────────

def test_1_parse_returns_10_courses():
    courses = parse_transcript(SIMPLE_TRANSCRIPT)
    assert len(courses) == 10

def test_2_parse_first_course_fields():
    courses = parse_transcript(SIMPLE_TRANSCRIPT)
    assert courses[0]["code"] == "MATH 140"
    assert courses[0]["credits"] == 4.0
    assert courses[0]["grade"] == "A"

def test_3_grade_forgiveness_keeps_latest():
    text = "MATH 140 - Calc - 3.0 - F\nMATH 140 - Calc - 3.0 - A"
    courses = parse_transcript(text)
    assert len(courses) == 1
    assert courses[0]["grade"] == "A"

def test_4_empty_transcript_raises():
    with pytest.raises(AuditParsingError):
        parse_transcript("")

def test_5_no_valid_courses_raises():
    with pytest.raises(AuditParsingError):
        parse_transcript("This is not a transcript at all.")

# ── COMPUTE_GPA ───────────────────────────────────────────────────────────────

def test_6_gpa_inline_transcript():
    courses = parse_transcript(SIMPLE_TRANSCRIPT)
    assert compute_gpa(courses) == 3.73

def test_7_transfer_excluded_from_gpa():
    text = "MATH 140 - Calc - 4.0 - A\nPHYS 211 - Physics - 3.0 - TR"
    courses = parse_transcript(text)
    assert compute_gpa(courses) == 4.00

def test_8_withdrawal_excluded_from_gpa():
    text = "MATH 140 - Calc - 4.0 - A\nCHEM 110 - Chem - 4.0 - W"
    courses = parse_transcript(text)
    assert compute_gpa(courses) == 4.00

def test_9_all_excluded_grades_returns_zero():
    text = "MATH 140 - Calc - 4.0 - TR\nCHEM 110 - Chem - 3.0 - W"
    courses = parse_transcript(text)
    assert compute_gpa(courses) == 0.00

def test_10_gpa_forgiveness_uses_retaken_grade():
    text = "MATH 140 - Calc - 3.0 - F\nMATH 140 - Calc - 3.0 - A"
    courses = parse_transcript(text)
    assert compute_gpa(courses) == 4.00

# ── RANK_FROM_GPA ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("gpa,expected", [
    (4.00, "Z"),
    (4.50, "Z"),
    (3.80, "S"),
    (3.99, "S"),
    (3.50, "A"),
    (3.79, "A"),
    (3.20, "B"),
    (3.49, "B"),
    (2.80, "C"),
    (3.19, "C"),
    (2.30, "D"),
    (2.79, "D"),
    (2.00, "E"),
    (2.29, "E"),
    (1.99, "F"),
    (0.00, "F"),
])
def test_11_rank_boundaries(gpa, expected):
    assert rank_from_gpa(gpa) == expected

# ── BUILD_PROMPT / EXTRACT_RANK ───────────────────────────────────────────────

def test_12_build_prompt_contains_inputs():
    prompt = build_prompt("Computer Science (B.S.)", "bulletin text", "transcript text")
    assert "Computer Science" in prompt
    assert "bulletin text" in prompt
    assert "transcript text" in prompt

def test_13_extract_rank_found():
    text = "...evaluation complete. **Student Rank: [S]**"
    assert extract_rank(text) == "S"

def test_14_extract_rank_missing_returns_unknown():
    assert extract_rank("No rank here.") == "UNKNOWN"

# ── RUN_GEMINI_AUDIT ──────────────────────────────────────────────────────────

def test_15_missing_api_key_raises_before_client():
    with patch("modules.audit_logic.genai.Client") as mock_cls:
        with pytest.raises(ValueError):
            run_gemini_audit("CS", "bulletin", "transcript", api_key=None)
        mock_cls.assert_not_called()

def test_16_success_on_first_attempt():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = "Audit result"
    with patch("modules.audit_logic.genai.Client", return_value=mock_client):
        result = run_gemini_audit("CS", "b", "t", api_key="key123")
    assert result == "Audit result"
    assert mock_client.models.generate_content.call_count == 1

def test_17_retries_twice_then_succeeds():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        ServerError("503", response=MagicMock(status_code=503), body={}),
        ServerError("503", response=MagicMock(status_code=503), body={}),
        MagicMock(text="Success after retries"),
    ]
    with patch("modules.audit_logic.genai.Client", return_value=mock_client), \
         patch("modules.audit_logic.time.sleep"):
        result = run_gemini_audit("CS", "b", "t", api_key="key123")
    assert result == "Success after retries"
    assert mock_client.models.generate_content.call_count == 3

def test_18_server_error_max_retries_raises():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = ServerError(
        "503", response=MagicMock(status_code=503), body={}
    )
    with patch("modules.audit_logic.genai.Client", return_value=mock_client), \
         patch("modules.audit_logic.time.sleep"):
        with pytest.raises(ServerError):
            run_gemini_audit("CS", "b", "t", api_key="key123")
    assert mock_client.models.generate_content.call_count == 3

def test_19_rate_limit_returns_error_string():
    mock_client = MagicMock()
    api_err = MagicMock(spec=APIError)
    api_err.code = 429
    mock_client.models.generate_content.side_effect = api_err
    with patch("modules.audit_logic.genai.Client", return_value=mock_client):
        result = run_gemini_audit("CS", "b", "t", api_key="key123")
    assert "Rate limit" in result or "429" in result

def test_20_demo_mode_skips_client():
    """app.py uses SAMPLE_PRECOMPUTED_REPORT when use_sample_transcript=True and no key.
    run_gemini_audit is never called in that path. This test confirms it raises
    ValueError (not a network call) when key is absent, matching app.py's guard."""
    with patch("modules.audit_logic.genai.Client") as mock_cls:
        with pytest.raises(ValueError):
            run_gemini_audit("CS", "b", "t", api_key="")
        mock_cls.assert_not_called()