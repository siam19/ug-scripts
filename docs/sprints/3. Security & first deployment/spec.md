
# Sprint 3 Specification: Security, Telemetry & First Deployment

> **Target Location**: `docs/sprints/3. Security & first deployment/spec.md`
> **Prerequisites**: Sprint 2 Completed (28/28 backend tests passing, `oxlint` 0 errors/warnings)
> 
> 
> **Infrastructure**: GCP Cloud Run + Firebase (Firestore Native Mode + Firebase Cloud Storage) + Vertex AI (`gemini-2.5-flash`)
> 
> 

---

## 1. Sprint 3 Objectives & Scope

1. **Bug Fix**: Fix click-outside deselection for active `reason` items in the workbench (`ResultsView.tsx` / `ReasonList.tsx`) to match `ScriptCard.tsx` line deselection behavior.


2. **Access Gate & Request Access**: Restrict app access behind an access code modal backed by Firestore, with a "Request Access" lead capture form and instant webhook notification.
3. **Token Accounting & Masthead Usage UI**: Track prompt and completion tokens across all full and granular generation endpoints, displaying session and lifetime usage in the app masthead.


4. **Generation Audit Logging & Image Archival**: Asynchronously archive every generation/regeneration payload to Firestore and user-uploaded product images to Firebase Storage.
5. **On-Demand Demo Products**: Serve 12 curated demo products from Firestore + Firebase Storage, fetched lazily only when requested in `ProductForm.tsx`.


6. **Production Cloud Run Deployment**: Package `apps/web` and `apps/api` into a unified multi-stage Docker container deployed on Google Cloud Run.



---

## 2. Cloud & Storage Architecture (Firebase + GCP)

Both `google-cloud-firestore` and `google-cloud-storage` run inside `apps/api` using **Application Default Credentials (ADC)**—no service account JSON files need to be bundled into the image.

### 2.1 Firestore Collections

#### 1. `access_codes` (Document ID: `<CODE>`, e.g., `BETA-DHAKA-01`)

```json
{
  "owner_name": "Demo Tester",
  "company": "Acme D2C",
  "active": true,
  "total_input_tokens": 14250,
  "total_output_tokens": 5310,
  "total_tokens": 19560,
  "generation_count": 8,
  "created_at": "2026-11-11T00:00:00Z",
  "last_used_at": "2026-11-11T01:15:00Z"
}

```

#### 2. `access_requests` (Document ID: Auto-ID)

```json
{
  "name": "Rahim Uddin",
  "phone": "+8801700000000",
  "company": "Chaldal / Independent",
  "status": "pending",
  "created_at": "2026-11-11T01:20:00Z"
}

```

#### 3. `demo_products` (Document ID: `<slug>`, e.g., `arong-hair-oil`)

```json
{
  "id": "arong-hair-oil",
  "name": "Keshabati Cold-Pressed Onion & Black Seed Hair Oil",
  "category": "Haircare & Beauty",
  "description": "100% cold-pressed herbal hair oil with red onion extract, kalonji, and rosemary. Non-sticky formula that reduces hair fall in 3 weeks.",
  "market": "Bangladesh",
  "language": "bn",
  "image_url": "https://firebasestorage.googleapis.com/.../demo-products/arong-hair-oil.webp",
  "order": 1
}

```

#### 4. `generation_logs` (Document ID: `<log_id>` UUID)

```json
{
  "access_code": "BETA-DHAKA-01",
  "endpoint": "/generate/stream",
  "product_meta": {
    "name": "Keshabati Hair Oil",
    "category": "Haircare & Beauty",
    "market": "Bangladesh",
    "language": "bn",
    "is_demo_product": false
  },
  "image_storage_uri": "gs://ugstar-94b38dd789aa.firebasestorage.app/uploads/BETA-DHAKA-01/9b1deb4d.webp",
  "image_public_url": "https://...",
  "request_payload": {},
  "response_payload": {},
  "usage": {
    "input_tokens": 1840,
    "output_tokens": 920,
    "total_tokens": 2760,
    "estimated_cost_usd": 0.00085
  },
  "created_at": "2026-11-11T01:30:00Z"
}

```

