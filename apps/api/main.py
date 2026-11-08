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
import os
from typing import Literal, Sequence, Any
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types

from schemas import GenerateResponse, Line, Reason, Script, Segment, Segments
from prompts import SEGMENT_PROMPT, SCRIPT_PROMPT

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
    # 1. API Key Authorization Check
    expected_api_key = os.environ.get("API_KEY")
    if not expected_api_key or x_api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad or missing API key. Provide a valid 'X-API-Key' header.",
        )

    # 2. Input Validation
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

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be 5 MB or smaller.",
        )

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
