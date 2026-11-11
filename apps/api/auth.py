"""
Authentication and Access Control Module.

Manages:
1. Access code verification against Firestore 'access_codes' collection with in-memory TTL caching.
2. FastAPI dependencies enforcing access gating with admin API_KEY bypass.
3. Access request dispatch and webhook notifications via httpx.
"""

import os
import time
from typing import Any
from fastapi import Header, HTTPException, Request, status
import httpx
from google.cloud import firestore

from firebase import get_firestore_client
from rate_limiter import SlidingWindowRateLimiter

# 60-second in-memory TTL cache for verified access codes: code -> (data, expires_at)
_access_cache: dict[str, tuple[dict[str, Any] | None, float]] = {}
CACHE_TTL_SECONDS = 60.0

# Rate limiter for access requests: max 5 requests per 10 minutes per IP
access_request_limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=600)

FALLBACK_ACCESS_CODES: dict[str, dict[str, Any]] = {
    "DEMO1": {
        "code": "DEMO1",
        "owner_name": "Demo User",
        "company": "Creator Beta",
        "active": True,
        "tokens_used": 0,
        "token_limit": 100000,
        "remaining_tokens": 100000,
    },
    "DHAKA": {
        "code": "DHAKA",
        "owner_name": "Dhaka Tester",
        "company": "Chaldal / Independent",
        "active": True,
        "tokens_used": 0,
        "token_limit": 100000,
        "remaining_tokens": 100000,
    },
    "BETA1": {
        "code": "BETA1",
        "owner_name": "Beta VIP",
        "company": "VIP Studio",
        "active": True,
        "tokens_used": 0,
        "token_limit": 100000,
        "remaining_tokens": 100000,
    },
    "UG001": {
        "code": "UG001",
        "owner_name": "UG Founder",
        "company": "UG-Scripts Core",
        "active": True,
        "tokens_used": 0,
        "token_limit": 100000,
        "remaining_tokens": 100000,
    },
    "BETA-DHAKA-01": {
        "code": "BETA-DHAKA-01",
        "owner_name": "Demo Tester",
        "company": "Chaldal / Independent",
        "active": True,
        "tokens_used": 0,
        "token_limit": 100000,
        "remaining_tokens": 100000,
    },
    "UG-CREATOR-88": {
        "code": "UG-CREATOR-88",
        "owner_name": "Creator Beta",
        "company": "Creator Studio",
        "active": True,
        "tokens_used": 0,
        "token_limit": 100000,
        "remaining_tokens": 100000,
    },
}


def clear_auth_cache() -> None:
    """Clears cached access codes (useful for tests and updates)."""
    _access_cache.clear()


async def verify_access_code_record(code: str) -> dict[str, Any] | None:
    """
    Checks if an access code exists and is active.
    Uses in-memory cache to minimize Firestore read operations.
    """
    clean_code = code.strip()
    if not clean_code:
        return None

    now = time.monotonic()
    if clean_code in _access_cache:
        cached_data, expires_at = _access_cache[clean_code]
        if now < expires_at:
            return cached_data

    # Query Firestore
    try:
        db = get_firestore_client()
        doc_ref = db.collection("access_codes").document(clean_code)
        doc = await doc_ref.get()

        if doc.exists:
            data = doc.to_dict() or {}
            if data.get("active", True):
                _access_cache[clean_code] = (data, now + CACHE_TTL_SECONDS)
                return data

        # Not found or inactive
        _access_cache[clean_code] = (None, now + CACHE_TTL_SECONDS)
        return None
    except Exception as e:
        # If Firestore is unavailable or unconfigured, log and use fallback demo codes
        print(f"Firestore access code lookup error: {e}")
        if clean_code in FALLBACK_ACCESS_CODES:
            print(f"Using fallback demo access code for '{clean_code}'")
            return FALLBACK_ACCESS_CODES[clean_code]
        return None


async def require_auth(
    x_access_code: str | None = Header(None, alias="X-Access-Code"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> dict[str, Any]:
    """
    FastAPI dependency that enforces authentication:
    1. If a valid X-API-Key is provided, grants admin bypass.
    2. Else, validates the provided X-Access-Code against Firestore.
    Raises HTTP 401 if unauthorized.
    """
    expected_api_key = os.environ.get("API_KEY")
    if expected_api_key and x_api_key == expected_api_key:
        return {
            "access_code": "ADMIN",
            "owner_name": "Administrator",
            "company": "Internal",
            "is_admin": True,
        }

    if x_access_code:
        record = await verify_access_code_record(x_access_code)
        if record:
            return {
                "access_code": x_access_code.strip(),
                "owner_name": record.get("owner_name", ""),
                "company": record.get("company", ""),
                "total_tokens": record.get("total_tokens", 0),
                "is_admin": False,
            }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Bad or missing API key or access code. Provide a valid 'X-Access-Code' or 'X-API-Key' header.",
    )


async def send_lead_notification(name: str, phone: str, company: str) -> None:
    """
    Sends an instant notification alert to NOTIFY_WEBHOOK_URL (Telegram / Discord / Slack).
    Runs asynchronously in the background.
    """
    webhook_url = os.environ.get("NOTIFY_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return

    text = (
        f"🎯 *New Demo Access Request - UG-Scripts*\n"
        f"👤 *Name*: {name}\n"
        f"📞 *Phone*: {phone}\n"
        f"🏢 *Company*: {company}"
    )

    payload: dict[str, Any]
    # Check if Telegram Bot API URL format
    if "api.telegram.org" in webhook_url:
        payload = {"text": text, "parse_mode": "Markdown"}
    else:
        # Custom notification worker / Discord / Slack
        payload = {
            "name": name,
            "phone": phone,
            "company": company,
            "text": text,
            "content": text,
        }

    headers: dict[str, str] = {}
    notify_secret = os.environ.get("NOTIFY_SECRET", "").strip()
    if notify_secret:
        headers["Authorization"] = f"Bearer {notify_secret}"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await client.post(webhook_url, json=payload, headers=headers)
    except Exception as e:
        print(f"Failed to deliver lead notification webhook: {e}")
