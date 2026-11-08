# Script Assistant API: Project Plan

*Product in, customer segments and ready-to-film scripts out. Gemini on Vertex AI, a small FastAPI service, and a React frontend, all in one monorepo.*

## 1. Goal and decisions

Build a Billo-style AI script writer. A user enters a product (name, description, category, image). The system returns 3 customer segments and 3 scripts, one per segment. Each script shows 3 reasons it should perform well, and each reason points at the exact lines that use the technique.

Decisions made so far:

- Run on existing Google Cloud credits: Vertex AI with Gemini. Start with gemini-3.5-flash; move only the script step to a stronger Gemini model if quality disappoints.
- No LangChain or agent framework. The flow is fixed, so it is a plain pipeline of structured-output calls using the google-genai SDK and Pydantic schemas. The older vertexai.generative\_models SDK is deprecated; do not use it.
- The product image is an input, because product photos carry a lot of information (packaging text, ingredients, specs, colors). Language (en or bn) and market are chosen per request in the frontend, not set as environment variables.
- There is no Billo-scale performance dataset. Start with hook patterns written into the prompt.

## 2. Pipeline

1. Frontend uploads name, description, category, market, language (en or bn) and an image to POST /generate.
2. Call 1 (segments): the model reads the image and description, then returns product\_facts (5-8 verifiable facts) and exactly 3 customer segments.
3. Calls 2-4 (scripts), run in parallel, one per segment. Each gets the product facts as plain text (not the image again), the segment, and an assigned hook style. Each returns a script with numbered lines and 3 reasons that cite line ids.
4. The API returns facts, segments and scripts together.

Why the facts step exists: it pays for the image once, and it stops the script step from inventing claims the image and description do not support.

Why hook styles are assigned: the three script calls run in parallel and cannot see each other, so each gets a different hook style (curiosity question, problem callout, demo or before-after) to keep the scripts from sounding alike.

Expected latency is 10-20 seconds end to end, because the two stages run in sequence.

## 3. Monorepo layout

Add two apps beside whatever already exists in the repo:

```
repo/
  apps/
    api/              FastAPI service (Python)
      main.py
      schemas.py
      prompts.py
      requirements.txt
      Dockerfile
    web/              React + Vite + TypeScript
  packages/
    api-types/        TypeScript types generated from the API's OpenAPI schema
  package.json        workspace root (pnpm workspaces)
  pnpm-workspace.yaml
```

The Python app lives in the JS monorepo as an independent app: it has its own requirements.txt and is not managed by pnpm. The web app consumes the API only over HTTP.

## 4. API service (apps/api)

### Contract

POST /generate, multipart/form-data:

- name (string), description (string), category (string), market (free text such as Bangladesh), language (en or bn)
- image (file): JPEG, PNG or WebP, at most 5 MB

Response JSON: facts (string list), segments (3 items), scripts (3 items, same order as segments). Errors: 415 for a wrong image type, 413 for an oversized image, 422 for missing fields, an empty or overlong market, or a language other than en or bn, 401 for a bad API key.

### Dependencies

fastapi, uvicorn, google-genai, pydantic, python-multipart.

### Environment variables

- GOOGLE\_CLOUD\_PROJECT, GOOGLE\_CLOUD\_LOCATION (use global)
- API\_KEY: shared secret checked on every request via an X-API-Key header
- ALLOWED\_ORIGINS: the web app's origin(s) for CORS

For local development run gcloud auth application-default login so the SDK can authenticate.

### schemas.py

```python
from typing import Literal
from pydantic import BaseModel

class Segment(BaseModel):
    name: str
    who: str
    pain_point: str
    platforms: list[str]

class Segments(BaseModel):
    product_facts: list[str]
    segments: list[Segment]   # prompt asks for exactly 3

class Line(BaseModel):
    id: int
    kind: Literal['hook', 'concept', 'cta']
    text: str

class Reason(BaseModel):
    title: str
    why: str
    line_ids: list[int]

class Script(BaseModel):
    segment: str
    lines: list[Line]
    reasons: list[Reason]     # prompt asks for exactly 3

class GenerateResponse(BaseModel):
    facts: list[str]
    segments: list[Segment]
    scripts: list[Script]
```

