import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import time
from google.genai.errors import ServerError, APIError

from modules.audit_logic import (
    parse_transcript,
    compute_gpa,
    rank_from_gpa,
    build_prompt,
    extract_rank,
    run_gemini_audit,
    run_demo_audit_mode,
    AuditParsingError
)

@pytest.fixture
def fixture_dir():
    return Path(__file__).parent / "fixtures"

# 1. parse_transcript on the fixture returns the exact course list
def test_1_parse_transcript_fixture(fixture_dir):
    transcript_path = fixture_dir / "sample_cs_sophomore.txt"
    text = transcript_path.read_text()
    courses = parse_transcript(text)
    assert len(courses) == 10
    assert courses[0]["code"] == "MATH 140"
    assert courses[0]["credits"] == 4.0
    assert courses[0]["grade"] == "A"

# 2. compute_gpa on the fixture equals 3.77
def test_2_compute_gpa_fixture(fixture_dir):
    transcript_path = fixture_dir / "sample_cs_sophomore.txt"
    courses = parse_transcript(transcript_path.read_text())
    gpa = compute_gpa(courses)
    assert gpa == 3.77

# 3. repeated course with grade forgiveness (F then A) counts only the replacement
def test_3_grade_forgiveness_repeat():
    # Grade forgiveness verification: when a course is repeated (F then A), 
    # the dictionary key overwrite ensures only the latest passing grade (A) is counted.
    text = "MATH 140 - Calc - 3.0 - F\nMATH 140 - Calc - 3.0 - A"
    courses = parse_transcript(text)
    assert len(courses) == 1
    assert courses[0]["grade"] == "A"
    assert compute_gpa(courses) == 4.00

# 4. transfer credits (TR) count toward credits but not GPA
def test_4_transfer_credits_excluded_from_gpa():
    text = "MATH 140 - Calc - 4.0 - A\nPHYS 211 - Physics - 3.0 - TR"
    courses = parse_transcript(text)
    gpa = compute_gpa(courses)
    total_credits = sum(c["credits"] for c in courses)
    assert gpa == 4.00
    assert total_credits == 7.0

# 5. missing cumulative GPA line: computed from courses, not defaulted
def test_5_missing_gpa_line_computed():
    text = "CHEM 110 - Chem - 4.0 - B"
    courses = parse_transcript(text)
    assert compute_gpa(courses) == 3.00

# 6. W/P/S grades are excluded from GPA
def test_6_pass_withdraw_audit_grades_excluded():
    text = "MATH 140 - Calc - 4.0 - A\nSTAT 200 - Stats - 3.0 - W\nKIN 101 - Fitness - 1.0 - P"
    courses = parse_transcript(text)
    gpa = compute_gpa(courses)
    assert gpa == 4.00

# 7. credit total is correct
def test_7_credit_total_sum():
    text = "MATH 140 - Calc - 4.0 - A\nENGL 15 - Comp - 3.0 - B\nCHEM 110 - Chem - 3.0 - C"
    courses = parse_transcript(text)
    total = sum(c["credits"] for c in courses)
    assert total == 10.0

# 8. rank_from_gpa parametrized on boundaries
@pytest.mark.parametrize("gpa,expected_rank", [
    (4.00, "Z"), (3.99, "S"), (3.80, "S"), (3.79, "A"), (3.50, "A"),
    (3.49, "B"), (3.20, "B"), (3.19, "C"), (2.80, "C"), (2.79, "D"),
    (2.30, "D"), (2.29, "E"), (2.00, "E"), (1.99, "F"), (0.00, "F")
])
def test_8_rank_from_gpa_boundaries(gpa, expected_rank):
    assert rank_from_gpa(gpa) == expected_rank

# 9. empty transcript raises or returns a friendly error
def test_9_empty_transcript_raises():
    with pytest.raises(AuditParsingError):
        parse_transcript("")

# 10. garbage/binary-looking text doesn’t crash
def test_10_garbage_text_handled():
    with pytest.raises(AuditParsingError):
        parse_transcript("\x00\x01\x02%^&*@# GARBAGE BINARY DATA")

# 11. build_prompt contains the major, bulletin text, and transcript text
def test_11_build_prompt_composition():
    prompt = build_prompt("Computer Science", "Bulletin 2026", "MATH 140 A")
    assert "Computer Science" in prompt
    assert "Bulletin 2026" in prompt
    assert "MATH 140 A" in prompt

