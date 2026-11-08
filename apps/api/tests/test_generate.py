"""
Tests for POST /generate pipeline execution, mock generation, and response structuring.
"""

import io
from unittest.mock import AsyncMock, patch

from schemas import Line, Reason, Script, Segment, Segments


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
            Line(id=2, kind="concept", text="This formula locks in moisture with 2% pure hyaluronic acid."),
            Line(id=3, kind="concept", text="It restores your barrier in just two drops daily."),
            Line(id=4, kind="cta", text="Tap the link below to get yours with free shipping."),
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
                line_ids=[2],
            ),
            Reason(
                title="Direct Action CTA",
                why="Reduces friction with an immediate free shipping incentive.",
                line_ids=[4],
            ),
        ],
    )


def test_generate_pipeline_success(client, valid_form_data, sample_png_bytes, valid_headers):
    """
    Verifies that the full pipeline handles Stage 1 facts/segments and Stage 2 parallel
    script generation, correctly returning a 200 payload adhering to GenerateResponse.
    """
    mock_segs = mock_segments_data()

    async def fake_ask(prompt, schema, parts=(), max_retries=1):
        if schema == Segments:
            return mock_segs
        elif schema == Script:
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
        assert len(first_script["lines"]) == 4
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
