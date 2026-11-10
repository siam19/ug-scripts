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


# ---------------------------------------------------------------------------
# Sprint 2: Granular Regeneration Request & Response Schemas
# ---------------------------------------------------------------------------


class ReasonInfo(BaseModel):
    """
    Marketing technique details attached to a line-group rewrite request.
    """
    title: str = Field(..., description="Technique name (e.g., 'Direct Objection Handling')")
    why: str = Field(..., description="Psychological explanation for why this works on the segment")


class ScriptLineContext(BaseModel):
    """
    Contextual representation of a visible script line provided for narrative flow.
    """
    id: int = Field(..., description="1-based position in visible script")
    kind: Literal['hook', 'concept', 'cta'] = Field(..., description="Role of this line in the video")
    text: str = Field(..., description="Dialogue text")


class RewrittenLine(BaseModel):
    """
    A single line generated as part of a reason line-group rewrite.
    """
    kind: Literal['hook', 'concept', 'cta'] = Field(..., description="Role of this line")
    text: str = Field(..., description="New dialogue text in the target language")


class SegmentRegenerateRequest(BaseModel):
    """
    Request model for POST /regenerate/segment.
    Generates a unique customer segment differing from all other active segments.
    """
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    market: str = Field(..., description="Target market (e.g., 'Bangladesh', 'Global')")
    language: Literal['en', 'bn'] = Field(..., description="Target language ('en' for English, 'bn' for Bangla)")
    facts: list[str] = Field(..., min_length=1, description="Current active product facts")
    current_segment: Segment = Field(..., description="The segment being replaced")
    existing_segment_names: list[str] = Field(
        default_factory=list,
        description="Names of other active segments to guarantee the new one is unique"
    )


class ScriptRewriteRequest(BaseModel):
    """
    Request model for POST /regenerate/script.
    Regenerates a complete script for a specific segment against active facts.
    """
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    market: str = Field(..., description="Target market")
    language: Literal['en', 'bn'] = Field(..., description="Target language")
    facts: list[str] = Field(..., min_length=1, description="Current product facts")
    segment: Segment = Field(..., description="Target segment (may include user edits)")
    hook_style: str | None = Field(
        None,
        description="Optional hook angle ('curiosity question', 'problem callout', 'demo / before-after')"
    )


class ReasonLinesRewriteRequest(BaseModel):
    """
    Request model for POST /regenerate/reason-lines.
    Rewrites the line group associated with a specific marketing technique.
    """
    name: str = Field(..., description="Product name")
    market: str = Field(..., description="Target market")
    language: Literal['en', 'bn'] = Field(..., description="Target language")
    facts: list[str] = Field(..., min_length=1, description="Current product facts")
    segment: Segment = Field(..., description="Target segment")
    full_script: list[ScriptLineContext] = Field(..., description="Complete sequence of visible script lines")
    target_line_ids: list[int] = Field(..., min_length=1, description="The sequential line IDs to replace")
    reason: ReasonInfo = Field(..., description="The rationale technique to regenerate and strengthen")


class ReasonLinesRewriteResponse(BaseModel):
    """
    Response model for POST /regenerate/reason-lines.
    """
    lines: list[RewrittenLine] = Field(
        ...,
        min_length=1,
        description="Replacement line sequence (count may vary slightly if required to fulfill the technique)"
    )


class LineRephraseRequest(BaseModel):
    """
    Request model for POST /regenerate/line/rephrase.
    Rephrases a single sentence to maintain core meaning while shifting tone.
    """
    name: str = Field(..., description="Product name")
    market: str = Field(..., description="Target market")
    language: Literal['en', 'bn'] = Field(..., description="Target language")
    facts: list[str] = Field(..., min_length=1, description="Current product facts")
    segment: Segment = Field(..., description="Target customer segment")
    script_context: list[ScriptLineContext] = Field(
        ...,
        description="Visible lines surrounding the target line to maintain narrative flow"
    )
    line_id: int = Field(..., description="Line ID of the target line")
    current_text: str = Field(..., description="Existing line dialogue to rephrase")
    kind: Literal['hook', 'concept', 'cta'] = Field(..., description="Role of the line")
    avoid_tones: list[str] = Field(
        default_factory=list,
        description="List of tones already attempted for this line (e.g. ['punchy', 'casual'])"
    )


