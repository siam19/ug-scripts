"""
Tests for Sprint 7 Backend Changes:
- Pre-generated log_id across /generate, /generate-stream, and /regenerate/* (X-Log-Id & SSE done event)
- CORS expose_headers includes X-Log-Id
- Public GET /auth/config (never exposes VITE_GOOGLE_CLIENT_SECRET)
- POST /feedback (auth, rate limiting, tag/rating/comment validation, idempotent Firestore upsert, offline fallback)
- POST /feedback/signal (auth, atomic firestore.Increment with merge=True, offline fallback)
- apps/api/scripts/export_feedback.py JSONL export
"""

import io
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.cloud import firestore

from auth import clear_auth_cache
from firebase import reset_clients, set_mock_firestore
from rate_limiter import feedback_limiter
from schemas import (
    FEEDBACK_TAGS,
    Line,
    LineRegenerateResponse,
    LineRephraseResponse,
    Reason,
    ReasonLinesRewriteResponse,
    RewrittenLine,
    Script,
    ScriptDraft,
    Segment,
    Segments,
)
from scripts.export_feedback import export_feedback_to_jsonl


@pytest.fixture(autouse=True)
def clean_feedback_state():
    clear_auth_cache()
    feedback_limiter.reset()
    yield
    clear_auth_cache()
    feedback_limiter.reset()
    reset_clients()


def _sample_script(segment_name: str = "Desk Workers") -> Script:
    return Script(
        segment=segment_name,
        lines=[
            Line(id=1, kind="hook", text="Stop scrolling if your skin feels dry by 2 PM!"),
            Line(id=2, kind="concept", text="Office AC steals moisture from your skin barrier all day."),
            Line(id=3, kind="concept", text="Two drops of our 2% hyaluronic serum lock in 24-hour hydration."),
            Line(id=4, kind="concept", text="It absorbs cleanly with zero sticky residue under sunscreen."),
            Line(id=5, kind="cta", text="Tap the link below to grab yours today."),
        ],
        reasons=[
            Reason(
                title="Pattern Interrupt Hook",
                why="Calls out the exact afternoon dryness pain point.",
                line_ids=[1],
            ),
            Reason(
                title="Concrete Fact Proof",
                why="Grounds hydration benefit in 2% hyaluronic acid.",
                line_ids=[2, 3, 4],
            ),
            Reason(
                title="Direct CTA",
                why="Clear next step at the end.",
                line_ids=[5],
            ),
        ],
    )


def _sample_segments() -> Segments:
    return Segments(
        product_facts=[
            "24-hour hydration formula",
            "Contains 2% pure hyaluronic acid",
            "Fragrance-free and hypoallergenic",
            "Glass dropper bottle packaging",
            "Made with ethical, cruelty-free ingredients",
        ],
        segments=[
            Segment(
                name="Desk Workers",
                who="25-35 year olds in AC offices",
                pain_point="Skin feels tight by 2 PM",
                platforms=["TikTok", "Reels"],
            ),
            Segment(
                name="Busy Mothers",
                who="Working moms short on time",
                pain_point="No time for 10-step routines",
                platforms=["Instagram Reels", "Facebook"],
            ),
            Segment(
                name="Outdoor Commuters",
                who="Daily commuters in heat and dust",
                pain_point="Pollution dulls skin barrier",
                platforms=["TikTok", "YouTube Shorts"],
            ),
        ],
    )


