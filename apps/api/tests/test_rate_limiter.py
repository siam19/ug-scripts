"""
Tests for Rate Limiter on Regeneration Endpoints.
Verifies:
- Permitted requests up to max_requests
- 429 Too Many Requests when limit is exceeded
- Retry-After header present
- Detail message: 'Slow down. Too many requests in 1 minute. Try again later.'
"""

from unittest.mock import AsyncMock, patch
import pytest

from rate_limiter import SlidingWindowRateLimiter, regeneration_limiter
from schemas import Segment


def test_sliding_window_rate_limiter_unit():
    """Unit test for the SlidingWindowRateLimiter data structure."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    key = "client-1"

    allowed, _ = limiter.is_allowed(key)
    assert allowed is True

    allowed, _ = limiter.is_allowed(key)
    assert allowed is True

    allowed, _ = limiter.is_allowed(key)
    assert allowed is True

    # 4th request exceeds limit
    allowed, retry_after = limiter.is_allowed(key)
    assert allowed is False
    assert retry_after > 0

    # Other client is unaffected
    allowed, _ = limiter.is_allowed("client-2")
    assert allowed is True

    # Reset clears history
    limiter.reset()
    allowed, _ = limiter.is_allowed(key)
    assert allowed is True


def test_regeneration_rate_limit_endpoint_triggers_429(
    client, valid_headers, sample_facts
):
    """
    Verifies that calling /regenerate/segment beyond max_requests
    triggers HTTP 429 with Retry-After header and exact message.
    """
    mock_segment = Segment(
        name="Tech Geeks",
        who="Early adopters",
        pain_point="Wants speed",
        platforms=["TikTok"],
    )

    payload = {
        "name": "Smart Bottle",
        "category": "Fitness",
        "market": "Bangladesh",
        "language": "en",
        "facts": sample_facts,
        "current_segment": mock_segment.model_dump(),
        "existing_segment_names": [],
    }

    # Temporarily set max_requests to 2 for quick testing
    original_max = regeneration_limiter.max_requests
    regeneration_limiter.max_requests = 2

    try:
        with patch("main.ask_gemini", new_callable=AsyncMock) as mock_gemini:
            mock_gemini.return_value = mock_segment

            # Request 1: OK
            res1 = client.post("/regenerate/segment", json=payload, headers=valid_headers)
            assert res1.status_code == 200

            # Request 2: OK
            res2 = client.post("/regenerate/segment", json=payload, headers=valid_headers)
            assert res2.status_code == 200

            # Request 3: 429 Too Many Requests
            res3 = client.post("/regenerate/segment", json=payload, headers=valid_headers)
            assert res3.status_code == 429
            assert "Slow down. Too many requests in 1 minute. Try again later." in res3.json()["detail"]
            assert "retry-after" in res3.headers
    finally:
        regeneration_limiter.max_requests = original_max


