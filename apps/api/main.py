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

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types
import httpx
from google.cloud import firestore

from audit import log_generation_task
from auth import (
    access_request_limiter,
    require_auth,
    send_lead_notification,
    verify_access_code_record,
)
from demo_products import find_demo_product, get_demo_products_catalog
from firebase import get_firestore_client
from rate_limiter import check_regeneration_rate_limit
from validation import (
    Issue,
    ask_validated,
    build_reason_lines_correction_prompt,
    validate_reason_lines_rewrite,
    validate_script,
)

from schemas import (
    AccessRequestCreate,
    AccessRequestResponse,
    DemoProduct,
    DemoProductsResponse,
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
    TokenUsage,
    VerifyAccessRequest,
    VerifyAccessResponse,
)
from usage import record_gemini_usage, start_token_tracking
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
    expose_headers=["X-Token-Usage", "Retry-After"],
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
    *,
    temperature: float | None = None,
    system_instruction: str | None = None,
    stage: str = "unspecified",
) -> Any:
    """
    Helper function to invoke Gemini on Vertex AI asynchronously with structured output.
    Returns the parsed Pydantic object corresponding to the provided schema.
    """
    client = get_genai_client()
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)

    config_kwargs: dict[str, Any] = {
        "response_mime_type": "application/json",
        "response_schema": schema,
    }
    if temperature is not None:
        config_kwargs["temperature"] = temperature
    if system_instruction is not None:
        config_kwargs["system_instruction"] = system_instruction

    for attempt in range(max_retries + 1):
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=[*parts, prompt],
                config=types.GenerateContentConfig(**config_kwargs),
            )
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                record_gemini_usage(response.usage_metadata, stage=stage)

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


async def run_stage1(
    name: str,
    category: str,
    description: str,
    market: str,
    parts: Sequence[Any] = (),
) -> Segments:
    """Executes Stage 1: multi-modal extraction of facts and segments."""
    segment_prompt = SEGMENT_PROMPT.format(
        name=name,
        category=category,
        description=description,
        market=market,
    )
    return await ask_gemini(
        prompt=segment_prompt,
        schema=Segments,
        parts=parts,
        stage="extract",
    )


async def run_stage2_single_script(
    index: int,
    segment: Segment,
    name: str,
    category: str,
    market: str,
    language: str,
    facts_text: str,
) -> Script:
    """Generates a single UGC script with deterministic in-code validation and single retry."""
    hook_style = HOOKS[index % len(HOOKS)]
    lang_name = LANGUAGES.get(language, language)
    prompt = SCRIPT_PROMPT.format(
        name=name,
        category=category,
        facts=facts_text,
        segment_name=segment.name,
        who=segment.who,
        pain_point=segment.pain_point,
        hook=hook_style,
        market=market,
        language=lang_name,
    )
    script_obj, _issues = await ask_validated(
        ask_gemini,
        prompt=prompt,
        schema=Script,
        stage="script",
        validate=lambda s: validate_script(s, language=language),
    )
    return script_obj


async def run_stage2(
    name: str,
    category: str,
    market: str,
    language: str,
    facts: list[str],
    segments: list[Segment],
) -> list[Script]:
    """Executes Stage 2: parallel generation of 3 scripts (one per segment)."""
    facts_text = "\n".join(f"- {fact}" for fact in facts)
    return await asyncio.gather(*[
        run_stage2_single_script(i, s, name, category, market, language, facts_text)
        for i, s in enumerate(segments)
    ])


def check_authorization(x_api_key: str | None) -> None:
    """Verifies that the provided X-API-Key matches the configured API_KEY."""
    expected_api_key = os.environ.get("API_KEY")
    if not expected_api_key or x_api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad or missing API key. Provide a valid 'X-API-Key' header.",
        )


def validate_market(market: str) -> str:
    """Validates market string length."""
    market_clean = market.strip()
    if not market_clean or len(market_clean) > 60:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Market must be between 1 and 60 characters.",
        )
    return market_clean


def validate_market_and_image(market: str, image: UploadFile) -> str:
    """Validates market string length and image media type."""
    market_clean = validate_market(market)

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