def _mock_firestore_for_feedback(existing_docs: dict[str, dict] | None = None):
    """Builds an in-memory async mock Firestore supporting set(..., merge=True) and get()."""
    store: dict[str, dict] = dict(existing_docs or {})
    writes: list[tuple[str, dict, bool]] = []

    def make_doc_ref(doc_id: str):
        ref = MagicMock()

        async def _set(data: dict, merge: bool = False):
            writes.append((doc_id, data, merge))
            if merge and doc_id in store:
                merged = dict(store[doc_id])
                for k, v in data.items():
                    if k == "signals" and isinstance(v, dict):
                        existing_sig = dict(merged.get("signals", {}))
                        for sig_k, sig_v in v.items():
                            inc = getattr(sig_v, "value", None)
                            if inc is not None:
                                existing_sig[sig_k] = existing_sig.get(sig_k, 0) + inc
                            else:
                                existing_sig[sig_k] = sig_v
                        merged["signals"] = existing_sig
                    else:
                        merged[k] = v
                store[doc_id] = merged
            else:
                new_doc = {}
                for k, v in data.items():
                    if k == "signals" and isinstance(v, dict):
                        new_sig = {}
                        for sig_k, sig_v in v.items():
                            inc = getattr(sig_v, "value", None)
                            new_sig[sig_k] = inc if inc is not None else sig_v
                        new_doc["signals"] = new_sig
                    else:
                        new_doc[k] = v
                store[doc_id] = new_doc

        async def _get():
            snap = MagicMock()
            snap.id = doc_id
            snap.exists = doc_id in store
            snap.to_dict.return_value = store.get(doc_id)
            return snap

        ref.set = AsyncMock(side_effect=_set)
        ref.get = AsyncMock(side_effect=_get)
        return ref

    def make_collection(name: str):
        coll = MagicMock()
        if name == "script_feedback":
            coll.document.side_effect = make_doc_ref

            async def _get_all():
                snaps = []
                for doc_id, data in store.items():
                    s = MagicMock()
                    s.id = doc_id
                    s.exists = True
                    s.to_dict.return_value = data
                    snaps.append(s)
                return snaps

            coll.get = AsyncMock(side_effect=_get_all)
        elif name == "access_codes":
            def _code_doc(code: str):
                ref = MagicMock()
                snap = MagicMock()
                snap.exists = code == "TEST-ACCESS-CODE"
                snap.to_dict.return_value = {
                    "owner_name": "Feedback Tester",
                    "company": "Test Studio",
                    "active": True,
                    "total_tokens": 0,
                }
                ref.get = AsyncMock(return_value=snap)
                ref.update = AsyncMock()
                return ref

            coll.document.side_effect = _code_doc
        else:
            doc_ref = MagicMock()
            doc_ref.set = AsyncMock()
            coll.document.return_value = doc_ref
        return coll

    db = MagicMock()
    db.collection.side_effect = make_collection
    return db, store, writes


# ---------------------------------------------------------------------------
# 1. GET /auth/config
# ---------------------------------------------------------------------------


def test_auth_config_returns_client_id_and_never_secret(client, monkeypatch):
    monkeypatch.setenv("VITE_GOOGLE_CLIENT_ID", "123456-public.apps.googleusercontent.com")
    monkeypatch.setenv("VITE_GOOGLE_CLIENT_SECRET", "super-secret-must-never-leak")

    res = client.get("/auth/config")
    assert res.status_code == 200
    body = res.json()
    assert body == {"google_client_id": "123456-public.apps.googleusercontent.com"}
    assert "super-secret-must-never-leak" not in res.text
    assert "secret" not in res.text.lower()


