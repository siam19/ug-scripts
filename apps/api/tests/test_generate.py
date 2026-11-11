"""
Tests for POST /generate pipeline execution, mock generation, and response structuring.
"""

import io
from unittest.mock import AsyncMock, patch

from schemas import Line, Reason, Script, ScriptDraft, Segment, Segments


def mock_segments_data():
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
                who="25-35 year olds working in air-conditioned offices",
                pain_point="Skin feels dry and tight by 2 PM",
                platforms=["TikTok", "Reels"],
            ),
            Segment(
                name="Busy Mothers",
                who="30-45 year old working moms",
                pain_point="No time for an elaborate 10-step skincare routine",
                platforms=["Instagram Reels", "Facebook"],
            ),
            Segment(
                name="Outdoor Commuters",
                who="Young urban professionals commuting daily in heat and pollution",
                pain_point="Pollution and heat strip skin barrier",
                platforms=["TikTok", "YouTube Shorts"],
            ),
        ],
    )


def mock_script_data(segment_name: str):
    return Script(
        segment=segment_name,
        lines=[
            Line(id=1, kind="hook", text="Stop scrolling if your skin feels like sandpaper by midday!"),
            Line(id=2, kind="concept", text="Working long hours in air-conditioned offices constantly strips moisture from your skin barrier."),
            Line(id=3, kind="concept", text="This lightweight formula locks in deep hydration with 2% pure hyaluronic acid all day long."),
            Line(id=4, kind="concept", text="It fully restores your protective moisture barrier in just two daily morning drops without greasiness."),
            Line(id=5, kind="concept", text="Within three weeks of consistent daily application, midday dryness completely disappears from your routine."),
            Line(id=6, kind="cta", text="Tap the link below to get yours with free express shipping today."),
        ],
        reasons=[
            Reason(
                title="Pattern Interrupt Hook",
                why="Stops the scroll by calling out the midday dry skin sensation immediately.",
                line_ids=[1],
            ),
            Reason(
                title="Ingredient Specificity",
                why="Highlights the clinical 2% hyaluronic acid fact to build instant trust.",
                line_ids=[3, 4],
            ),
            Reason(
                title="Direct Action CTA",
                why="Reduces friction with an immediate free shipping incentive.",
                line_ids=[6],
            ),
        ],
    )


def test_generate_pipeline_success(client, valid_form_data, sample_png_bytes, valid_headers):
    """
    Verifies that the full pipeline handles Stage 1 facts/segments and Stage 2 parallel
    script generation, correctly returning a 200 payload adhering to GenerateResponse.
    """
    mock_segs = mock_segments_data()

    async def fake_ask(prompt, schema, parts=(), max_retries=1, **kwargs):
        if schema == Segments:
            return mock_segs
        elif schema in (Script, ScriptDraft):
            # Extract segment name or default
            return mock_script_data("Desk Workers")
        raise ValueError(f"Unexpected schema: {schema}")

    with patch("main.ask_gemini", side_effect=fake_ask) as patched_ask:
        files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
        response = client.post("/generate", data=valid_form_data, files=files, headers=valid_headers)

        assert response.status_code == 200
        payload = response.json()

        # Check top-level contract
        assert "facts" in payload
        assert "segments" in payload
        assert "scripts" in payload

        # Check data contents
        assert len(payload["facts"]) == 5
        assert len(payload["segments"]) == 3
        assert len(payload["scripts"]) == 3

        # Verify Stage 1 and Stage 2 invocation counts
        # 1 call for Segments + 3 parallel calls for Scripts = 4 total calls
        assert patched_ask.call_count == 4

        # Validate first script schema
        first_script = payload["scripts"][0]
        assert len(first_script["lines"]) == 6
        assert first_script["lines"][0]["kind"] == "hook"
        assert len(first_script["reasons"]) == 3
        assert first_script["reasons"][0]["line_ids"] == [1]


def test_generate_handles_upstream_vertex_ai_error(client, valid_form_data, sample_png_bytes, valid_headers):
    """
    Verifies that unhandled upstream Vertex AI exceptions are converted to clean 502 HTTP errors.
    """
    with patch("main.get_genai_client") as mock_get_client:
        mock_client = mock_get_client.return_value
        mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("Vertex AI Quota Exceeded"))

        files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
        response = client.post("/generate", data=valid_form_data, files=files, headers=valid_headers)

        assert response.status_code == 502
        assert "Vertex AI generation error" in response.json()["detail"]


def test_generate_stream_pipeline_success(client, valid_form_data, sample_png_bytes, valid_headers):
    """
    Verifies that POST /generate-stream returns a text/event-stream response and
    progressively yields Stage 1 segments followed by each completed script and 'done'.
    """
    import json

    mock_segs = mock_segments_data()

    async def fake_ask(prompt, schema, parts=(), max_retries=1, **kwargs):
        if schema == Segments:
            return mock_segs
        elif schema in (Script, ScriptDraft):
            return mock_script_data("Desk Workers")
        raise ValueError(f"Unexpected schema: {schema}")

    with patch("main.ask_gemini", side_effect=fake_ask) as patched_ask:
        files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
        response = client.post("/generate-stream", data=valid_form_data, files=files, headers=valid_headers)

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = []
        for line in response.text.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        assert len(events) == 5  # 1 segments + 3 scripts + 1 done

        # First event is segments
        assert events[0]["event"] == "segments"
        assert len(events[0]["facts"]) == 5
        assert len(events[0]["segments"]) == 3

        # Next 3 events are scripts
        script_events = events[1:4]
        script_indices = set()
        for se in script_events:
            assert se["event"] == "script"
            script_indices.add(se["index"])
            assert "script" in se
            assert len(se["script"]["lines"]) == 6

        assert script_indices == {0, 1, 2}

        # Last event is done
        assert events[4]["event"] == "done"
        assert patched_ask.call_count == 4


def test_generate_stream_handles_upstream_vertex_ai_error(client, valid_form_data, sample_png_bytes, valid_headers):
    """
    Verifies that upstream errors during streaming yield an SSE error event.
    """
    import json

    with patch("main.ask_gemini", side_effect=Exception("Vertex AI Stream Error")):
        files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
        response = client.post("/generate-stream", data=valid_form_data, files=files, headers=valid_headers)

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = []
        for line in response.text.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        assert len(events) == 1
        assert events[0]["event"] == "error"
        assert "Vertex AI Stream Error" in events[0]["detail"]


def test_generate_stream_missing_api_key_returns_401(client, valid_form_data, sample_png_bytes):
    """
    Verifies that authorization check runs before streaming starts and returns HTTP 401.
    """
    files = {"image": ("test.png", io.BytesIO(sample_png_bytes), "image/png")}
    response = client.post("/generate-stream", data=valid_form_data, files=files)
    assert response.status_code == 401