_demo_image_cache: dict[str, bytes] = {}


async def resolve_image_bytes(
    image: UploadFile | None,
    demo_product_id: str | None,
) -> tuple[bytes, str, str | None]:
    """
    Resolves image bytes, content-type, and demo_image_url from either an uploaded file
    or a selected demo product preset.
    """
    if demo_product_id and demo_product_id.strip():
        demo = await find_demo_product(demo_product_id.strip())
        if not demo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Demo product '{demo_product_id}' was not found.",
            )

        if demo.id in _demo_image_cache:
            return _demo_image_cache[demo.id], "image/jpeg", demo.image_url

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as http_client:
                img_res = await http_client.get(demo.image_url)
                if img_res.status_code == 200 and img_res.content:
                    _demo_image_cache[demo.id] = img_res.content
                    ct = img_res.headers.get("content-type", "image/jpeg")
                    return img_res.content, ct, demo.image_url
        except Exception as e:
            print(f"Warning: Failed to fetch demo image from remote CDN: {e}")

        # Minimal 1x1 valid JPEG fallback bytes
        placeholder_jpeg = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00"
            b"\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19"
            b"\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9="
            b"82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00"
            b"\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04"
            b"\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
        )
        return placeholder_jpeg, "image/jpeg", demo.image_url

    if not image or not image.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either an image file or a valid demo_product_id must be provided.",
        )

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{image.content_type}'. Use JPEG, PNG, or WebP.",
        )

    image_bytes = await read_and_validate_image_bytes(image)
    return image_bytes, image.content_type, None


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


# ---------------------------------------------------------------------------
# Sprint 3: Authentication & Demo Products Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/auth/verify",
    response_model=VerifyAccessResponse,
    tags=["Authentication"],
    summary="Verify demo access code and retrieve user usage statistics",
)
async def verify_access(payload: VerifyAccessRequest):
    record = await verify_access_code_record(payload.code)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access code. Please check your code or request access.",
        )
    return VerifyAccessResponse(
        valid=True,
        owner_name=record.get("owner_name", ""),
        company=record.get("company", ""),
        total_tokens=record.get("total_tokens", 0),
        total_input_tokens=record.get("total_input_tokens", 0),
        total_output_tokens=record.get("total_output_tokens", 0),
    )