def test_auth_config_fallback_to_google_client_id_and_empty_default(client, monkeypatch):
    monkeypatch.delenv("VITE_GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "fallback-client-id.apps.googleusercontent.com")
    res = client.get("/auth/config")
    assert res.status_code == 200
    assert res.json() == {"google_client_id": "fallback-client-id.apps.googleusercontent.com"}

    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    res_empty = client.get("/auth/config")
    assert res_empty.status_code == 200
    assert res_empty.json() == {"google_client_id": ""}


# ---------------------------------------------------------------------------
# 2. Pre-generated log_id & X-Log-Id / SSE done log_id + CORS
# ---------------------------------------------------------------------------


def test_cors_exposes_x_log_id_header(client):
    res = client.get(
        "/auth/config",
        headers={"Origin": "http://localhost:5173"},
    )
    assert res.status_code == 200
    exposed = res.headers.get("access-control-expose-headers", "")
    assert "X-Log-Id" in exposed
    assert "X-Token-Usage" in exposed


def test_generate_sets_x_log_id_and_passes_same_id_to_audit(
    client, valid_form_data, sample_png_bytes, valid_headers
):
    segs = _sample_segments()

    async def fake_ask(prompt, schema, parts=(), max_retries=1, **kwargs):
        if schema == Segments:
            return segs
        return _sample_script("Desk Workers")

    with (
        patch("main.ask_gemini", side_effect=fake_ask),
        patch("main.log_generation_task", new_callable=AsyncMock) as mock_log,
    ):
        files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
        res = client.post("/generate", data=valid_form_data, files=files, headers=valid_headers)

    assert res.status_code == 200
    log_id = res.headers.get("X-Log-Id")
    assert log_id
    uuid.UUID(log_id)  # valid UUID
    mock_log.assert_awaited_once()
    assert mock_log.call_args.kwargs["log_id"] == log_id


def test_generate_stream_emits_log_id_in_done_event(
    client, valid_form_data, sample_png_bytes, valid_headers
):
    segs = _sample_segments()

    async def fake_ask(prompt, schema, parts=(), max_retries=1, **kwargs):
        if schema == Segments:
            return segs
        return _sample_script("Desk Workers")

    with (
        patch("main.ask_gemini", side_effect=fake_ask),
        patch("main.log_generation_task", new_callable=AsyncMock) as mock_log,
    ):
        files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
        res = client.post("/generate-stream", data=valid_form_data, files=files, headers=valid_headers)

    assert res.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in res.text.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [e for e in events if e.get("event") == "done"]
    assert len(done_events) == 1
    log_id = done_events[0].get("log_id")
    assert log_id
    uuid.UUID(log_id)
    mock_log.assert_awaited_once()
    assert mock_log.call_args.kwargs["log_id"] == log_id


def test_regenerate_json_endpoints_return_x_log_id(client, valid_headers, sample_facts):
    seg = _sample_segments().segments[0]

    with (
        patch("main.ask_gemini", new_callable=AsyncMock) as mock_gemini,
        patch("main.log_generation_task", new_callable=AsyncMock) as mock_log,
    ):
        # 1. /regenerate/segment
        mock_gemini.return_value = seg
        res1 = client.post(
            "/regenerate/segment",
            json={
                "name": "Hydra Serum",
                "category": "Skincare",
                "market": "Bangladesh",
                "language": "en",
                "facts": sample_facts,
                "current_segment": seg.model_dump(),
            },
            headers=valid_headers,
        )
        assert res1.status_code == 200
        assert res1.headers.get("X-Log-Id") == mock_log.call_args.kwargs["log_id"]

        # 2. /regenerate/script
        mock_gemini.return_value = _sample_script(seg.name)
        res2 = client.post(
            "/regenerate/script",
            json={
                "name": "Hydra Serum",
                "category": "Skincare",
                "market": "Bangladesh",
                "language": "en",
                "facts": sample_facts,
                "segment": seg.model_dump(),
            },
            headers=valid_headers,
        )
        assert res2.status_code == 200
        assert res2.headers.get("X-Log-Id") == mock_log.call_args.kwargs["log_id"]

        # 3. /regenerate/reason-lines
        mock_gemini.return_value = ReasonLinesRewriteResponse(
            lines=[RewrittenLine(kind="hook", text="Wait—is your skin feeling tight by 2 PM?")]
        )
        res3 = client.post(
            "/regenerate/reason-lines",
            json={
                "name": "Hydra Serum",
                "market": "Bangladesh",
                "language": "en",
                "facts": sample_facts,
                "segment": seg.model_dump(),
                "full_script": [
                    {"id": 1, "kind": "hook", "text": "Old hook"},
                    {"id": 2, "kind": "concept", "text": "Concept line"},
                    {"id": 3, "kind": "cta", "text": "Buy now"},
                ],
                "target_line_ids": [1],
                "reason": {"title": "Hook", "why": "Attention"},
            },
            headers=valid_headers,
        )
        assert res3.status_code == 200
        assert res3.headers.get("X-Log-Id") == mock_log.call_args.kwargs["log_id"]

        # 4. /regenerate/line/rephrase
        mock_gemini.return_value = LineRephraseResponse(text="Dry skin by 2 PM?", tone="punchy")
        res4 = client.post(
            "/regenerate/line/rephrase",
            json={
                "name": "Hydra Serum",
                "market": "Bangladesh",
                "language": "en",
                "facts": sample_facts,
                "segment": seg.model_dump(),
                "script_context": [{"id": 1, "kind": "hook", "text": "Dry skin?"}],
                "line_id": 1,
                "current_text": "Dry skin?",
                "kind": "hook",
            },
            headers=valid_headers,
        )
        assert res4.status_code == 200
        assert res4.headers.get("X-Log-Id") == mock_log.call_args.kwargs["log_id"]

        # 5. /regenerate/line/regenerate
        mock_gemini.return_value = LineRegenerateResponse(text="Why does AC wreck your glow?", kind="hook")
        res5 = client.post(
            "/regenerate/line/regenerate",
            json={
                "name": "Hydra Serum",
                "market": "Bangladesh",
                "language": "en",
                "facts": sample_facts,
                "segment": seg.model_dump(),
                "script_context": [{"id": 1, "kind": "hook", "text": "Dry skin?"}],
                "line_id": 1,
                "current_text": "Dry skin?",
                "kind": "hook",
            },
            headers=valid_headers,
        )
        assert res5.status_code == 200
        assert res5.headers.get("X-Log-Id") == mock_log.call_args.kwargs["log_id"]


def test_regenerate_section_emits_log_id_in_done_event(client, valid_headers, sample_facts):
    segs = _sample_segments().segments

    async def fake_ask(prompt, schema, parts=(), max_retries=1, **kwargs):
        if schema == Segment:
            return segs[0]
        return _sample_script(segs[0].name)

    with (
        patch("main.ask_gemini", side_effect=fake_ask),
        patch("main.log_generation_task", new_callable=AsyncMock) as mock_log,
    ):
        res = client.post(
            "/regenerate/section",
            json={
                "name": "Hydra Serum",
                "category": "Skincare",
                "market": "Bangladesh",
                "language": "en",
                "facts": sample_facts,
                "slots": [
                    {"index": 0, "keep_segment": True, "segment": segs[0].model_dump()},
                    {"index": 1, "keep_segment": True, "segment": segs[1].model_dump()},
                    {"index": 2, "keep_segment": True, "segment": segs[2].model_dump()},
                ],
            },
            headers=valid_headers,
        )

    assert res.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in res.text.splitlines()
        if line.startswith("data: ")
    ]
    done_events = [e for e in events if e.get("event") == "done"]
    assert len(done_events) == 1
    log_id = done_events[0].get("log_id")
    assert log_id
    uuid.UUID(log_id)
    mock_log.assert_awaited_once()
    assert mock_log.call_args.kwargs["log_id"] == log_id