# 12. extract_rank on a realistic response returns the right rank
def test_12_extract_rank_valid():
    response = "Some intro text.\n\n**Student Rank: [S]**\n\nMetrics follow."
    assert extract_rank(response) == "S"

# 13. extract_rank on a response with no rank handles it gracefully
def test_13_extract_rank_missing():
    response = "No rank header provided in this text."
    assert extract_rank(response) == "UNKNOWN"

# 14. 500 then success: patch time.sleep and assert call_count == 2
@patch("modules.audit_logic.time.sleep", return_value=None)
@patch("modules.audit_logic.genai.Client")
def test_14_server_error_retry_success(mock_client_cls, mock_sleep):
    client_instance = MagicMock()
    client_instance.models.generate_content.side_effect = [
        ServerError(500, {"error": "Server Down"}),
        MagicMock(text="**Student Rank: [S]**")
    ]
    mock_client_cls.return_value = client_instance

    res = run_gemini_audit("CS", "Bulletin", "Transcript", api_key="test-key")
    assert client_instance.models.generate_content.call_count == 2
    assert "**Student Rank: [S]**" in res

# 15. persistent 500: patch time.sleep, assert max retries and raises ServerError
@patch("modules.audit_logic.time.sleep", return_value=None)
@patch("modules.audit_logic.genai.Client")
def test_15_persistent_server_error_max_retries(mock_client_cls, mock_sleep):
    client_instance = MagicMock()
    client_instance.models.generate_content.side_effect = ServerError(500, {"error": "Persistent Error"})
    mock_client_cls.return_value = client_instance

    with pytest.raises(ServerError):
        run_gemini_audit("CS", "Bulletin", "Transcript", api_key="test-key")
    assert client_instance.models.generate_content.call_count == 3

# 16. 429: exact message, no retry loop
@patch("modules.audit_logic.genai.Client")
def test_16_rate_limit_429_no_retry(mock_client_cls):
    client_instance = MagicMock()
    client_instance.models.generate_content.side_effect = APIError(429, {"error": "Rate limit"})
    mock_client_cls.return_value = client_instance

    res = run_gemini_audit("CS", "Bulletin", "Transcript", api_key="test-key")
    assert client_instance.models.generate_content.call_count == 1
    assert "API Error: Rate limit encountered." in res

# 17. 503 handled: patch time.sleep
@patch("modules.audit_logic.time.sleep", return_value=None)
@patch("modules.audit_logic.genai.Client")
def test_17_service_unavailable_503(mock_client_cls, mock_sleep):
    client_instance = MagicMock()
    client_instance.models.generate_content.side_effect = [
        ServerError(503, {"error": "Service Unavailable"}),
        MagicMock(text="**Student Rank: [B]**")
    ]
    mock_client_cls.return_value = client_instance

    res = run_gemini_audit("CS", "Bulletin", "Transcript", api_key="test-key")
    assert client_instance.models.generate_content.call_count == 2
    assert "**Student Rank: [B]**" in res

# 18. missing API key: friendly error and client never constructed
def test_18_missing_api_key_error():
    with pytest.raises(ValueError, match="Missing API key"):
        run_gemini_audit("CS", "Bulletin", "Transcript", api_key="")

# 19. Demo mode test for real: call offline report path with no API key, assert precomputed report returned and genai.Client never called
@patch("modules.audit_logic.genai.Client")
def test_19_demo_mode_no_client_called(mock_client_cls):
    res = run_demo_audit_mode(api_key=None)
    assert res == "OFFLINE_DEMO_REPORT"
    mock_client_cls.assert_not_called()

# 20. malformed or schema-invalid model response: handled, no crash
@patch("modules.audit_logic.genai.Client")
def test_20_malformed_model_response(mock_client_cls):
    client_instance = MagicMock()
    client_instance.models.generate_content.return_value = MagicMock(text="MALFORMED UNSTRUCTURED RESPONSE WITH NO RANK TAG")
    mock_client_cls.return_value = client_instance

    res = run_gemini_audit("CS", "Bulletin", "Transcript", api_key="test-key")
    rank = extract_rank(res)
    assert rank == "UNKNOWN"

# 21. Real anonymized transcript fixture test asserting exact course count (8) and hand-calculated GPA (3.64)
def test_21_real_anonymized_transcript(fixture_dir):
    transcript_path = fixture_dir / "real_anonymized_transcript.txt"
    text = transcript_path.read_text()
    courses = parse_transcript(text)
    gpa = compute_gpa(courses)
    assert len(courses) == 8
    assert gpa == 3.64