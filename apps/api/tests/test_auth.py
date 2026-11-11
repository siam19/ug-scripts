"""
Tests for Access Code Verification, Lead Requests, and Auth Dependency.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from firebase import set_mock_firestore, reset_clients
from auth import clear_auth_cache, access_request_limiter


@pytest.fixture(autouse=True)
def clean_auth_state():
    clear_auth_cache()
    access_request_limiter.reset()
    yield
    clear_auth_cache()
    reset_clients()


def test_verify_access_code_invalid(client):
    # Mock Firestore returning non-existent document
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_doc_ref = MagicMock()
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    mock_coll = MagicMock()
    mock_coll.document.return_value = mock_doc_ref
    mock_db.collection.return_value = mock_coll
    set_mock_firestore(mock_db)

    res = client.post("/auth/verify", json={"code": "INVALID-CODE-99"})
    assert res.status_code == 401
    assert "Invalid or expired access code" in res.json()["detail"]


def test_verify_access_code_valid(client):
    # Mock Firestore returning active access code document
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "owner_name": "Demo Tester",
        "company": "Test Agency",
        "active": True,
        "total_tokens": 5200,
        "total_input_tokens": 4000,
        "total_output_tokens": 1200,
    }
    mock_doc_ref = MagicMock()
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    mock_coll = MagicMock()
    mock_coll.document.return_value = mock_doc_ref
    mock_db.collection.return_value = mock_coll
    set_mock_firestore(mock_db)

    res = client.post("/auth/verify", json={"code": "VALID-BETA-01"})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["owner_name"] == "Demo Tester"
    assert data["company"] == "Test Agency"
    assert data["total_tokens"] == 5200


def test_request_access_success(client):
    mock_db = MagicMock()
    mock_coll = MagicMock()
    mock_coll.add = AsyncMock(return_value=(MagicMock(), MagicMock()))
    mock_db.collection.return_value = mock_coll
    set_mock_firestore(mock_db)

    payload = {
        "name": "Rahim Khan",
        "phone": "+8801712345678",
        "company": "Bengal Digital",
    }
    res = client.post("/auth/request-access", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "received" in data["message"].lower()


def test_request_access_rate_limit(client):
    mock_db = MagicMock()
    mock_coll = MagicMock()
    mock_coll.add = AsyncMock(return_value=(MagicMock(), MagicMock()))
    mock_db.collection.return_value = mock_coll
    set_mock_firestore(mock_db)

    payload = {
        "name": "Spam Tester",
        "phone": "+8801700000000",
        "company": "Spam Corp",
    }
    # Limit is 5 requests per 10 minutes
    for _ in range(5):
        res = client.post("/auth/request-access", json=payload)
        assert res.status_code == 200

    # 6th request must trigger 429
    res = client.post("/auth/request-access", json=payload)
    assert res.status_code == 429
    assert "Too many access requests" in res.json()["detail"]


def test_get_demo_products_catalog(client):
    res = client.get("/demo-products")
    assert res.status_code == 200
    data = res.json()
    assert "products" in data
    # Verified fallback returns 3 products
    assert len(data["products"]) >= 3
    assert data["products"][0]["id"] == "radhuni-biryani-masala"