# ---------------------------------------------------------------------------
# 3. POST /feedback & POST /feedback/signal
# ---------------------------------------------------------------------------


def _feedback_payload(**overrides):
    base = {
        "log_id": "log-abc-123",
        "script_index": 1,
        "rating": -1,
        "tags": ["bland", "weak_hook"],
        "comment": "Hook needs more punch.",
        "script_snapshot": _sample_script("Desk Workers").model_dump(),
        "script_format": "ugc",
        "language": "en",
        "segment_name": "Desk Workers",
    }
    base.update(overrides)
    return base


def test_feedback_requires_auth(client):
    res = client.post("/feedback", json=_feedback_payload())
    assert res.status_code == 401

    res_sig = client.post(
        "/feedback/signal",
        json={"log_id": "log-abc-123", "script_index": 0, "signal": "copy"},
    )
    assert res_sig.status_code == 401


def test_feedback_tag_rating_and_comment_validation(client, valid_headers):
    db, _, _ = _mock_firestore_for_feedback()
    set_mock_firestore(db)

    # Invalid tag
    res_bad_tag = client.post(
        "/feedback",
        json=_feedback_payload(tags=["not_a_valid_tag"]),
        headers=valid_headers,
    )
    assert res_bad_tag.status_code == 422

    # Invalid rating (0 or 5)
    res_bad_rating = client.post(
        "/feedback",
        json=_feedback_payload(rating=5),
        headers=valid_headers,
    )
    assert res_bad_rating.status_code == 422

    # Comment exceeding 500 chars
    res_long_comment = client.post(
        "/feedback",
        json=_feedback_payload(comment="x" * 501),
        headers=valid_headers,
    )
    assert res_long_comment.status_code == 422

    # All 8 constrained tags accepted & deduplicated
    res_all_tags = client.post(
        "/feedback",
        json=_feedback_payload(tags=[*FEEDBACK_TAGS, "bland"]),
        headers=valid_headers,
    )
    assert res_all_tags.status_code == 200