### 2.2 Firebase Cloud Storage Bucket Layout

```text
gs://<PROJECT_ID>.firebasestorage.app/
├── demo-products/                  # 12 pre-uploaded ~100KB WebP product images
│   ├── bd-hair-oil.webp
│   ├── bd-specialty-coffee.webp
│   └── ... (12 total)
└── uploads/                        # User-uploaded product photos archived in background
    └── {access_code}/
        └── {log_id}.{jpg|png|webp}

```

---

## 3. Detailed Feature Specifications

### 3.1 Bug Fix: Workbench `ReasonItem` Click-Outside Deselection

* **Problem**: Clicking outside `ScriptCard.tsx` deselects a selected line via a `pointerdown` listener, but clicking outside `ReasonList.tsx` / `ResultsView.tsx` leaves a selected `reason-item` active.


* **Solution**:
* In `ResultsView.tsx` (or `ReasonList.tsx`), attach a `document.addEventListener('pointerdown', ...)` effect active whenever `workspace.selection.kind === 'reason'`.


* If the click target is outside both `reasonListRef.current` and `scriptCardRef.current` (so clicking highlighted cited lines inside the script card doesn't prematurely clear context), dispatch `SELECT_NONE` (`{ kind: 'none' }`).





---

### 3.2 Feature 1: Access Code Gate & "Request Access" Flow

* **Backend (`apps/api`)**:
* **`POST /auth/verify`**: Accepts `{ "code": str }`. Queries `access_codes/{code}`. If missing or `active == False`, returns `HTTP 401`. If valid, returns:
```json
{
  "valid": true,
  "owner_name": "Demo Tester",
  "total_input_tokens": 14250,
  "total_output_tokens": 5310,
  "total_tokens": 19560
}

```


* **`POST /auth/request-access`**: Accepts `{ "name": str, "phone": str, "company": str }`. Rate-limited via `SlidingWindowRateLimiter` (3 req/hour per IP). Saves document to `access_requests` and triggers a `BackgroundTask` that sends a formatted message to `NOTIFY_WEBHOOK_URL` (Telegram Bot API or Discord Webhook).


* **Auth Dependency (`verify_access_code`)**: Replaces static `X-API-Key` validation on `/generate`, `/generate/stream`, `/regenerate/*`, and `/demo-products` by reading the `X-Access-Code` header and verifying it against an in-memory 60-second TTL cache backed by Firestore `access_codes`.




* **Frontend (`apps/web`)**:
* Store verified access code in `localStorage` (`ug_access_code`).
* Create `AccessGateModal.tsx` with two views:
1. **Enter Code View**: Input for access code + "Unlock App" primary CTA + "Need a code? Request Access" secondary button.
2. **Request Access View**: Inputs for `Name`, `Phone`, and `Company` + Submit button showing confirmation state.


* Attach `X-Access-Code` header in `useGenerateScript.ts` and `useRegenerate.ts`. If any API call returns `401`, clear `ug_access_code` and re-open `AccessGateModal`.





---

### 3.3 Feature 2: Modular Token Counting & Masthead Usage Tracker

* **Backend (`apps/api/usage.py`)**:
* Create a `contextvars.ContextVar("token_usage")` holding a mutable `TokenUsageAccumulator(input_tokens=0, output_tokens=0)`.
* Inside `ask_gemini()` (`apps/api/main.py`), after `response = await client.aio.models.generate_content(...)`, extract:


```python
usage = response.usage_metadata
if usage:
    acc = token_usage_var.get()
    acc.add(
        prompt_tokens=usage.prompt_token_count or 0,
        output_tokens=usage.candidates_token_count or 0,
    )

```


* Because `POST /generate` runs Stage 1 followed by 3 concurrent Stage 2 calls via `asyncio.gather`, child coroutines inherit the request's `ContextVar` and automatically sum all 4 Gemini calls into a single request total.


* **Transport to Frontend**:
* Standard JSON endpoints (`/generate`, `/regenerate/*`): Inject response header `X-Token-Usage: {"in": 1840, "out": 920, "total": 2760}` and expose it in CORS `expose_headers`.


* Streaming endpoint (`/generate/stream`): Include the `usage` object in the final SSE `complete` / `done` event payload.






* Frontend Masthead UI (`App.tsx`):


* Maintain `sessionTokens` (in `sessionStorage`) and `lifetimeTokens` (hydrated from `POST /auth/verify` and incremented after each generation/regeneration).
* Render a compact pill in the `masthead` header:
`Tokens: 2.7k session · 22.3k total` (with a hover tooltip showing input/output breakdown and estimated USD cost based on `gemini-2.5-flash` pricing).





---

### 3.4 Feature 3: Generation Audit Logging & Firebase Storage Image Archival

* **Backend (`apps/api/audit.py`)**:
* Create `log_generation_task(...)` executed via FastAPI `BackgroundTasks`:
1. If `endpoint` is `/generate` or `/generate/stream`:


* If the user uploaded a custom file (not a preset `demo_product_id`), upload `image_bytes` to Firebase Cloud Storage at `uploads/{access_code}/{log_id}.{ext}` and generate its storage URI.
* If the user used a demo product, reference the existing `demo_products` image URL.


2. **Write `generation_logs/{log_id}` in Firestore** with `access_code`, `endpoint`, `product_meta`, `request_payload`, `response_payload`, `usage`, and `created_at`.
3. **Atomically update `access_codes/{access_code}**` using `firestore.Increment` on `total_input_tokens`, `total_output_tokens`, `total_tokens`, and `generation_count`, plus `last_used_at`.





---

### 3.5 Feature 4: Lazy-Loaded Demo Products via Firestore

* **Backend**:
* **`GET /demo-products`**: Queries `firestore.collection("demo_products").order_by("order").stream()`. Cached in memory for 10 minutes (`ttl_cache`) so repeated opens cost zero Firestore reads.
* Update `POST /generate` & `POST /generate/stream`: Allow either `image: UploadFile` OR `demo_product_id: str`. If `demo_product_id` is passed, FastAPI fetches the demo image bytes from Firebase Storage in-memory (with a local LRU cache) so the browser doesn't even have to download and re-upload the image file!




* Frontend (`ProductForm.tsx`):


* Add a **"Try a Demo Product"** collapsible drawer/modal trigger at the top of `ProductForm.tsx`.


* Clicking the button triggers `GET /demo-products` (lazy fetch on first open) and displays the 12 products (6 Bangladesh `bn`/`en`, 6 Global `en`) as compact cards with thumbnail, name, category badge, and language tag.


* Clicking a card populates `name`, `category`, `description`, `market`, `language`, displays the remote thumbnail preview in the image dropzone, and sets `demoProductId` on the form state.




* **Seed Script (`apps/api/scripts/seed_firestore.py`)**:
* A one-command CLI script to upload the 12 curated demo images to Firebase Storage, seed the `demo_products` collection, and create initial `access_codes`.



---

### 3.6 Feature 5: Unified Cloud Run Deployment

┌───────────────────────────────────────────────────────────┐
│              Google Cloud Run (Single Service)            │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ FastAPI (Uvicorn)                                   │  │
│  │  ├── /api/*        ──> API & SSE Streaming Routes   │  │
│  │  └── /*            ──> StaticFiles (apps/web/dist)  │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────┬─────────────────────────────┬──────────────┘
               │ (ADC Auth)                  │ (ADC Auth)
               ▼                             ▼
     ┌──────────────────┐          ┌──────────────────┐
     │    Vertex AI     │          │    Firestore     │
     │ gemini-2.5-flash │          │   Native Mode    │
     └──────────────────┘          └────────────────── 

* **Single-Container Multi-Stage `Dockerfile` (Root)**:
* **Stage 1 (`oven/bun:1-alpine`)**: Installs workspace dependencies, generates `packages/api-types`, and runs `bun build:web` (`VITE_API_URL=""` for same-origin requests).


* **Stage 2 (`python:3.12-slim`)**: Installs `apps/api/requirements.txt` (adding `google-cloud-firestore`, `google-cloud-storage`, `httpx`), copies `apps/api`, and copies `apps/web/dist` into `/app/static`.



* FastAPI Static Mounting (`apps/api/main.py`):


* Prefix API routes (or mount static assets last with a SPA fallback route) so `/` serves `index.html` and `/assets/*` serves Vite's hashed bundles.
* Add `X-Accel-Buffering: no` header to `StreamingResponse` on `/generate/stream` so Cloud Run's proxy flushes SSE events immediately.




* New Environment Variables (`apps/api/.env`):



| Variable | Description | Example |
| --- | --- | --- |
| `GOOGLE_CLOUD_PROJECT` | GCP & Firebase Project ID

 | `ugstar-94b38dd789aa`

 |
| `FIREBASE_STORAGE_BUCKET` | Firebase Cloud Storage bucket name | `ugstar-94b38dd789aa.firebasestorage.app` |
| `FIRESTORE_DATABASE` | Firestore database ID | `(default)` |
| `NOTIFY_WEBHOOK_URL` | Telegram / Discord webhook for access requests | `[https://api.telegram.org/bot.../sendMessage](https://api.telegram.org/bot.../sendMessage)` |

---

## 4. Future Sprints Roadmap (Sprint 4+)

The following architectural items are intentionally deferred from Sprint 3 to keep the first deployment lean and focused:

1. **Google Docs Direct Integration (Portfolio Showcase)**:
* Integrate Google Identity Services (GIS) OAuth2 (`drive.file` non-sensitive scope) to allow 1-click export of a generated script, persona card, and marketing rationale directly into a formatted Google Doc in the user's Google Drive, alongside `.docx` download.




2. **Server-Side Reverse Proxy & BFF (Backend-for-Frontend) Auth**:
* Replace client-held headers with `HttpOnly`, `Secure`, `SameSite=Strict` session cookies issued via a server-side proxy / edge worker so access tokens are never accessible to client-side JavaScript.


3. **Distributed Rate Limiting (Redis / Cloud Armor)**:
* Upgrade `apps/api/rate_limiter.py` from the current per-process in-memory `SlidingWindowRateLimiter` to Redis (Memorystore / Upstash) or GCP Cloud Armor so rate limits hold consistently across multiple Cloud Run container instances.




4. **Admin & Analytics Dashboard (`/admin`)**:
* Build an internal view to approve `access_requests` with 1 click (auto-generating an access code and messaging the requester), browse `generation_logs` with uploaded product images, and inspect per-company token cost breakdowns.


5. **Per-Code Token Quotas & Hard Caps**:
* Add a `max_tokens_limit` field to `access_codes` documents so demo codes automatically deactivate once a tester consumes their allocated token budget (e.g., 100k tokens).



---

## 5. Implementation Checklist (Step-by-Step)

* [ ] **Step 1**: Fix `ReasonList` click-outside deselection in `ResultsView.tsx`.


* [ ] **Step 2**: Add `google-cloud-firestore`, `google-cloud-storage`, and `httpx` to `apps/api/requirements.txt` and create `apps/api/firebase.py` client initializer.


* [ ] **Step 3**: Implement `POST /auth/verify`, `POST /auth/request-access`, and the `verify_access_code` FastAPI dependency.
* [ ] **Step 4**: Implement `ContextVar` token accumulator in `ask_gemini()`, attach `X-Token-Usage` header, and wire up `BackgroundTasks` for `generation_logs` + Firebase Storage image upload.


* [ ] **Step 5**: Implement `GET /demo-products`, `demo_product_id` support in `/generate`, and `scripts/seed_firestore.py`.


* [ ] **Step 6**: Regenerate shared OpenAPI TypeScript types (`bun gen:types`).


* [ ] **Step 7**: Build `<AccessGateModal/>`, Masthead token usage pill, and the lazy-loaded Demo Product selector in `ProductForm.tsx`.


* [ ] **Step 8**: Write backend unit/integration tests for auth, token headers, and demo products (`bun test:api`).


* [ ] **Step 9**: Create root multi-stage `Dockerfile` and deploy to Cloud Run.