### main.py

```python
import asyncio, os
from typing import Literal
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from schemas import *
from prompts import SEGMENT_PROMPT, SCRIPT_PROMPT

client = genai.Client(
    vertexai=True,
    project=os.environ['GOOGLE_CLOUD_PROJECT'],
    location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'global'))
MODEL = 'gemini-3.5-flash'
LANGUAGES = {'en': 'English', 'bn': 'Bangla'}
ALLOWED = {'image/jpeg', 'image/png', 'image/webp'}
MAX_BYTES = 5 * 1024 * 1024
HOOKS = ['curiosity question', 'problem callout', 'demo / before-after']

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get('ALLOWED_ORIGINS', '').split(','),
    allow_methods=['POST'], allow_headers=['*'])

async def ask(prompt, schema, parts=()):
    r = await client.aio.models.generate_content(
        model=MODEL, contents=[*parts, prompt],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_schema=schema))
    return r.parsed

@app.post('/generate', response_model=GenerateResponse)
async def generate(
    name: str = Form(...), description: str = Form(...),
    category: str = Form(...), market: str = Form(...),
    language: Literal['en', 'bn'] = Form(...),
    image: UploadFile = File(...),
    x_api_key: str = Header(None)):
    if x_api_key != os.environ['API_KEY']:
        raise HTTPException(401, 'Bad API key')
    market = market.strip()
    if not market or len(market) > 60:
        raise HTTPException(422, 'Market must be 1-60 characters')
    if image.content_type not in ALLOWED:
        raise HTTPException(415, 'Use a JPEG, PNG or WebP image')
    data = await image.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, 'Image must be 5 MB or smaller')
    img = types.Part.from_bytes(data=data, mime_type=image.content_type)

    segs = await ask(
        SEGMENT_PROMPT.format(name=name, category=category,
                              description=description, market=market),
        Segments, parts=[img])
    facts = '\n'.join('- ' + f for f in segs.product_facts)
    scripts = await asyncio.gather(*[
        ask(SCRIPT_PROMPT.format(
                name=name, category=category, facts=facts,
                segment_name=s.name, who=s.who, pain_point=s.pain_point,
                hook=HOOKS[i], market=market,
                language=LANGUAGES[language]),
            Script)
        for i, s in enumerate(segs.segments)])
    return {'facts': segs.product_facts,
            'segments': segs.segments, 'scripts': scripts}
```

## 5. Prompts (prompts.py)

These two prompts are where output quality lives. Iterate on them against the test set in section 8.

### SEGMENT\_PROMPT

```
You are a performance-marketing strategist for short-form UGC video ads
(TikTok, Reels, Shorts) in {market}.

PRODUCT
Name: {name}
Category: {category}
Description: {description}
The attached image is the product photo. Read it closely: packaging
text, ingredients/specs, colors, size cues, anything a viewer notices.

TASK
1. product_facts: 5-8 concrete, verifiable facts drawn ONLY from the
   description and image. No invented claims.
2. segments: exactly 3 customer segments most likely to buy. They must
   differ in motivation, not just age. For each: name, who (age range,
   situation, daily context), pain_point (in their own words), platforms.
Be specific. 'Young professionals' is too vague.
```

### SCRIPT\_PROMPT

```
You write scripts that a creator films on a phone for a short-form ad in
{market}. Write in {language}, spoken and natural, never ad-copy stiff.

PRODUCT: {name} ({category})
FACTS YOU MAY USE:
{facts}
TARGET: {segment_name}: {who}. Pain point: {pain_point}
HOOK STYLE: {hook}

RULES
- 20-35 seconds spoken (about 60-90 words).
- Structure: hook (first 3 seconds, must stop the scroll), concept, cta.
  Tag each line with its kind and number lines from 1.
- Use only the facts above. No medical claims, no '#1', no made-up
  numbers or testimonials.
- Speak to this segment's pain point, not to everyone.
- reasons: exactly 3. Each names a specific technique (pattern
  interrupt, specificity, objection handling, social proof, etc.),
  explains why it works for THIS segment, and lists the line_ids that
  use it. Never cite a line that does not do what you claim.
```