def test_feedback_upsert_idempotency_and_access_code_auth(client):
    db, store, writes = _mock_firestore_for_feedback()
    set_mock_firestore(db)
    headers = {"X-Access-Code": "TEST-ACCESS-CODE"}

    # First implicit signal arrives before explicit rating
    sig_res = client.post(
        "/feedback/signal",
        json={"log_id": "log-999", "script_index": 0, "signal": "copy"},
        headers=headers,
    )
    assert sig_res.status_code == 200
    assert sig_res.json() == {"success": True, "feedback_id": "log-999_0", "stored": True}
    assert store["log-999_0"]["signals"] == {"copy": 1}

    # First feedback submission: thumbs down
    fb1 = client.post(
        "/feedback",
        json=_feedback_payload(
            log_id="log-999",
            script_index=0,
            rating=-1,
            tags=["too_long"],
            comment="Trim line 3",
        ),
        headers=headers,
    )
    assert fb1.status_code == 200
    assert fb1.json()["feedback_id"] == "log-999_0"

    # Second feedback submission for same {log_id}_{script_index}: flips to thumbs up
    fb2 = client.post(
        "/feedback",
        json=_feedback_payload(
            log_id="log-999",
            script_index=0,
            rating=1,
            tags=["great_hook"],
            comment="Actually great!",
        ),
        headers=headers,
    )
    assert fb2.status_code == 200
    assert len(store) == 1  # idempotent upsert on same doc id

    doc = store["log-999_0"]
    assert doc["rating"] == 1
    assert doc["tags"] == ["great_hook"]
    assert doc["comment"] == "Actually great!"
    assert doc["access_code"] == "TEST-ACCESS-CODE"
    assert "pipeline_version" in doc
    assert "prompt_versions" in doc
    assert doc["updated_at"] == firestore.SERVER_TIMESTAMP
    assert doc["signals"] == {"copy": 1}  # preserved via merge=True
    assert all(merge is True for _, _, merge in writes)


