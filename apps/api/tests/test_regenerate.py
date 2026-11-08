"""
Tests for Sprint 2 Granular Regeneration Endpoints.
Covers:
- POST /regenerate/segment
- POST /regenerate/script
- POST /regenerate/reason-lines
- POST /regenerate/line/rephrase
- POST /regenerate/line/regenerate
- POST /regenerate/section (SSE streaming)
- Authorization, validation, and language retention (en and bn).
"""

import json
from unittest.mock import AsyncMock, patch
import pytest

from schemas import (
    Line,
    LineRegenerateResponse,
    LineRephraseResponse,
    Reason,
    ReasonLinesRewriteResponse,
    RewrittenLine,
    Script,
    Segment,
)


@pytest.fixture
def sample_facts():
    return [
        "24-hour hydration formula",
        "Contains 2% pure hyaluronic acid",
        "Fragrance-free and hypoallergenic",
    ]


@pytest.fixture
def sample_segment():
    return Segment(
        name="Desk Workers",
        who="25-35 year olds working in air-conditioned offices",
        pain_point="Skin feels dry and tight by 2 PM",
        platforms=["TikTok", "Reels"],
    )


# ---------------------------------------------------------------------------
# 1. POST /regenerate/segment
# ---------------------------------------------------------------------------


def test_regenerate_segment_unauthorized(client, sample_facts, sample_segment):
    payload = {
        "name": "Hydra Serum",
        "category": "Skincare",
        "market": "Bangladesh",
        "language": "en",
        "facts": sample_facts,
        "current_segment": sample_segment.model_dump(),
        "existing_segment_names": ["Busy Mothers"],
    }
    res = client.post("/regenerate/segment", json=payload)
    assert res.status_code == 401


def test_regenerate_segment_validation_error(client, valid_headers, sample_segment):
    # Missing required 'facts'
    payload = {
        "name": "Hydra Serum",
        "category": "Skincare",
        "market": "Bangladesh",
        "language": "en",
        "facts": [],  # min_length=1
        "current_segment": sample_segment.model_dump(),
    }
    res = client.post("/regenerate/segment", json=payload, headers=valid_headers)
    assert res.status_code == 422


