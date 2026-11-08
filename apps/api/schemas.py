"""
Data schemas for the Script Assistant API.

These Pydantic models define both:
1. The structured output schemas passed to Gemini on Vertex AI via the google-genai SDK.
2. The HTTP API response contracts for FastAPI and generated OpenAPI/TypeScript types.
"""

from typing import Literal
from pydantic import BaseModel, Field


class Segment(BaseModel):
    """
    Represents a specific target audience / customer segment.
    """
    name: str = Field(
        ...,
        description="Clear, descriptive title for this customer segment (e.g., 'Exhausted Working Parents')"
    )
    who: str = Field(
        ...,
        description="Demographics, daily context, and life situation of this audience persona"
    )
    pain_point: str = Field(
        ...,
        description="Core frustration, anxiety, or unmet desire expressed in their own natural words"
    )
    platforms: list[str] = Field(
        ...,
        description="Short-form platforms where this segment is most active (e.g., ['TikTok', 'Instagram Reels', 'YouTube Shorts'])"
    )


class Segments(BaseModel):
    """
    Output model for Stage 1 of the pipeline: verifiable product facts and 3 audience segments.
    """
    product_facts: list[str] = Field(
        ...,
        description="5 to 8 concrete, verifiable facts drawn ONLY from the product description and image"
    )
    segments: list[Segment] = Field(
        ...,
        description="Exactly 3 distinct customer segments that differ in motivation and context"
    )


class Line(BaseModel):
    """
    A single spoken line or beat within a UGC video script.
    """
    id: int = Field(
        ...,
        description="1-based sequential line index used for referencing in rationale reasons"
    )
    kind: Literal['hook', 'concept', 'cta'] = Field(
        ...,
        description="Role of this line in the video structure: 'hook' (0-3s), 'concept' (body), or 'cta' (action)"
    )
    text: str = Field(
        ...,
        description="Spoken dialogue or voiceover text meant to be delivered naturally on camera"
    )


class Reason(BaseModel):
    """
    Performance rationale explaining why a specific technique was incorporated into the script.
    """
    title: str = Field(
        ...,
        description="Short name of the performance marketing technique (e.g., 'Curiosity Gap Hook', 'Direct Objection Handling')"
    )
    why: str = Field(
        ...,
        description="Explanation of why this technique specifically resonates with this target segment"
    )
    line_ids: list[int] = Field(
        ...,
        description="List of 1-based line IDs from the script that demonstrate this technique"
    )


class Script(BaseModel):
    """
    Complete ready-to-film short-form video ad script for a specific customer segment.
    """
    segment: str = Field(
        ...,
        description="Name of the customer segment this script is customized for"
    )
    lines: list[Line] = Field(
        ...,
        description="Ordered sequence of script lines structured as hook, concept, and cta"
    )
    reasons: list[Reason] = Field(
        ...,
        description="Exactly 3 reasons explaining why the script is constructed this way"
    )


class GenerateResponse(BaseModel):
    """
    The top-level response payload returned by POST /generate.
    """
    facts: list[str] = Field(
        ...,
        description="5 to 8 verifiable product facts extracted from image and description"
    )
    segments: list[Segment] = Field(
        ...,
        description="The 3 customer segments identified for the product"
    )
    scripts: list[Script] = Field(
        ...,
        description="The 3 customized scripts, each targeting one of the customer segments"
    )
