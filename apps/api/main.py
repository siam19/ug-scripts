"""
Script Assistant API - Main FastAPI Service

This service powers the Billo-style AI UGC script writer:
1. Accepts product information (name, description, category, market, language, image).
2. Executes Stage 1 (Gemini on Vertex AI): Extracts 5-8 verifiable product facts and 3 customer segments.
3. Executes Stage 2 (Parallel Gemini calls): Generates 3 customized UGC scripts (one per segment)
   with dedicated hook styles, timestamped line sequences, and technique rationales.
4. Returns facts, segments, and scripts for the frontend application.
"""

import asyncio
import json
import os
from typing import Literal, Sequence, Any
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types

from schemas import (
    GenerateResponse,
    Line,
    LineRegenerateRequest,
    LineRegenerateResponse,
    LineRephraseRequest,
    LineRephraseResponse,
    Reason,
    ReasonLinesRewriteRequest,
    ReasonLinesRewriteResponse,
    Script,
    ScriptRewriteRequest,
    SectionRegenerateRequest,
    Segment,
    SegmentRegenerateRequest,
    Segments,
)
from prompts import (
    REGENERATE_LINE_PROMPT,
    REGENERATE_SEGMENT_PROMPT,
    REPHRASE_LINE_PROMPT,
    REWRITE_REASON_LINES_PROMPT,
    REWRITE_SCRIPT_PROMPT,
    SCRIPT_PROMPT,
    SEGMENT_PROMPT,
    format_avoid_tones,
    format_facts_text,
    format_script_context,
    get_language_block,
)

# Load environment variables from .env file if available (e.g. apps/api/.env or repo root)
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Constants and Configuration
DEFAULT_MODEL = "gemini-3.5-flash"
LANGUAGES = {"en": "English", "bn": "Bangla"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
HOOKS = [
    "curiosity question",
    "problem callout",
    "demo / before-after",
]

# FastAPI Application instance
app = FastAPI(
    title="Script Assistant API",
    description="Generates customer segments and ready-to-film UGC scripts using Gemini on Vertex AI.",
    version="1.0.0",
)

# Configure CORS Middleware
allowed_origins_raw = os.environ.get("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]
if not allowed_origins:
    # Default local development origins for Vite
    allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in allowed_origins else allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Global GenAI client cache
_genai_client: genai.Client | None = None


def get_genai_client() -> genai.Client:
    """
    Initializes and returns a singleton google-genai Client targeting Vertex AI.
    Lazy initialization ensures the app can start and export OpenAPI specs even if
    GCP credentials are not yet configured in the environment.
    """
    global _genai_client
    if _genai_client is None:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GOOGLE_CLOUD_PROJECT environment variable is not configured.",
            )
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        _genai_client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
    return _genai_client


async def ask_gemini(
    prompt: str,
    schema: type[Any],
    parts: Sequence[Any] = (),
    max_retries: int = 1,
) -> Any:
    """
    Helper function to invoke Gemini on Vertex AI asynchronously with structured output.
    Returns the parsed Pydantic object corresponding to the provided schema.
    """
    client = get_genai_client()
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    for attempt in range(max_retries + 1):
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=[*parts, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            parsed = response.parsed
            if parsed is not None:
                return parsed
            raise ValueError("Model response did not contain parsed structured data.")
        except Exception as e:
            if attempt == max_retries:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Vertex AI generation error: {str(e)}",
                )
            await asyncio.sleep(1)


def check_authorization(x_api_key: str | None) -> None:
    """Verifies that the provided X-API-Key matches the configured API_KEY."""
    expected_api_key = os.environ.get("API_KEY")
    if not expected_api_key or x_api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad or missing API key. Provide a valid 'X-API-Key' header.",
        )


def validate_market_and_image(market: str, image: UploadFile) -> str:
    """Validates market string length and image media type."""
    market_clean = market.strip()
    if not market_clean or len(market_clean) > 60:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Market must be between 1 and 60 characters.",
        )

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{image.content_type}'. Use JPEG, PNG, or WebP.",
        )

    return market_clean