class LineRephraseResponse(BaseModel):
    """
    Response model for POST /regenerate/line/rephrase.
    """
    text: str = Field(..., description="Rephrased dialogue text in target language")
    tone: str = Field(..., description="Selected tone identifier (e.g., 'punchy', 'casual', 'authentic', 'direct')")


class LineRegenerateRequest(BaseModel):
    """
    Request model for POST /regenerate/line/regenerate.
    Replaces a single line with an alternative angle or idea for that position.
    """
    name: str = Field(..., description="Product name")
    market: str = Field(..., description="Target market")
    language: Literal['en', 'bn'] = Field(..., description="Target language")
    facts: list[str] = Field(..., min_length=1, description="Current product facts")
    segment: Segment = Field(..., description="Target customer segment")
    script_context: list[ScriptLineContext] = Field(
        ...,
        description="Visible lines before and after the line"
    )
    line_id: int = Field(..., description="Line ID of the target line")
    current_text: str = Field(..., description="Existing dialogue being replaced")
    kind: Literal['hook', 'concept', 'cta'] = Field(..., description="Role of the line")


class LineRegenerateResponse(BaseModel):
    """
    Response model for POST /regenerate/line/regenerate.
    """
    text: str = Field(..., description="Freshly generated line in the target language")
    kind: Literal['hook', 'concept', 'cta'] = Field(..., description="Verified line kind")


class SlotConfig(BaseModel):
    """
    Configuration for an individual customer segment slot during section regeneration.
    """
    index: int = Field(..., description="Slot index (0..2)")
    keep_segment: bool = Field(False, description="Whether to keep the existing segment data")
    segment: Segment | None = Field(None, description="Segment to retain if keep_segment is True")


class SectionRegenerateRequest(BaseModel):
    """
    Request model for POST /regenerate/section.
    Regenerates customer segments and scripts progressively after facts updates.
    """
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    market: str = Field(..., description="Target market")
    language: Literal['en', 'bn'] = Field(..., description="Target language")
    facts: list[str] = Field(..., min_length=1, description="Current active product facts")
    slots: list[SlotConfig] = Field(
        default_factory=list,
        description="Configuration for each slot indicating whether to preserve or replace"
    )


# ---------------------------------------------------------------------------
# Sprint 3: Security, Telemetry, & Demo Product Models
# ---------------------------------------------------------------------------


class TokenUsage(BaseModel):
    """Token accounting breakdown for a generation call."""
    input_tokens: int = Field(default=0, ge=0, description="Prompt tokens consumed")
    output_tokens: int = Field(default=0, ge=0, description="Completion tokens generated")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")


class VerifyAccessRequest(BaseModel):
    """Request model for POST /auth/verify."""
    code: str = Field(..., min_length=3, max_length=50, description="Demo access code")


class VerifyAccessResponse(BaseModel):
    """Response model for POST /auth/verify."""
    valid: bool = Field(..., description="Whether the access code is valid and active")
    owner_name: str = Field(default="", description="Tester or organization name")
    company: str = Field(default="", description="Company name")
    total_tokens: int = Field(default=0, description="Lifetime total tokens consumed by this code")
    total_input_tokens: int = Field(default=0, description="Lifetime input tokens consumed")
    total_output_tokens: int = Field(default=0, description="Lifetime output tokens generated")


class AccessRequestCreate(BaseModel):
    """Request model for POST /auth/request-access."""
    name: str = Field(..., min_length=2, max_length=100, description="Requester's full name")
    phone: str = Field(..., min_length=6, max_length=25, description="Requester's contact phone number")
    company: str = Field(..., min_length=2, max_length=100, description="Requester's company or agency")


class AccessRequestResponse(BaseModel):
    """Response model for POST /auth/request-access."""
    success: bool = Field(..., description="Whether the request was successfully recorded")
    message: str = Field(..., description="Confirmation feedback for the user")


class DemoProduct(BaseModel):
    """Pre-curated demo product model."""
    id: str = Field(..., description="Unique product slug")
    name: str = Field(..., description="Product title")
    category: str = Field(..., description="Product category")
    description: str = Field(..., description="Detailed product description")
    market: str = Field(..., description="Target market (e.g., Bangladesh, US)")
    language: Literal['en', 'bn'] = Field(..., description="Target dialogue language")
    image_url: str = Field(..., description="Direct HTTPS URL to sample product image")
    order: int = Field(default=0, description="Display order sequence")


class DemoProductsResponse(BaseModel):
    """Response model for GET /demo-products."""
    products: list[DemoProduct] = Field(default_factory=list, description="List of preset demo products")

