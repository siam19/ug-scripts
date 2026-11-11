# Backend Architectural Context & Implementation Guide for Sprint 4 Ideas

> **Document Location**: `docs/sprints/4. Pipeline optimization /ideas.context.md`  
> **Target Audience**: AI Assistants, System Architects, and Backend Engineers collaborating on `ideas.md`  
> **Prerequisites**: Assumes reader is familiar with `project-context.md`  
> **Scope**: Concrete code mechanisms, Pydantic schemas, LLM invocation internals, and data flows necessary to implement the proposals in `ideas.md`  
> **Last Updated**: 2026-11-11

---

## 1. Executive Summary & Purpose

This document provides the exact code-level context required to evaluate, design, and implement the quality enhancements outlined in [`ideas.md`](ideas.md). While `project-context.md` provides a broad architectural overview, this document drills directly into the **specific functions, schemas, prompt mechanics, and concurrency loops** that each idea in `ideas.md` will touch.

---

## 2. LLM Invocation Engine (`ask_gemini`)

All generative AI calls throughout the backend route through a single asynchronous helper function located in [`apps/api/main.py`](../../apps/api/main.py#L157-L195).

### Current Implementation
```python
# apps/api/main.py
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
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                record_gemini_usage(response.usage_metadata)

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
```

### Critical Context for Sprint 4 Ideas
1. **Schema Enforcement via Pydantic**: When `response_schema=schema` is passed, the `google-genai` SDK converts the Pydantic model into an OpenAPI-compatible JSON schema. Gemini 3.5 Flash strictly constrains output tokens to valid JSON conforming to this schema. The SDK automatically hydrates `response.parsed` directly into an instance of `schema`.
2. **Current Limitations to Address**:
   - `ask_gemini` currently does **not** accept a `temperature` parameter. It relies on the model default (~1.0). Adding `temperature: float | None = None` to `types.GenerateContentConfig` is required for Idea 4.7 (0.2 for Stage 1 extraction, 0.7 for creative writing).
   - `ask_gemini` currently does **not** take a `system_instruction`. Everything is packed into `contents=[*parts, prompt]`. Moving static role definitions into `types.GenerateContentConfig(system_instruction=...)` enables Vertex AI Context Caching.
   - `ask_gemini` currently returns as soon as JSON parses. It contains **no business-rule validation** (word count, hook duration, Bengali script verification).

---

## 3. Idea 1: Facts vs. Angles & Two-Tier Grounding

### Current Pipeline Reality
Currently, Stage 1 extraction (`SEGMENT_PROMPT` in [`apps/api/prompts.py`](../../apps/api/prompts.py#L41-L61)) outputs a flat model:
```python
# apps/api/schemas.py (Current)
class Segments(BaseModel):
    product_facts: list[str] = Field(
        ...,
        description="5 to 8 concrete, verifiable facts drawn ONLY from the product description and image"
    )
    segments: list[Segment] = Field(
        ...,
        description="Exactly 3 distinct customer segments that differ in motivation and context"
    )
```

In Stage 2, `main.py` formats these facts into a single flat bulleted list:
```python
# apps/api/main.py:571
facts_text = "\n".join(f"- {fact}" for fact in segs.product_facts)
```
Every script sees the exact same flat list of facts, causing the model to either dump random packaging specs or ignore emotional hooks.

### Implementation Blueprint for Two-Tier Grounding

#### 1. Schema Expansion in `apps/api/schemas.py`
```python
from typing import Literal
from pydantic import BaseModel, Field

class Fact(BaseModel):
    text: str = Field(..., description="Concrete, verifiable packaging or description claim")
    value: Literal['core', 'visual', 'trivia'] = Field(
        ..., 
        description="'core' = active ingredients/guarantees; 'visual' = color/cues; 'trivia' = packaging text"
    )

class Angle(BaseModel):
    type: Literal['benefit', 'moment', 'objection', 'demo', 'emotion', 'context'] = Field(
        ...,
        description="Angle category providing creative narrative framing"
    )
    text: str = Field(..., description="The situation, consequence, sensory demo, or objection framing")
    based_on: list[int] = Field(
        default_factory=list,
        description="1-based indices into product_facts that ground this angle. Empty only for pure audience context."
    )

class Segment(BaseModel):
    name: str
    who: str
    pain_point: str
    platforms: list[str]
    target_angle_indices: list[int] = Field(
        default_factory=list,
        description="1-based indices of angles specifically relevant to this segment's pain point"
    )

class Segments(BaseModel):
    product_facts: list[Fact]
    angles: list[Angle]
    segments: list[Segment]
```

#### 2. Segment Gating Check
In `apps/api/main.py`, before launching parallel script tasks, add a deterministic gating check:
```python
for segment in segs.segments:
    if not segment.target_angle_indices:
        # Segment is ungrounded: retry Stage 1 or assign closest angles
        ...
```

#### 3. Targeted Stage 2 Context Injection
Instead of passing all facts to all scripts, filter the prompt context per segment:
```python
# In generate_single_script(index, segment):
relevant_angles = [segs.angles[i - 1] for i in segment.target_angle_indices if 1 <= i <= len(segs.angles)]
grounded_fact_indices = {idx for a in relevant_angles for idx in a.based_on}
relevant_facts = [segs.product_facts[i - 1] for i in grounded_fact_indices if 1 <= i <= len(segs.product_facts)]

# Pass only relevant_facts and relevant_angles to SCRIPT_PROMPT
```

---

## 4. Idea 2: Format Setting (UGC vs. 30s Commercial Ad)

### The Existing Injected Block Pattern
The codebase already uses dynamic string template injection for language rules (`LANGUAGE_BLOCK` in [`apps/api/prompts.py`](../../apps/api/prompts.py#L23-L34)).

We can mirror this proven pattern with a `FORMAT_SPEC` dictionary:

```python
# apps/api/prompts.py

FORMAT_SPECS: dict[str, dict[str, Any]] = {
    "ugc": {
        "name": "UGC (Creator Phone-Shot)",
        "voice": "First-person creator on camera ('I tried this', 'look at my skin'). Imperfect, casual, peer-to-peer recommendation.",
        "length": "20-35 seconds spoken (about 60-90 words).",
        "structure": "Hook (0-3s scroll-stopper), Concept (body & social proof), CTA (direct call to action).",
        "hook_styles": ["Curiosity Question", "Problem Callout", "Demo / Before-After"],
        "banned_phrases": ["my secret is", "game changer", "click the link below", "upgrade your", "look no further"],
        "code_mixing": "Natural Bengali-English code mixing allowed for spoken dialogue (e.g., 'স্কিন কেয়ার', 'অর্ডার').",
        "few_shot_examples": "...",
    },
    "commercial_30s": {
        "name": "30-Second Commercial Ad",
        "voice": "Polished brand voice. Third-person voiceover (VO) or narrator allowed. Dynamic, cinematic delivery.",
        "length": "Strictly 28-32 seconds spoken (about 65-80 words).",
        "structure": "Cold Open / Visual Hook (0-5s), Problem Exposition (5-12s), Product as Hero (12-24s), Brand Tagline & End Card (24-30s).",
        "hook_styles": ["Cold-Open Scene", "Slice of Life Problem", "Product-as-Hero Cinematic Reveal"],
        "banned_phrases": ["hey guys", "TikTok made me buy it", "smash that like button"],
        "code_mixing": "Formal standard Bengali. Avoid colloquial slang.",
        "few_shot_examples": "...",
    }
}
```

### Schema Changes on `Line`
To support 30s commercial ads without breaking UGC rendering, make `speaker` and `visual` optional in [`apps/api/schemas.py`](../../apps/api/schemas.py#L49-L65):

```python
class Line(BaseModel):
    id: int = Field(..., description="1-based sequential line index")
    kind: Literal['hook', 'concept', 'cta'] = Field(..., description="Role of this beat in video structure")
    text: str = Field(..., description="Spoken dialogue or voiceover narration")
    speaker: str | None = Field(
        default=None,
        description="Optional: 'Creator', 'Voiceover (VO)', 'Customer 1', 'On-Screen Text'"
    )
    visual: str | None = Field(
        default=None,
        description="Optional: On-screen action direction or shot cue (e.g., '[Close-up: Dropper on cheek]')"
    )
```

### API Endpoint Parameterization
In [`apps/api/main.py`](../../apps/api/main.py#L510-L540):
- Add `format: Literal['ugc', 'commercial_30s'] = Form('ugc')` to `/generate` and `/generate-stream`.
- Add `format: Literal['ugc', 'commercial_30s'] = 'ugc'` to all regeneration payloads (`ScriptRewriteRequest`, `SectionRegenerateRequest`).

---

## 5. Idea 3: Pipeline Refinements (Validation, Retries & Planning)

### 1. In-Code Script Validation & Single Retry
Currently, word count and duration rules live **only** in prompt text, leading to frequent length drift.

Here is the exact implementation structure for an in-code validator in `apps/api/main.py`:

```python
# apps/api/validation.py (New helper module)
import re

class ScriptValidationError(Exception):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__(", ".join(issues))

def validate_script(script: Script, format_type: str = "ugc", language: str = "en") -> None:
    issues: list[str] = []
    
    # 1. Total word count & pacing check
    total_words = sum(len(line.text.split()) for line in script.lines)
    min_words, max_words = (60, 90) if format_type == "ugc" else (65, 80)
    if not (min_words <= total_words <= max_words):
        issues.append(f"Total script word count is {total_words} words (expected between {min_words} and {max_words}).")

    # 2. Hook length (first 3 seconds ~ 7-9 words)
    hook_lines = [l for l in script.lines if l.kind == "hook"]
    if not hook_lines:
        issues.append("Missing 'hook' line at the start of the script.")
    elif format_type == "ugc":
        hook_words = sum(len(l.text.split()) for l in hook_lines)
        if hook_words > 10:
            issues.append(f"Hook exceeds 3-second window: contains {hook_words} words (must be 8 words or fewer).")

    # 3. Final line must be CTA
    if script.lines and script.lines[-1].kind != "cta":
        issues.append(f"Final line is '{script.lines[-1].kind}', but must be 'cta'.")

    # 4. Reason line citations must exist and be contiguous
    valid_ids = {l.id for l in script.lines}
    for r in script.reasons:
        for lid in r.line_ids:
            if lid not in valid_ids:
                issues.append(f"Reason '{r.title}' cites nonexistent line ID {lid}.")
        # Contiguous check
        sorted_ids = sorted(r.line_ids)
        if sorted_ids and sorted_ids != list(range(sorted_ids[0], sorted_ids[-1] + 1)):
            issues.append(f"Reason '{r.title}' cites non-contiguous line IDs {sorted_ids}.")

    # 5. Language Unicode Check (Bengali)
    if language == "bn":
        bengali_chars = len(re.findall(r'[\u0980-\u09FF]', " ".join(l.text for l in script.lines)))
        total_chars = len("".join(l.text.split()))
        if total_chars > 0 and (bengali_chars / total_chars) < 0.65:
            issues.append("Script contains insufficient Bengali script (বাংলা). Dialogue must be in Bengali script.")

    if issues:
        raise ScriptValidationError(issues)
```

#### Integration with Automatic Retry in `generate_single_script`
```python
# apps/api/main.py
async def generate_single_script_with_retry(index: int, segment: Segment) -> tuple[int, Script]:
    # Attempt 1: Standard generation
    script_obj = await ask_gemini(prompt=initial_prompt, schema=Script, temperature=0.7)
    
    try:
        validate_script(script_obj, format_type=format_type, language=language)
        return index, script_obj
    except ScriptValidationError as val_err:
        # Attempt 2: Target correction prompt
        correction_prompt = f"""{initial_prompt}

CRITICAL CORRECTION REQUIRED:
Your previous output violated these rules:
{format_issues(val_err.issues)}

Regenerate the script fixing all violations above.
"""
        script_obj_retry = await ask_gemini(prompt=correction_prompt, schema=Script, temperature=0.3)
        return index, script_obj_retry
```

---

### 2. Stage 3 Critique-and-Rewrite Architecture
`ideas.md` Section 4 proposes an optional critique-and-rewrite pass. In an SSE streaming pipeline, there are two execution patterns:

1. **Gated Emission (Quality First)**:
   - `generate_single_script` runs Stage 2 -> runs Critique -> if score < 7.5, runs Rewrite -> emits `event: script`.
   - *Impact*: Increases time-to-first-script from ~5s to ~8s, but every emitted script is guaranteed high quality.
2. **Progressive Optimistic Emit (Speed First)**:
   - Stage 2 emits initial draft immediately: `{"event": "script", "index": idx, "script": draft}`.
   - Critique runs in the background. If rewritten, emits: `{"event": "script_upgrade", "index": idx, "script": upgraded_script}`.
   - *Impact*: Frontend keeps ~4s TTFC while seamlessly upgrading text in place.

---

## 6. Idea 4: Eval Set & Ranking in Firestore

### How Audit Logging Operates Today
In [`apps/api/audit.py`](../../apps/api/audit.py), every generation run writes a document to Firestore collection `generation_logs`:

```python
# apps/api/audit.py:62-72
log_ref = db.collection("generation_logs").document(log_id)
await log_ref.set({
    "log_id": log_id,
    "access_code": access_code,
    "endpoint": endpoint,
    "product_meta": product_meta,
    "image_storage_uri": image_uri,
    "request_payload": request_payload or {},
    "response_payload": response_payload or {},
    "usage": usage_data,
    "created_at": firestore.SERVER_TIMESTAMP,
})
```

### Implementing User Ratings / Feedback
To collect ratings from demo users (turning production usage into an eval dataset):

#### 1. Expose `log_id` to the Client
In `main.py`, include `log_id` in the final SSE `done` event:
```python
yield f"data: {json.dumps({'event': 'done', 'log_id': log_id, 'usage': usage})}\n\n"
```

#### 2. Create Rating Endpoint in `apps/api/main.py`
```python
class ScriptFeedbackRequest(BaseModel):
    log_id: str
    script_index: int
    rating: int = Field(..., ge=1, le=5, description="1 to 5 star rating or thumbs up/down")
    tags: list[str] = Field(default_factory=list, description="e.g. ['bland', 'great_hook', 'unrealistic']")
    comment: str | None = None

@app.post("/audit/feedback", tags=["Telemetry"])
async def submit_script_feedback(
    payload: ScriptFeedbackRequest,
    auth: dict[str, Any] = Depends(require_auth),
):
    db = get_firestore_client()
    log_ref = db.collection("generation_logs").document(payload.log_id)
    feedback_doc = {
        f"feedback_script_{payload.script_index}": {
            "rating": payload.rating,
            "tags": payload.tags,
            "comment": payload.comment,
            "submitted_at": firestore.SERVER_TIMESTAMP,
        }
    }
    await log_ref.set(feedback_doc, merge=True)
    return {"status": "recorded"}
```

---

## 7. Idea 5: Scenes Feature (Visual Video Directing)

`ideas.md` Section 6 proposes adding visual, action-based scene breakdowns alongside each script.

### 1. New Pydantic Schema (`apps/api/schemas.py`)
```python
class Scene(BaseModel):
    scene_number: int = Field(..., description="1-based sequential scene order")
    line_ids: list[int] = Field(..., description="Script lines spoken during this visual scene")
    setting: str = Field(..., description="Location, time of day, environment (e.g. 'Bright modern bathroom, morning sunlight')")
    subject_wardrobe: str = Field(..., description="Creator description, wardrobe, hair, look")
    action: str = Field(..., description="Verb-driven physical action (e.g. 'Unscrews dropper, places 2 drops directly onto cheek')")
    props: str = Field(..., description="Props in frame, packaging placement, background items")
    camera: str = Field(..., description="Framing and camera movement (e.g. 'Macro close-up, slight handheld drift')")
    on_screen_text: str | None = Field(default=None, description="Optional text overlay or caption sticker")
    ai_visual_prompt: str = Field(
        ...,
        description="Self-contained image/video generator prompt with zero relative references, ready for Midjourney/Runway"
    )

class ScriptScenes(BaseModel):
    look_bible: str = Field(
        ...,
        description="Short consistency summary (character description, lighting mood, color palette) governing all scenes"
    )
    scenes: list[Scene]
```

### 2. New Endpoint Design
```python
# apps/api/main.py
@app.post(
    "/generate/scenes",
    response_model=ScriptScenes,
    tags=["Script Generation"],
    dependencies=[Depends(check_regeneration_rate_limit)],
)
async def generate_scenes_for_script(
    payload: GenerateScenesRequest,
    auth: dict[str, Any] = Depends(require_auth),
):
    """
    Generates detailed action-based scene directions and standalone AI image/video
    generation prompts for a completed script.
    """
    ...
```

---

## 8. TypeScript Contract Workflow (`packages/api-types`)

Whenever schemas change in `apps/api/schemas.py`, the changes must be compiled into TypeScript types so the frontend and API client remain in strict sync.

### Type Generation Mechanism
```
apps/api/schemas.py (Python Pydantic Models)
        │
        ▼ FastAPI Reflection
apps/api/openapi.json (OpenAPI 3.1 Specification)
        │
        ▼ openapi-typescript CLI
packages/api-types/src/schema.d.ts (Raw TypeScript interfaces)
        │
        ▼ Clean re-exports
packages/api-types/src/index.ts (Importable types for apps/web)
```

### Command to Re-synchronize Types
From the repository root:
```bash
bun run gen:types
```
This runs:
1. `dump:schema`: Dumps `app.openapi()` to `apps/api/openapi.json`.
2. `openapi-typescript`: Compiles `openapi.json` into `packages/api-types/src/schema.d.ts`.

---

## 9. File Directory Reference for Sprint 4

| File Path | Role in Implementing Sprint 4 Ideas |
| :--- | :--- |
| `apps/api/main.py` | Core route endpoints (`/generate-stream`, `/regenerate/*`), `ask_gemini` temperature support, validation retry loops. |
| `apps/api/prompts.py` | `SEGMENT_PROMPT` update (facts vs angles), `FORMAT_SPECS` dictionary, few-shot examples, banned phrases. |
| `apps/api/schemas.py` | New `Fact`, `Angle`, and `Scene` models; optional `speaker` & `visual` on `Line`; `format` fields. |
| `apps/api/validation.py` | *[Proposed new file]* Deterministic Python validator checking word count, hook duration, line IDs, and Bengali Unicode. |
| `apps/api/audit.py` | Adding script feedback/rating storage to `generation_logs`. |
| `apps/api/tests/` | Unit and integration test suite (must be extended for new validation rules and schemas). |
| `packages/api-types/src/index.ts` | Re-exporting newly generated TypeScript types. |
