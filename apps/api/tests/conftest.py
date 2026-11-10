"""
Pytest fixtures and configuration for API test suite.
"""

import base64
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure apps/api directory is on sys.path
api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

# Ensure test API key and project are set in environment
os.environ.setdefault("API_KEY", "test-secret-key-12345")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

from main import app  # noqa: E402
from rate_limiter import regeneration_limiter  # noqa: E402


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Resets the in-memory rate limiter before each test."""
    regeneration_limiter.reset()
    yield
    regeneration_limiter.reset()


@pytest.fixture
def client():
    """Provides a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    return os.environ.get("API_KEY", "test-secret-key-12345")


@pytest.fixture
def valid_headers(valid_api_key):
    return {"X-API-Key": valid_api_key}


@pytest.fixture
def sample_png_bytes():
    """Returns valid 1x1 PNG bytes."""
    b64_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    return base64.b64decode(b64_png)


@pytest.fixture
def valid_form_data():
    return {
        "name": "Smart Hydration Tumbler",
        "description": "Vacuum-insulated smart stainless steel water bottle with LED temperature display and hourly hydration reminders.",
        "category": "Fitness & Lifestyle",
        "market": "Bangladesh",
        "language": "en",
    }


@pytest.fixture
def sample_facts():
    return [
        "24-hour hydration formula",
        "Contains 2% pure hyaluronic acid",
        "Fragrance-free and hypoallergenic",
    ]
