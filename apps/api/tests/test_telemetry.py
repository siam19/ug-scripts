"""
Tests for Token Usage Accounting and Access Code Auth on Endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from firebase import set_mock_firestore, reset_clients
from auth import clear_auth_cache
from schemas import LineRephraseResponse


@pytest.fixture(autouse=True)
def clean_state():
    clear_auth_cache()
    yield
    clear_auth_cache()
    reset_clients()


@patch("main.ask_gemini", new_callable=AsyncMock)
def test_regenerate_with_valid_access_code_returns_usage_header(mock_gemini, client):
    mock_gemini.return_value = LineRephraseResponse(
        text="Never settle for lukewarm hydration again.",
        tone="punchy",
    )

    # Mock Firestore for valid access code
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "owner_name": "Demo Tester",
        "company": "Test Agency",
        "active": True,
        "total_tokens": 100,
    }
    mock_doc_ref = MagicMock()
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    mock_doc_ref.update = AsyncMock()

    mock_log_ref = MagicMock()
    mock_log_ref.set = AsyncMock()

    def mock_collection(name):
        coll = MagicMock()
        if name == "access_codes":
            coll.document.return_value = mock_doc_ref
        elif name == "generation_logs":
            coll.document.return_value = mock_log_ref
        return coll

    mock_db.collection.side_effect = mock_collection
    set_mock_firestore(mock_db)

    payload = {
        "name": "Smart Bottle",
        "market": "Global",
        "language": "en",
        "facts": ["Insulated stainless steel"],
        "segment": {
            "name": "Fitness Enthusiasts",
            "who": "Gym goers",
            "pain_point": "Warm water in gym",
            "platforms": ["TikTok"],
        },
        "script_context": [{"id": 1, "kind": "hook", "text": "Tired of warm water?"}],
        "line_id": 1,
        "current_text": "Tired of warm water?",
        "kind": "hook",
    }
    headers = {"X-Access-Code": "TEST-CODE-VALID"}
    res = client.post("/regenerate/line/rephrase", json=payload, headers=headers)
    assert res.status_code == 200
    assert "X-Token-Usage" in res.headers
    data = res.json()
    assert data["tone"] == "punchy"