@app.post(
    "/auth/request-access",
    response_model=AccessRequestResponse,
    tags=["Authentication"],
    summary="Submit a lead request for demo access",
)
async def request_access(
    payload: AccessRequestCreate,
    request: Request,
    background_tasks: BackgroundTasks,
):
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = access_request_limiter.is_allowed(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many access requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        db = get_firestore_client()
        await db.collection("access_requests").add({
            "name": payload.name.strip(),
            "phone": payload.phone.strip(),
            "company": payload.company.strip(),
            "status": "pending",
            "created_at": firestore.SERVER_TIMESTAMP,
            "ip": client_ip,
        })
    except Exception as e:
        print(f"Warning: Failed to save access request in Firestore: {e}")

    background_tasks.add_task(
        send_lead_notification,
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        company=payload.company.strip(),
    )

    return AccessRequestResponse(
        success=True,
        message="Access request received. We will contact you with your access code.",
    )


@app.get(
    "/demo-products",
    response_model=DemoProductsResponse,
    tags=["System"],
    summary="Retrieve curated preset demo products",
)
async def list_demo_products():
    products = await get_demo_products_catalog()
    return DemoProductsResponse(products=products)


# ---------------------------------------------------------------------------
# Script Generation Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/generate",
    response_model=GenerateResponse,
    tags=["Script Generation"],
    summary="Generate customer segments and 3 UGC scripts from product details and image",
)
async def generate(
    response: Response,
    background_tasks: BackgroundTasks,
    name: str = Form(..., description="Product name"),
    description: str = Form(..., description="Detailed product description"),
    category: str = Form(..., description="Product category"),
    market: str = Form(..., description="Target market country or region (e.g., 'Bangladesh')"),
    language: Literal["en", "bn"] = Form(..., description="Desired script language: 'en' for English or 'bn' for Bangla"),
    image: UploadFile | None = File(None, description="Product image file (JPEG, PNG, or WebP, max 5 MB)"),
    demo_product_id: str | None = Form(None, description="Preset demo product ID (if not uploading an image)"),
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
    x_access_code: str | None = Header(None, alias="X-Access-Code", description="Demo access code"),
    auth: dict[str, Any] = Depends(require_auth),
):
    """
    Pipeline:
    1. Authenticate request using X-Access-Code or X-API-Key header.
    2. Validate input constraints (market length, image or demo product).
    3. Stage 1: Send product image + details to Gemini to extract verifiable facts & 3 segments.
    4. Stage 2: In parallel, generate 3 UGC scripts customized for each segment with assigned hook styles.
    5. Return unified facts, segments, and scripts with X-Token-Usage header.
    6. Asynchronously archive image and audit log to Firestore.
    """
    acc = start_token_tracking()
    market_clean = validate_market(market)
    image_bytes, content_type, demo_img_url = await resolve_image_bytes(image, demo_product_id)

    # Create image part for the multi-modal call
    img_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)

    # 3. Stage 1: Facts and Segments Extraction
    segs: Segments = await run_stage1(
        name=name,
        category=category,
        description=description,
        market=market_clean,
        parts=[img_part],
    )

    # 4. Stage 2: Parallel Script Generation (One per Segment)
    scripts: list[Script] = await run_stage2(
        name=name,
        category=category,
        market=market_clean,
        language=language,
        facts=segs.product_facts,
        segments=segs.segments,
    )

    usage = acc.to_dict()
    response.headers["X-Token-Usage"] = json.dumps(usage)

    # 5. Background audit log & image archival
    background_tasks.add_task(
        log_generation_task,
        access_code=auth.get("access_code", "ANONYMOUS"),
        endpoint="/generate",
        product_meta={
            "name": name,
            "category": category,
            "market": market_clean,
            "language": language,
            "is_demo_product": bool(demo_product_id),
        },
        image_bytes=image_bytes if not demo_img_url else None,
        image_content_type=content_type,
        demo_image_url=demo_img_url,
        request_payload={"name": name, "category": category, "market": market_clean, "language": language},
        response_payload={
            "facts": segs.product_facts,
            "segments": [s.model_dump() for s in segs.segments],
            "scripts": [s.model_dump() for s in scripts],
        },
        usage=usage,
    )

    # 6. Build and Return Final Unified Response
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
    background_tasks: BackgroundTasks,
    name: str = Form(..., description="Product name"),
    description: str = Form(..., description="Detailed product description"),
    category: str = Form(..., description="Product category"),
    market: str = Form(..., description="Target market country or region (e.g., 'Bangladesh')"),
    language: Literal["en", "bn"] = Form(..., description="Desired script language: 'en' for English or 'bn' for Bangla"),
    image: UploadFile | None = File(None, description="Product image file (JPEG, PNG, or WebP, max 5 MB)"),
    demo_product_id: str | None = Form(None, description="Preset demo product ID (if not uploading an image)"),
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
    x_access_code: str | None = Header(None, alias="X-Access-Code", description="Demo access code"),
    auth: dict[str, Any] = Depends(require_auth),
):
    """
    Progressive SSE Pipeline:
    1. Authenticate request using X-Access-Code or X-API-Key header.
    2. Validate input constraints (market length, image or demo product).
    3. Stage 1: Send product image + details to Gemini to extract verifiable facts & 3 segments.
       -> Yields 'segments' event immediately.
    4. Stage 2: In parallel, generate 3 UGC scripts customized for each segment.
       -> Yields each 'script' event as soon as its generation completes.
    5. Yields 'done' event with usage breakdown on completion, or 'error' event on failure.
    6. Asynchronously logs telemetry and token usage in Firestore.
    """
    market_clean = validate_market(market)
    image_bytes, content_type, demo_img_url = await resolve_image_bytes(image, demo_product_id)
    img_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)

    async def event_generator():
        acc = start_token_tracking()
        collected_segments: list[dict[str, Any]] = []
        collected_scripts: list[dict[str, Any]] = []
        try:
            # 1. Stage 1: Facts and Segments Extraction
            segs: Segments = await run_stage1(
                name=name,
                category=category,
                description=description,
                market=market_clean,
                parts=[img_part],
            )
            collected_segments = [s.model_dump() for s in segs.segments]

            # Emit Stage 1 facts and segments
            stage1_data = {
                "event": "segments",
                "facts": segs.product_facts,
                "segments": collected_segments,
            }
            yield f"data: {json.dumps(stage1_data)}\n\n"

            # 2. Stage 2: Parallel Script Generation (One per Segment)
            facts_text = "\n".join(f"- {fact}" for fact in segs.product_facts)

            async def generate_single_script(index: int, segment: Segment) -> tuple[int, Script]:
                script_obj = await run_stage2_single_script(
                    index=index,
                    segment=segment,
                    name=name,
                    category=category,
                    market=market_clean,
                    language=language,
                    facts_text=facts_text,
                )
                return index, script_obj

            tasks = [
                asyncio.create_task(generate_single_script(i, s))
                for i, s in enumerate(segs.segments)
            ]

            try:
                for future in asyncio.as_completed(tasks):
                    idx, script_obj = await future
                    dumped_script = script_obj.model_dump()
                    collected_scripts.append(dumped_script)
                    script_data = {
                        "event": "script",
                        "index": idx,
                        "script": dumped_script,
                    }
                    yield f"data: {json.dumps(script_data)}\n\n"
            except Exception:
                for t in tasks:
                    if not t.done():
                        t.cancel()
                raise

            usage = acc.to_dict()
            yield f"data: {json.dumps({'event': 'done', 'usage': usage})}\n\n"

            # Background audit logging
            background_tasks.add_task(
                log_generation_task,
                access_code=auth.get("access_code", "ANONYMOUS"),
                endpoint="/generate-stream",
                product_meta={
                    "name": name,
                    "category": category,
                    "market": market_clean,
                    "language": language,
                    "is_demo_product": bool(demo_product_id),
                },
                image_bytes=image_bytes if not demo_img_url else None,
                image_content_type=content_type,
                demo_image_url=demo_img_url,
                request_payload={"name": name, "category": category, "market": market_clean, "language": language},
                response_payload={
                    "facts": segs.product_facts,
                    "segments": collected_segments,
                    "scripts": collected_scripts,
                },
                usage=usage,
            )

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
# Sprint 2 & 3: Granular Regeneration Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/regenerate/segment",
    response_model=Segment,
    tags=["Granular Regenerations"],
    summary="Regenerate a single customer segment distinct from all active segments",
    dependencies=[Depends(check_regeneration_rate_limit)],
)
async def regenerate_segment(
    payload: SegmentRegenerateRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
    x_access_code: str | None = Header(None, alias="X-Access-Code", description="Demo access code"),
    auth: dict[str, Any] = Depends(require_auth),
):
    """
    Generates a unique customer segment differing from all other active segments
    while maintaining the selected language (English or Bangla).
    """
    acc = start_token_tracking()
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
    result = await ask_gemini(prompt=prompt, schema=Segment, stage="regenerate_segment")
    usage = acc.to_dict()
    response.headers["X-Token-Usage"] = json.dumps(usage)

    background_tasks.add_task(
        log_generation_task,
        access_code=auth.get("access_code", "ANONYMOUS"),
        endpoint="/regenerate/segment",
        product_meta={"name": payload.name, "category": payload.category, "market": payload.market, "language": payload.language},
        request_payload=payload.model_dump(),
        response_payload=result.model_dump(),
        usage=usage,
    )
    return result


