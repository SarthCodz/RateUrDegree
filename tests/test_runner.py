import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from google.genai.errors import ServerError

from modules.audit_logic import run_gemini_audit

@pytest.fixture
def fixture_dir():
    return Path(__file__).parent / "fixtures"

@patch("modules.audit_logic.genai.Client")
def test_run_gemini_audit_success(mock_genai_client, fixture_dir):
    """Test successful audit run with mocked Gemini Client returning expected rank and metrics."""
    mock_response = MagicMock()
    mock_response.text = "**Student Rank: [S]**\n\n### Quick Student Metrics\n- **Cumulative GPA**: 3.80"
    
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client_instance

    transcript_path = fixture_dir / "sample_cs_sophomore.txt"
    transcript_text = transcript_path.read_text()
    bulletin_text = "Computer Science B.S. Bulletin Requirements..."

    result = run_gemini_audit("Computer Science (B.S.)", bulletin_text, transcript_text, api_key="fake-key")
    
    assert "**Student Rank: [S]**" in result
    assert "Cumulative GPA" in result

@patch("modules.audit_logic.genai.Client")
def test_run_gemini_audit_rate_limit_retry(mock_genai_client):
    """Test retry behavior on server errors or rate limits."""
    mock_client_instance = MagicMock()
    # Provide required response_json argument to ServerError
    mock_client_instance.models.generate_content.side_effect = [
        ServerError(response_json={"error": {"message": "Internal Server Error"}}),
        MagicMock(text="**Student Rank: [B]**")
    ]
    mock_genai_client.return_value = mock_client_instance

    result = run_gemini_audit("Computer Science", "Bulletin", "Transcript", api_key="fake-key")
    assert "**Student Rank: [B]**" in result