def test_feedback_signal_atomic_increment_and_merge(client, valid_headers):
    db, store, writes = _mock_firestore_for_feedback()
    set_mock_firestore(db)

    for signal in ("copy", "copy", "save", "regenerate"):
        res = client.post(
            "/feedback/signal",
            json={"log_id": "log-sig", "script_index": 2, "signal": signal},
            headers=valid_headers,
        )
        assert res.status_code == 200
        assert res.json() == {"success": True, "feedback_id": "log-sig_2", "stored": True}

    assert store["log-sig_2"]["signals"] == {"copy": 2, "save": 1, "regenerate": 1}
    # Verify firestore.Increment(1) and merge=True were passed
    last_doc_id, last_data, last_merge = writes[-1]
    assert last_doc_id == "log-sig_2"
    assert last_merge is True
    assert isinstance(last_data["signals"]["regenerate"], firestore.Increment)
    assert last_data["signals"]["regenerate"].value == 1


def test_feedback_graceful_fallback_when_firestore_unavailable(client, valid_headers):
    broken_db = MagicMock()
    broken_coll = MagicMock()
    broken_ref = MagicMock()
    broken_ref.set = AsyncMock(side_effect=RuntimeError("Firestore offline"))
    broken_coll.document.return_value = broken_ref
    broken_db.collection.return_value = broken_coll
    set_mock_firestore(broken_db)

    res = client.post("/feedback", json=_feedback_payload(), headers=valid_headers)
    assert res.status_code == 200
    assert res.json() == {"success": True, "feedback_id": "log-abc-123_1", "stored": False}

    res_sig = client.post(
        "/feedback/signal",
        json={"log_id": "log-abc-123", "script_index": 1, "signal": "save"},
        headers=valid_headers,
    )
    assert res_sig.status_code == 200
    assert res_sig.json() == {"success": True, "feedback_id": "log-abc-123_1", "stored": False}


def test_feedback_rate_limiting(client, valid_headers):
    db, _, _ = _mock_firestore_for_feedback()
    set_mock_firestore(db)

    feedback_limiter.max_requests = 2
    try:
        for _ in range(2):
            r = client.post("/feedback", json=_feedback_payload(), headers=valid_headers)
            assert r.status_code == 200
        r_limited = client.post("/feedback", json=_feedback_payload(), headers=valid_headers)
        assert r_limited.status_code == 429
        assert "Retry-After" in r_limited.headers
    finally:
        feedback_limiter.max_requests = 60


# ---------------------------------------------------------------------------
# 4. Export Script (apps/api/scripts/export_feedback.py)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_feedback_to_jsonl_and_filters(tmp_path):
    ts = datetime(2026, 11, 18, 12, 0, 0, tzinfo=timezone.utc)
    db, _, _ = _mock_firestore_for_feedback(
        existing_docs={
            "log-1_0": {
                "feedback_id": "log-1_0",
                "log_id": "log-1",
                "script_index": 0,
                "rating": -1,
                "tags": ["bland"],
                "language": "bn",
                "script_format": "ugc",
                "segment_name": "Dhaka Commuters",
                "script_snapshot": {"segment": "Dhaka Commuters", "lines": [{"id": 1, "kind": "hook", "text": "গরমে ক্লান্ত?"}], "reasons": []},
                "updated_at": ts,
            },
            "log-2_1": {
                "feedback_id": "log-2_1",
                "log_id": "log-2",
                "script_index": 1,
                "rating": 1,
                "tags": ["great_hook"],
                "language": "en",
                "script_format": "commercial_30s",
                "segment_name": "Desk Workers",
                "script_snapshot": _sample_script("Desk Workers").model_dump(),
                "updated_at": ts,
            },
        }
    )

    out_all = tmp_path / "all.jsonl"
    records = await export_feedback_to_jsonl(out_all, db=db)
    assert len(records) == 2
    lines = out_all.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    parsed_first = json.loads(lines[0])
    assert parsed_first["updated_at"] == ts.isoformat()
    assert "গরমে ক্লান্ত?" in lines[0]

    out_bn = tmp_path / "bn_neg.jsonl"
    filtered = await export_feedback_to_jsonl(out_bn, rating=-1, language="bn", db=db)
    assert len(filtered) == 1
    assert filtered[0]["feedback_id"] == "log-1_0"