@app.post(
    "/regenerate/script",
    response_model=Script,
    tags=["Granular Regenerations"],
    summary="Rewrite an entire UGC script for a specific segment",
    dependencies=[Depends(check_regeneration_rate_limit)],
)
async def rewrite_script(
    payload: ScriptRewriteRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
    x_access_code: str | None = Header(None, alias="X-Access-Code", description="Demo access code"),
    auth: dict[str, Any] = Depends(require_auth),
):
    """
    Regenerates a complete script for a specific segment against active facts
    while strictly retaining the requested language and enforcing contiguous reasons.
    """
    acc = start_token_tracking()
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
    result, _issues = await ask_validated(
        ask_gemini,
        prompt=prompt,
        schema=Script,
        stage="rewrite_script",
        validate=lambda s: validate_script(s, language=payload.language),
    )
    usage = acc.to_dict()
    response.headers["X-Token-Usage"] = json.dumps(usage)

    background_tasks.add_task(
        log_generation_task,
        access_code=auth.get("access_code", "ANONYMOUS"),
        endpoint="/regenerate/script",
        product_meta={"name": payload.name, "category": payload.category, "market": payload.market, "language": payload.language},
        request_payload=payload.model_dump(),
        response_payload=result.model_dump(),
        usage=usage,
    )
    return result