Note: the reasons are the model's rationale, not measured performance. Until real data exists, label them as why the script is built this way, not as a prediction.

## 6. Deployment (Cloud Run)

- Add a Dockerfile in apps/api that installs requirements and runs uvicorn on the port Cloud Run provides.
- Deploy with gcloud run deploy script-api --source apps/api, set the env vars from section 4.
- Grant the service account the Vertex AI User role so Gemini calls need no API key.
- The endpoint is protected by the X-API-Key check. Set a Cloud Run request timeout of at least 60 seconds.

## 7. React frontend (apps/web)

### Setup

```
cd apps
pnpm create vite web --template react-ts
cd web && pnpm install
```

Add the package to the workspace in pnpm-workspace.yaml (apps/*, packages/*). Optional: add Tailwind for styling and TanStack Query for the request state.

Environment (apps/web/.env.local): VITE\_API\_URL and VITE\_API\_KEY. In local development you can instead use a Vite dev-server proxy to the API to avoid CORS.

Security note: anything in a VITE\_ variable ships to the browser. That is acceptable for an internal tool or early testing. Before the page is public, send requests through your own backend (for example the existing Worker) that holds the key.

### Keep types in sync

FastAPI publishes /openapi.json. Generate TypeScript types from it into packages/api-types with openapi-typescript, and add a script (for example pnpm gen:types) that re-runs it after schema changes. The frontend then imports Script, Segment and GenerateResponse instead of hand-writing them.

### Request

```ts
const form = new FormData();
form.append('name', name);
form.append('description', description);
form.append('category', category);
form.append('market', market);       // free text, for example 'Bangladesh'
form.append('language', language);   // 'en' or 'bn'
form.append('image', file);
const res = await fetch(`${import.meta.env.VITE_API_URL}/generate`, {
  method: 'POST',
  headers: { 'X-API-Key': import.meta.env.VITE_API_KEY },
  body: form,
});
```

Do not set the Content-Type header yourself; the browser adds the multipart boundary.

### Screens and components

- ProductForm: name, description, category (select), market (text input with a default such as Bangladesh), language (an English / Bangla toggle that sends en or bn), and an image dropzone with a preview. Validate type (JPEG, PNG, WebP) and size (5 MB) before sending. Submit button disabled while loading.
- LoadingState: shown for the 10-20 second wait, with a note that scripts are being written. Do not freeze the form silently.
- ResultsView: shows product facts as chips, then three segment tabs or cards.
- SegmentCard: segment name, who, pain point, platforms.
- ScriptCard: lines listed in order with their number, color-coded by kind (hook, concept, cta). A copy-script button copies the plain text of the lines.
- ReasonList: three reasons per script. Selecting or hovering a reason highlights the lines in its line\_ids; hovering a line shows which reasons cite it.
- ErrorBanner: friendly messages for 413, 415, 422, 401 and network or timeout failures, with a retry button that keeps the form contents.

Keep the last result in component state so switching between segment tabs does not trigger another request.

## 8. Testing and quality

- Keep a test set of about 10 varied products (different categories, with images) and run the API against all of them after every prompt change. Save the outputs side by side.
- Check by hand: do scripts use only the stated facts, is the hook in the first 3 seconds, are the language and tone natural, do the cited line ids match the technique named.
- Log every request and response (without the API key) so real usage can be reviewed when tuning prompts.
- Add a lightweight validation step in the API: reject and retry once if the output has fewer than 3 segments, fewer than 3 reasons, or reasons citing line ids that do not exist.

## 9. Build order

1. apps/api: schemas, endpoint, prompts; test with curl and the 10-product test set.
2. Deploy to Cloud Run and confirm the credits are being used.
3. apps/web: form with image upload, language and market inputs, request, and a plain results view.
4. Generated types, line highlighting for reasons, loading and error states.