async def read_and_validate_image_bytes(image: UploadFile) -> bytes:
    """Reads uploaded image file bytes and enforces maximum size limit."""
    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be 5 MB or smaller.",
        )
    return image_bytes


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for Cloud Run and monitoring probes.
    """
    return {
        "status": "healthy",
        "project_configured": bool(os.environ.get("GOOGLE_CLOUD_PROJECT")),
        "model": os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
    }


@app.post(
    "/generate",
    response_model=GenerateResponse,
    tags=["Script Generation"],
    summary="Generate customer segments and 3 UGC scripts from product details and image",
)
async def generate(
    name: str = Form(..., description="Product name"),
    description: str = Form(..., description="Detailed product description"),
    category: str = Form(..., description="Product category"),
    market: str = Form(..., description="Target market country or region (e.g., 'Bangladesh')"),
    language: Literal["en", "bn"] = Form(..., description="Desired script language: 'en' for English or 'bn' for Bangla"),
    image: UploadFile = File(..., description="Product image file (JPEG, PNG, or WebP, max 5 MB)"),
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
):
    """
    Pipeline:
    1. Authenticate request using X-API-Key header.
    2. Validate input constraints (market length, image mime type, file size).
    3. Stage 1: Send product image + details to Gemini to extract verifiable facts & 3 segments.
    4. Stage 2: In parallel, generate 3 UGC scripts customized for each segment with assigned hook styles.
    5. Return unified facts, segments, and scripts.
    """
    check_authorization(x_api_key)
    market_clean = validate_market_and_image(market, image)
    image_bytes = await read_and_validate_image_bytes(image)

    # Create image part for the multi-modal call
    img_part = types.Part.from_bytes(data=image_bytes, mime_type=image.content_type)

    # 3. Stage 1: Facts and Segments Extraction
    segment_prompt = SEGMENT_PROMPT.format(
        name=name,
        category=category,
        description=description,
        market=market_clean,
    )
    segs: Segments = await ask_gemini(
        prompt=segment_prompt,
        schema=Segments,
        parts=[img_part],
    )

    # Format facts list for injection into Stage 2 script prompts
    facts_text = "\n".join(f"- {fact}" for fact in segs.product_facts)

    # 4. Stage 2: Parallel Script Generation (One per Segment)
    async def generate_single_script(index: int, segment: Segment) -> Script:
        hook_style = HOOKS[index % len(HOOKS)]
        prompt = SCRIPT_PROMPT.format(
            name=name,
            category=category,
            facts=facts_text,
            segment_name=segment.name,
            who=segment.who,
            pain_point=segment.pain_point,
            hook=hook_style,
            market=market_clean,
            language=LANGUAGES[language],
        )
        return await ask_gemini(prompt=prompt, schema=Script)

    # Execute all 3 script calls concurrently
    scripts: list[Script] = await asyncio.gather(*[
        generate_single_script(i, s) for i, s in enumerate(segs.segments)
    ])

    # 5. Build and Return Final Unified Response
    return GenerateResponse(
        facts=segs.product_facts,
        segments=segs.segments,
        scripts=scripts,
    )


@app.post(
    "/generate-stream",
    tags=["Script Generation"],
    summary="Progressively stream customer segments and generated UGC scripts via SSE",
)
async def generate_stream(
    name: str = Form(..., description="Product name"),
    description: str = Form(..., description="Detailed product description"),
    category: str = Form(..., description="Product category"),
    market: str = Form(..., description="Target market country or region (e.g., 'Bangladesh')"),
    language: Literal["en", "bn"] = Form(..., description="Desired script language: 'en' for English or 'bn' for Bangla"),
    image: UploadFile = File(..., description="Product image file (JPEG, PNG, or WebP, max 5 MB)"),
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
):
    """
    Progressive SSE Pipeline:
    1. Authenticate request using X-API-Key header.
    2. Validate input constraints (market length, image mime type, file size).
    3. Stage 1: Send product image + details to Gemini to extract verifiable facts & 3 segments.
       -> Yields 'segments' event immediately.
    4. Stage 2: In parallel, generate 3 UGC scripts customized for each segment.
       -> Yields each 'script' event as soon as its generation completes.
    5. Yields 'done' event when all scripts are generated, or 'error' event on failure.
    """
    check_authorization(x_api_key)
    market_clean = validate_market_and_image(market, image)
    image_bytes = await read_and_validate_image_bytes(image)

    img_part = types.Part.from_bytes(data=image_bytes, mime_type=image.content_type)

    async def event_generator():
        try:
            # 1. Stage 1: Facts and Segments Extraction
            segment_prompt = SEGMENT_PROMPT.format(
                name=name,
                category=category,
                description=description,
                market=market_clean,
            )
            segs: Segments = await ask_gemini(
                prompt=segment_prompt,
                schema=Segments,
                parts=[img_part],
            )

            # Emit Stage 1 facts and segments
            stage1_data = {
                "event": "segments",
                "facts": segs.product_facts,
                "segments": [s.model_dump() for s in segs.segments],
            }
            yield f"data: {json.dumps(stage1_data)}\n\n"

            # 2. Stage 2: Parallel Script Generation (One per Segment)
            facts_text = "\n".join(f"- {fact}" for fact in segs.product_facts)

            async def generate_single_script(index: int, segment: Segment) -> tuple[int, Script]:
                hook_style = HOOKS[index % len(HOOKS)]
                prompt = SCRIPT_PROMPT.format(
                    name=name,
                    category=category,
                    facts=facts_text,
                    segment_name=segment.name,
                    who=segment.who,
                    pain_point=segment.pain_point,
                    hook=hook_style,
                    market=market_clean,
                    language=LANGUAGES[language],
                )
                script_obj = await ask_gemini(prompt=prompt, schema=Script)
                return index, script_obj

            tasks = [
                asyncio.create_task(generate_single_script(i, s))
                for i, s in enumerate(segs.segments)
            ]

            try:
                for future in asyncio.as_completed(tasks):
                    idx, script_obj = await future
                    script_data = {
                        "event": "script",
                        "index": idx,
                        "script": script_obj.model_dump(),
                    }
                    yield f"data: {json.dumps(script_data)}\n\n"
            except Exception:
                for t in tasks:
                    if not t.done():
                        t.cancel()
                raise

            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        except Exception as e:
            detail = getattr(e, "detail", str(e))
            yield f"data: {json.dumps({'event': 'error', 'detail': detail})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Sprint 2: Granular Regeneration Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/regenerate/segment",
    response_model=Segment,
    tags=["Granular Regenerations"],
    summary="Regenerate a single customer segment distinct from all active segments",
)
async def regenerate_segment(
    payload: SegmentRegenerateRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
):
    """
    Generates a unique customer segment differing from all other active segments
    while maintaining the selected language (English or Bangla).
    """
    check_authorization(x_api_key)
    lang_block = get_language_block(payload.language)
    facts_text = format_facts_text(payload.facts)
    other_names = "\n".join(
        f'- Other active segment: "{name}"'
        for name in payload.existing_segment_names
        if name and name.strip()
    )

    prompt = REGENERATE_SEGMENT_PROMPT.format(
        name=payload.name,
        category=payload.category,
        market=payload.market,
        language_block=lang_block,
        facts=facts_text,
        current_segment_name=payload.current_segment.name,
        current_segment_who=payload.current_segment.who,
        current_segment_pain_point=payload.current_segment.pain_point,
        other_segment_names=other_names or "None",
    )
    return await ask_gemini(prompt=prompt, schema=Segment)


@app.post(
    "/regenerate/script",
    response_model=Script,
    tags=["Granular Regenerations"],
    summary="Rewrite an entire UGC script for a specific segment",
)
async def rewrite_script(
    payload: ScriptRewriteRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
):
    """
    Regenerates a complete script for a specific segment against active facts
    while strictly retaining the requested language and enforcing contiguous reasons.
    """
    check_authorization(x_api_key)
    lang_block = get_language_block(payload.language)
    facts_text = format_facts_text(payload.facts)
    hook_style = payload.hook_style or HOOKS[0]

    prompt = REWRITE_SCRIPT_PROMPT.format(
        name=payload.name,
        category=payload.category,
        market=payload.market,
        language_block=lang_block,
        facts=facts_text,
        segment_name=payload.segment.name,
        who=payload.segment.who,
        pain_point=payload.segment.pain_point,
        hook=hook_style,
    )
    return await ask_gemini(prompt=prompt, schema=Script)


@app.post(
    "/regenerate/reason-lines",
    response_model=ReasonLinesRewriteResponse,
    tags=["Granular Regenerations"],
    summary="Rewrite the contiguous line group cited by a marketing technique",
)
async def rewrite_reason_lines(
    payload: ReasonLinesRewriteRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
):
    """
    Rewrites the lines cited by a marketing technique while keeping surrounding
    script narrative context and preserving structural roles (hook/cta).
    """
    check_authorization(x_api_key)
    lang_block = get_language_block(payload.language)
    facts_text = format_facts_text(payload.facts)
    full_script_text = format_script_context(payload.full_script)
    target_lines = [l for l in payload.full_script if l.id in payload.target_line_ids]
    target_lines_text = format_script_context(target_lines)
    target_pos_str = ", ".join(str(i) for i in sorted(payload.target_line_ids))

    prompt = REWRITE_REASON_LINES_PROMPT.format(
        name=payload.name,
        market=payload.market,
        language_block=lang_block,
        facts=facts_text,
        segment_name=payload.segment.name,
        who=payload.segment.who,
        pain_point=payload.segment.pain_point,
        full_script=full_script_text,
        target_positions=target_pos_str,
        target_lines=target_lines_text,
        reason_title=payload.reason.title,
        reason_why=payload.reason.why,
    )
    return await ask_gemini(prompt=prompt, schema=ReasonLinesRewriteResponse)


@app.post(
    "/regenerate/line/rephrase",
    response_model=LineRephraseResponse,
    tags=["Granular Regenerations"],
    summary="Rephrase a single line in an alternative tone while preserving meaning",
)
async def rephrase_line(
    payload: LineRephraseRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
):
    """
    Rephrases a single sentence into a distinct tone (punchy, casual, authentic, direct)
    while preserving grammatical subject/object and language settings.
    """
    check_authorization(x_api_key)
    lang_block = get_language_block(payload.language)
    facts_text = format_facts_text(payload.facts)
    script_context_text = format_script_context(payload.script_context)
    avoid_str = format_avoid_tones(payload.avoid_tones)
    lang_name = LANGUAGES.get(payload.language, "English")

    prompt = REPHRASE_LINE_PROMPT.format(
        name=payload.name,
        market=payload.market,
        language_block=lang_block,
        language_name=lang_name,
        language_code=payload.language,
        facts=facts_text,
        segment_name=payload.segment.name,
        who=payload.segment.who,
        pain_point=payload.segment.pain_point,
        script_context=script_context_text,
        line_id=payload.line_id,
        current_text=payload.current_text,
        kind=payload.kind,
        avoid_tones=avoid_str,
    )
    return await ask_gemini(prompt=prompt, schema=LineRephraseResponse)


@app.post(
    "/regenerate/line/regenerate",
    response_model=LineRegenerateResponse,
    tags=["Granular Regenerations"],
    summary="Replace a single line with a completely new angle fitting the same position",
)
async def regenerate_line(
    payload: LineRegenerateRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
):
    """
    Replaces a single line with a fresh, distinct angle matching its structural role
    (hook, concept, cta) in the chosen language.
    """
    check_authorization(x_api_key)
    lang_block = get_language_block(payload.language)
    facts_text = format_facts_text(payload.facts)
    script_context_text = format_script_context(payload.script_context)
    lang_name = LANGUAGES.get(payload.language, "English")

    prompt = REGENERATE_LINE_PROMPT.format(
        name=payload.name,
        market=payload.market,
        language_block=lang_block,
        language_name=lang_name,
        language_code=payload.language,
        facts=facts_text,
        segment_name=payload.segment.name,
        who=payload.segment.who,
        pain_point=payload.segment.pain_point,
        script_context=script_context_text,
        line_id=payload.line_id,
        current_text=payload.current_text,
        kind=payload.kind,
    )
    return await ask_gemini(prompt=prompt, schema=LineRegenerateResponse)


@app.post(
    "/regenerate/section",
    tags=["Granular Regenerations"],
    summary="Regenerate customer segments and scripts progressively via SSE after facts updates",
)
async def regenerate_section(
    payload: SectionRegenerateRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
):
    """
    Progressive SSE pipeline that runs when product facts are updated:
    1. Preserves hand-edited segments where keep_segment is True.
    2. Generates new distinct segments for slots where keep_segment is False.
       -> Yields 'segments' event.
    3. In parallel, rewrites scripts for all 3 segments with updated facts.
       -> Yields 'script' event as each finishes.
    4. Yields 'done' event on completion or 'error' on failure.
    """
    check_authorization(x_api_key)
    facts_text = format_facts_text(payload.facts)
    lang_block = get_language_block(payload.language)

    async def event_generator():
        try:
            # 1. Determine segments for 3 slots
            final_segments: list[Segment | None] = [None, None, None]
            kept_names: list[str] = []

            # Populate kept segments first
            for slot in payload.slots:
                if slot.keep_segment and slot.segment:
                    if 0 <= slot.index < 3:
                        final_segments[slot.index] = slot.segment
                        kept_names.append(slot.segment.name)

            # Generate new segments for remaining slots
            for idx in range(3):
                if final_segments[idx] is None:
                    existing = kept_names + [s.name for s in final_segments if s]
                    other_names = "\n".join(f'- Other segment: "{n}"' for n in existing) or "None"
                    prompt = REGENERATE_SEGMENT_PROMPT.format(
                        name=payload.name,
                        category=payload.category,
                        market=payload.market,
                        language_block=lang_block,
                        facts=facts_text,
                        current_segment_name="Earlier Segment",
                        current_segment_who="Audience from earlier facts",
                        current_segment_pain_point="Outdated context",
                        other_segment_names=other_names,
                    )
                    seg = await ask_gemini(prompt=prompt, schema=Segment)
                    final_segments[idx] = seg

            resolved_segments = [s for s in final_segments if s is not None]

            # Emit Stage 1 finalized segments
            stage1_data = {
                "event": "segments",
                "facts": payload.facts,
                "segments": [s.model_dump() for s in resolved_segments],
            }
            yield f"data: {json.dumps(stage1_data)}\n\n"

            # 2. Parallel Script Generation across all 3 segments
            async def generate_single_script(index: int, segment: Segment) -> tuple[int, Script]:
                hook_style = HOOKS[index % len(HOOKS)]
                prompt = REWRITE_SCRIPT_PROMPT.format(
                    name=payload.name,
                    category=payload.category,
                    market=payload.market,
                    language_block=lang_block,
                    facts=facts_text,
                    segment_name=segment.name,
                    who=segment.who,
                    pain_point=segment.pain_point,
                    hook=hook_style,
                )
                script_obj = await ask_gemini(prompt=prompt, schema=Script)
                return index, script_obj

            tasks = [
                asyncio.create_task(generate_single_script(i, s))
                for i, s in enumerate(resolved_segments)
            ]

            try:
                for future in asyncio.as_completed(tasks):
                    idx, script_obj = await future
                    script_data = {
                        "event": "script",
                        "index": idx,
                        "script": script_obj.model_dump(),
                    }
                    yield f"data: {json.dumps(script_data)}\n\n"
            except Exception:
                for t in tasks:
                    if not t.done():
                        t.cancel()
                raise

            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        except Exception as e:
            detail = getattr(e, "detail", str(e))
            yield f"data: {json.dumps({'event': 'error', 'detail': detail})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