@app.post(
    "/regenerate/reason-lines",
    response_model=ReasonLinesRewriteResponse,
    tags=["Granular Regenerations"],
    summary="Rewrite the contiguous line group cited by a marketing technique",
    dependencies=[Depends(check_regeneration_rate_limit)],
)
async def rewrite_reason_lines(
    payload: ReasonLinesRewriteRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
    x_access_code: str | None = Header(None, alias="X-Access-Code", description="Demo access code"),
    auth: dict[str, Any] = Depends(require_auth),
):
    """
    Rewrites the lines cited by a marketing technique while keeping surrounding
    script narrative context and preserving structural roles (hook/cta).
    """
    acc = start_token_tracking()
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
    result, _issues = await ask_validated(
        ask_gemini,
        prompt=prompt,
        schema=ReasonLinesRewriteResponse,
        stage="rewrite_reason_lines",
        validate=lambda r: validate_reason_lines_rewrite(
            r,
            target_line_ids=payload.target_line_ids,
            total_script_lines=len(payload.full_script),
            language=payload.language,
        ),
        build_correction=build_reason_lines_correction_prompt,
    )
    usage = acc.to_dict()
    response.headers["X-Token-Usage"] = json.dumps(usage)

    background_tasks.add_task(
        log_generation_task,
        access_code=auth.get("access_code", "ANONYMOUS"),
        endpoint="/regenerate/reason-lines",
        product_meta={"name": payload.name, "market": payload.market, "language": payload.language},
        request_payload=payload.model_dump(),
        response_payload=result.model_dump(),
        usage=usage,
    )
    return result


@app.post(
    "/regenerate/line/rephrase",
    response_model=LineRephraseResponse,
    tags=["Granular Regenerations"],
    summary="Rephrase a single line in an alternative tone while preserving meaning",
    dependencies=[Depends(check_regeneration_rate_limit)],
)
async def rephrase_line(
    payload: LineRephraseRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
    x_access_code: str | None = Header(None, alias="X-Access-Code", description="Demo access code"),
    auth: dict[str, Any] = Depends(require_auth),
):
    """
    Rephrases a single sentence into a distinct tone (punchy, casual, authentic, direct)
    while preserving grammatical subject/object and language settings.
    """
    acc = start_token_tracking()
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
    result = await ask_gemini(prompt=prompt, schema=LineRephraseResponse, stage="rephrase_line")
    usage = acc.to_dict()
    response.headers["X-Token-Usage"] = json.dumps(usage)

    background_tasks.add_task(
        log_generation_task,
        access_code=auth.get("access_code", "ANONYMOUS"),
        endpoint="/regenerate/line/rephrase",
        product_meta={"name": payload.name, "market": payload.market, "language": payload.language},
        request_payload=payload.model_dump(),
        response_payload=result.model_dump(),
        usage=usage,
    )
    return result


