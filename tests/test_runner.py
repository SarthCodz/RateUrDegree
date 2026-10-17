import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

# Import actual functions from your core logic module
from audit_logic import (
    calculate_gpa,
    determine_rank,
    check_missing_requirements,
    generate_schedule,
    AuditParsingError
)

@pytest.fixture
def fixture_dir():
    return Path(__file__).parent / "fixtures"

def test_gpa_calculation_manual_arithmetic(fixture_dir):
    """
    Manually computed GPA test:
    MATH 140: 4.0 credits * 4.0 (A) = 16.0 points
    CMPSC 121: 3.0 credits * 4.0 (A) = 12.0 points
    ENGL 15: 3.0 credits * 3.0 (B) = 9.0 points
    Total Quality Points = 37.0
    Total Credits = 10.0
    Expected GPA = 37.0 / 10.0 = 3.70
    """
    transcript_path = fixture_dir / "sample_cs_sophomore.txt"
    text = transcript_path.read_text()
    
    gpa = calculate_gpa(text)
    assert gpa == pytest.approx(3.70, rel=1e-2)

def test_determine_rank_thresholds():
    """Verify rank categorization logic based on GPA thresholds."""
    assert determine_rank(3.85) == "S"
    assert determine_rank(3.40) == "B"
    assert determine_rank(2.10) == "E"

def test_missing_gpa_raises_or_computes():
    """Ensure a missing GPA field is dynamically computed or flagged rather than using a hardcoded fallback."""
    transcript_without_gpa = "MATH 140 | 4.0 credits | Grade: A"
    # Should compute from courses or raise/flag, instead of defaulting to a silent 3.80
    gpa = calculate_gpa(transcript_without_gpa)
    assert gpa == 4.00  # Computed directly from coursework

def test_garbage_input_raises_friendly_error():
    """Test that corrupted or invalid input raises a friendly AuditParsingError."""
    garbage_text = "$%^&* INVALID CORRUPTED BINARY STREAM DATA $$$"
    with pytest.raises(AuditParsingError, match="Unable to parse transcript"):
        calculate_gpa(garbage_text)

@patch("audit_logic.genai.GenerativeModel")
def test_gemini_schema_validation_valid(mock_model_class):
    """Test Gemini integration with valid canned JSON schema response."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "status": "success",
        "missing_courses": ["CMPSC 122"],
        "recommended_schedule": ["MATH 141", "CMPSC 122"]
    })
    mock_model_class.return_value.generate_content.return_value = mock_response

    result = generate_schedule("Sample transcript text")
    assert "CMPSC 122" in result["missing_courses"]
    assert len(result["recommended_schedule"]) == 2

@patch("audit_logic.genai.GenerativeModel")
def test_gemini_schema_validation_invalid(mock_model_class):
    """Test Gemini schema validation behavior when API returns malformed or invalid JSON structure."""
    mock_response = MagicMock()
    mock_response.text = "NOT VALID JSON SCHEMA OUTPUT"
    mock_model_class.return_value.generate_content.return_value = mock_response

    with pytest.raises((json.JSONDecodeError, ValueError)):
        generate_schedule("Sample transcript text")