@patch("main.ask_gemini", new_callable=AsyncMock)
def test_regenerate_segment_success(mock_gemini, client, valid_headers, sample_facts, sample_segment):
    mock_new_segment = Segment(
        name="Night Owls & Gamers",
        who="Late night workers and gamers exposed to screen blue light",
        pain_point="Skin looks dull and tired from late nights",
        platforms=["YouTube Shorts", "TikTok"],
    )
    mock_gemini.return_value = mock_new_segment

    payload = {
        "name": "Hydra Serum",
        "category": "Skincare",
        "market": "Bangladesh",
        "language": "en",
        "facts": sample_facts,
        "current_segment": sample_segment.model_dump(),
        "existing_segment_names": ["Desk Workers", "Busy Mothers"],
    }

    res = client.post("/regenerate/segment", json=payload, headers=valid_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Night Owls & Gamers"
    assert data["platforms"] == ["YouTube Shorts", "TikTok"]

    # Verify prompt received the other segment names
    prompt_used = mock_gemini.call_args[1]["prompt"]
    assert "Desk Workers" in prompt_used
    assert "Busy Mothers" in prompt_used


@patch("main.ask_gemini", new_callable=AsyncMock)
def test_regenerate_segment_bangla_retention(mock_gemini, client, valid_headers, sample_facts, sample_segment):
    mock_bn_segment = Segment(
        name="কলেজ শিক্ষার্থী ও তরুণরা",
        who="পকেট খরচ সামলে চলা কলেজ ও বিশ্ববিদ্যালয়ের তরুণ-তরুণী",
        pain_point="অল্প খরচে ভালো মানের স্কিনকেয়ার প্রোডাক্ট খুঁজে পাওয়া যায় না",
        platforms=["TikTok", "Instagram Reels"],
    )
    mock_gemini.return_value = mock_bn_segment

    payload = {
        "name": "Hydra Serum",
        "category": "Skincare",
        "market": "Bangladesh",
        "language": "bn",
        "facts": sample_facts,
        "current_segment": sample_segment.model_dump(),
        "existing_segment_names": [],
    }

    res = client.post("/regenerate/segment", json=payload, headers=valid_headers)
    assert res.status_code == 200
    data = res.json()
    assert "কলেজ শিক্ষার্থী" in data["name"]

    # Verify Bengali language block in prompt
    prompt_used = mock_gemini.call_args[1]["prompt"]
    assert "Bangla" in prompt_used
    assert "বাংলা" in prompt_used


# ---------------------------------------------------------------------------
# 2. POST /regenerate/script
# ---------------------------------------------------------------------------


def test_rewrite_script_unauthorized(client, sample_facts, sample_segment):
    payload = {
        "name": "Hydra Serum",
        "category": "Skincare",
        "market": "Bangladesh",
        "language": "en",
        "facts": sample_facts,
        "segment": sample_segment.model_dump(),
    }
    res = client.post("/regenerate/script", json=payload)
    assert res.status_code == 401


@patch("main.ask_gemini", new_callable=AsyncMock)
def test_rewrite_script_success(mock_gemini, client, valid_headers, sample_facts, sample_segment):
    mock_script = Script(
        segment="Desk Workers",
        lines=[
            Line(id=1, kind="hook", text="Working under AC all day? Watch this."),
            Line(id=2, kind="concept", text="2% pure hyaluronic acid keeps skin plump for 24 hours."),
            Line(id=3, kind="concept", text="No sticky residue under your makeup."),
            Line(id=4, kind="cta", text="Grab yours before the sale ends."),
        ],
        reasons=[
            Reason(title="Direct Callout Hook", why="Targets AC office workers instantly.", line_ids=[1]),
            Reason(title="Clinical Specificity", why="Names 2% hyaluronic acid.", line_ids=[2]),
            Reason(title="Benefit CTA", why="Creates immediate buying incentive.", line_ids=[3, 4]),
        ],
    )
    mock_gemini.return_value = mock_script

    payload = {
        "name": "Hydra Serum",
        "category": "Skincare",
        "market": "Bangladesh",
        "language": "en",
        "facts": sample_facts,
        "segment": sample_segment.model_dump(),
        "hook_style": "problem callout",
    }

    res = client.post("/regenerate/script", json=payload, headers=valid_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["segment"] == "Desk Workers"
    assert len(data["lines"]) == 4
    assert len(data["reasons"]) == 3
    assert data["lines"][0]["kind"] == "hook"
    assert data["lines"][3]["kind"] == "cta"


# ---------------------------------------------------------------------------
# 3. POST /regenerate/reason-lines
# ---------------------------------------------------------------------------


@patch("main.ask_gemini", new_callable=AsyncMock)
def test_rewrite_reason_lines_success(mock_gemini, client, valid_headers, sample_facts, sample_segment):
    mock_response = ReasonLinesRewriteResponse(
        lines=[
            RewrittenLine(kind="concept", text="Formulated with clinical-grade 2% pure hyaluronic acid."),
            RewrittenLine(kind="concept", text="It locks in cellular moisture without clogging pores."),
        ]
    )
    mock_gemini.return_value = mock_response

    payload = {
        "name": "Hydra Serum",
        "market": "Bangladesh",
        "language": "en",
        "facts": sample_facts,
        "segment": sample_segment.model_dump(),
        "full_script": [
            {"id": 1, "kind": "hook", "text": "Is your AC drying out your skin?"},
            {"id": 2, "kind": "concept", "text": "Here is the ingredient breakdown."},
            {"id": 3, "kind": "concept", "text": "It hydrates your face deeply."},
            {"id": 4, "kind": "cta", "text": "Order now!"},
        ],
        "target_line_ids": [2, 3],
        "reason": {
            "title": "Clinical Ingredient Specificity",
            "why": "Establishes scientific authority with 2% hyaluronic acid claim.",
        },
    }

    res = client.post("/regenerate/reason-lines", json=payload, headers=valid_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["lines"]) == 2
    assert "clinical-grade" in data["lines"][0]["text"]


# ---------------------------------------------------------------------------
# 4. POST /regenerate/line/rephrase
# ---------------------------------------------------------------------------


@patch("main.ask_gemini", new_callable=AsyncMock)
def test_rephrase_line_success(mock_gemini, client, valid_headers, sample_facts, sample_segment):
    mock_response = LineRephraseResponse(
        text="Quick fact: 2 drops give you 24 hours of locked-in hydration.",
        tone="punchy",
    )
    mock_gemini.return_value = mock_response

    payload = {
        "name": "Hydra Serum",
        "market": "Bangladesh",
        "language": "en",
        "facts": sample_facts,
        "segment": sample_segment.model_dump(),
        "script_context": [
            {"id": 1, "kind": "hook", "text": "Stop scrolling right now!"},
            {"id": 2, "kind": "concept", "text": "This serum provides deep hydration all day long."},
        ],
        "line_id": 2,
        "current_text": "This serum provides deep hydration all day long.",
        "kind": "concept",
        "avoid_tones": ["casual"],
    }

    res = client.post("/regenerate/line/rephrase", json=payload, headers=valid_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["tone"] == "punchy"
    assert "Quick fact:" in data["text"]

    prompt_used = mock_gemini.call_args[1]["prompt"]
    assert "casual" in prompt_used


# ---------------------------------------------------------------------------
# 5. POST /regenerate/line/regenerate
# ---------------------------------------------------------------------------


@patch("main.ask_gemini", new_callable=AsyncMock)
def test_regenerate_line_success(mock_gemini, client, valid_headers, sample_facts, sample_segment):
    mock_response = LineRegenerateResponse(
        text="Wait, did you know air conditioning pulls moisture straight out of your pores?",
        kind="hook",
    )
    mock_gemini.return_value = mock_response

    payload = {
        "name": "Hydra Serum",
        "market": "Bangladesh",
        "language": "en",
        "facts": sample_facts,
        "segment": sample_segment.model_dump(),
        "script_context": [
            {"id": 1, "kind": "hook", "text": "Dry skin alert!"},
            {"id": 2, "kind": "concept", "text": "Use pure hyaluronic acid."},
        ],
        "line_id": 1,
        "current_text": "Dry skin alert!",
        "kind": "hook",
    }

    res = client.post("/regenerate/line/regenerate", json=payload, headers=valid_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["kind"] == "hook"
    assert "air conditioning" in data["text"]


# ---------------------------------------------------------------------------
# 6. POST /regenerate/section (SSE Stream)
# ---------------------------------------------------------------------------


@patch("main.ask_gemini", new_callable=AsyncMock)
def test_regenerate_section_stream(mock_gemini, client, valid_headers, sample_facts, sample_segment):
    # Mock calls:
    # Slot 0 kept -> no segment call needed
    # Slot 1 new -> calls ask_gemini with Segment
    # Slot 2 new -> calls ask_gemini with Segment
    # 3 scripts -> calls ask_gemini with Script for each
    mock_seg = Segment(
        name="Campus Students",
        who="18-24 college students",
        pain_point="Pocket money limit",
        platforms=["TikTok"],
    )
    mock_scr = Script(
        segment="Test",
        lines=[
            Line(id=1, kind="hook", text="Hook line"),
            Line(id=2, kind="concept", text="Concept line"),
            Line(id=3, kind="cta", text="CTA line"),
        ],
        reasons=[
            Reason(title="Test", why="Why", line_ids=[1]),
            Reason(title="Test 2", why="Why 2", line_ids=[2]),
            Reason(title="Test 3", why="Why 3", line_ids=[3]),
        ],
    )

    async def side_effect(prompt, schema, *args, **kwargs):
        if schema == Segment:
            return mock_seg
        return mock_scr

    mock_gemini.side_effect = side_effect

    payload = {
        "name": "Hydra Serum",
        "category": "Skincare",
        "market": "Bangladesh",
        "language": "en",
        "facts": sample_facts,
        "slots": [
            {"index": 0, "keep_segment": True, "segment": sample_segment.model_dump()},
            {"index": 1, "keep_segment": False, "segment": None},
            {"index": 2, "keep_segment": False, "segment": None},
        ],
    }

    res = client.post("/regenerate/section", json=payload, headers=valid_headers)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    events = []
    for line in res.iter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    event_types = [e.get("event") for e in events]
    assert "segments" in event_types
    assert "script" in event_types
    assert "done" in event_types

    # Verify Stage 1 segment output kept slot 0
    segments_event = next(e for e in events if e.get("event") == "segments")
    assert len(segments_event["segments"]) == 3
    assert segments_event["segments"][0]["name"] == "Desk Workers"