@app.post(
    "/regenerate/line/regenerate",
    response_model=LineRegenerateResponse,
    tags=["Granular Regenerations"],
    summary="Replace a single line with a completely new angle fitting the same position",
    dependencies=[Depends(check_regeneration_rate_limit)],
)
async def regenerate_line(
    payload: LineRegenerateRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
    x_access_code: str | None = Header(None, alias="X-Access-Code", description="Demo access code"),
    auth: dict[str, Any] = Depends(require_auth),
):
    """
    Replaces a single line with a fresh, distinct angle matching its structural role
    (hook, concept, cta) in the chosen language.
    """
    acc = start_token_tracking()
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
    result = await ask_gemini(prompt=prompt, schema=LineRegenerateResponse, stage="regenerate_line")
    usage = acc.to_dict()
    response.headers["X-Token-Usage"] = json.dumps(usage)

    background_tasks.add_task(
        log_generation_task,
        access_code=auth.get("access_code", "ANONYMOUS"),
        endpoint="/regenerate/line/regenerate",
        product_meta={"name": payload.name, "market": payload.market, "language": payload.language},
        request_payload=payload.model_dump(),
        response_payload=result.model_dump(),
        usage=usage,
    )
    return result


@app.post(
    "/regenerate/section",
    tags=["Granular Regenerations"],
    summary="Regenerate customer segments and scripts progressively via SSE after facts updates",
    dependencies=[Depends(check_regeneration_rate_limit)],
)
async def regenerate_section(
    payload: SectionRegenerateRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(None, alias="X-API-Key", description="API Key for request authorization"),
    x_access_code: str | None = Header(None, alias="X-Access-Code", description="Demo access code"),
    auth: dict[str, Any] = Depends(require_auth),
):
    """
    Progressive SSE pipeline that runs when product facts are updated:
    1. Preserves hand-edited segments where keep_segment is True.
    2. Generates new distinct segments for slots where keep_segment is False.
       -> Yields 'segments' event.
    3. In parallel, rewrites scripts for all 3 segments with updated facts.
       -> Yields 'script' event as each finishes.
    4. Yields 'done' event with usage breakdown on completion or 'error' on failure.
    """
    facts_text = format_facts_text(payload.facts)
    lang_block = get_language_block(payload.language)

    async def event_generator():
        acc = start_token_tracking()
        collected_segments: list[dict[str, Any]] = []
        collected_scripts: list[dict[str, Any]] = []
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
                    seg = await ask_gemini(prompt=prompt, schema=Segment, stage="regenerate_segment")
                    final_segments[idx] = seg

            resolved_segments = [s for s in final_segments if s is not None]
            collected_segments = [s.model_dump() for s in resolved_segments]

            # Emit Stage 1 finalized segments
            stage1_data = {
                "event": "segments",
                "facts": payload.facts,
                "segments": collected_segments,
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
                script_obj, _issues = await ask_validated(
                    ask_gemini,
                    prompt=prompt,
                    schema=Script,
                    stage="rewrite_script",
                    validate=lambda s: validate_script(s, language=payload.language),
                )
                return index, script_obj

            tasks = [
                asyncio.create_task(generate_single_script(i, s))
                for i, s in enumerate(resolved_segments)
            ]

            try:
                for future in asyncio.as_completed(tasks):
                    idx, script_obj = await future
                    dumped_script = script_obj.model_dump()
                    collected_scripts.append(dumped_script)
                    script_data = {
                        "event": "script",
                        "index": idx,
                        "script": dumped_script,
                    }
                    yield f"data: {json.dumps(script_data)}\n\n"
            except Exception:
                for t in tasks:
                    if not t.done():
                        t.cancel()
                raise

            usage = acc.to_dict()
            yield f"data: {json.dumps({'event': 'done', 'usage': usage})}\n\n"

            # Background audit logging
            background_tasks.add_task(
                log_generation_task,
                access_code=auth.get("access_code", "ANONYMOUS"),
                endpoint="/regenerate/section",
                product_meta={
                    "name": payload.name,
                    "category": payload.category,
                    "market": payload.market,
                    "language": payload.language,
                },
                request_payload=payload.model_dump(),
                response_payload={
                    "facts": payload.facts,
                    "segments": collected_segments,
                    "scripts": collected_scripts,
                },
                usage=usage,
            )

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
# Static File & SPA Serving (Production)
# ---------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).resolve().parent / "static"
if not STATIC_DIR.exists():
    alt = Path("/app/static")
    if alt.exists():
        STATIC_DIR = alt
if not STATIC_DIR.exists():
    alt = Path(__file__).resolve().parent.parent / "web" / "dist"
    if alt.exists():
        STATIC_DIR = alt

if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not Found")

