# Sprint 3 Changelog: Security, Telemetry & First Deployment

## Log Entry: UI Bug Fix, Multi-Stage Containerization, & Baseline Cloud Run Deployment

**Date**: 2026-11-11  
**Status**: Completed & Verified Live  
**Live Service URL**: `https://ug-scripts-363767463375.asia-southeast1.run.app` (Region: `asia-southeast1`)

---

### 1. UI Bug Fix: Pinned Reason Deselection on Outside Click

* **File Modified**: [`apps/web/src/components/ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx)
* **Problem**: In Sprint 2, clicking outside the script card deselected any active line selection, but clicking outside the reasoning workbench left pinned technique reason cards active.
* **Resolution**:
  - Attached `workbenchRef = useRef<HTMLDivElement>(null)` to the `.workbench` container enclosing both `ScriptCard` and `ReasonList`.
  - Added a `pointerdown` listener on `document` active whenever `workspace.selection.kind === 'reason'`.
  - If a pointer click lands outside `workbenchRef.current`, the reducer dispatches `{ type: 'SELECT_NONE' }`, cleanly deselecting the pinned reason card and removing highlighted line cues.

---

### 2. FastAPI Production Static Asset & SPA Serving

* **File Modified**: [`apps/api/main.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/main.py)
* **Implementation**:
  - Mounted `/assets` to serve hashed Vite CSS and JavaScript bundles using `StaticFiles`.
  - Registered a fallback catch-all route `@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)` that returns `index.html` for single-page application routing.
  - Appended this router *after* all existing API routes (`/health`, `/generate`, `/generate-stream`, `/regenerate/*`), preventing any path interception or route shadowing.
  - Made static folder resolution conditional: activates only if `/app/static` or `apps/web/dist` exists, leaving local development (`uvicorn` + `vite dev`) and the offline pytest suite 100% unaffected.

---

### 3. Unified Multi-Stage Container & Ignore Configuration

* **Files Created**:
  - [`Dockerfile`](file:///home/bast0k/projects/ug-script-writer/Dockerfile): Multi-stage build:
    - **Stage 1 (`oven/bun:1-alpine`)**: Copies monorepo manifests, runs `bun install --frozen-lockfile`, and builds `apps/web` with `VITE_API_URL=""` for same-origin relative API requests.
    - **Stage 2 (`python:3.12-slim`)**: Installs `apps/api/requirements.txt`, copies backend application code, and copies built web assets from Stage 1 into `/app/static`.
  - [`.dockerignore`](file:///home/bast0k/projects/ug-script-writer/.dockerignore): Excludes `node_modules`, `.venv`, `.pytest_cache`, `.git`, `.env*`, and documentation from Docker build contexts.
  - [`.gcloudignore`](file:///home/bast0k/projects/ug-script-writer/.gcloudignore): Mirrors ignore rules for fast Google Cloud Build upload without uploading local virtual environments.

---

### 4. GCP IAM Hardening & Baseline Cloud Run Deployment

* **Services Enabled**:
  - `run.googleapis.com` (Cloud Run)
  - `cloudbuild.googleapis.com` (Cloud Build)
  - `artifactregistry.googleapis.com` (Artifact Registry)
* **IAM Permissions Granted**:
  - Granted `roles/storage.objectViewer`, `roles/artifactregistry.writer`, and `roles/logging.logWriter` to Cloud Build service account `363767463375-compute@developer.gserviceaccount.com`.
  - Attached existing Vertex AI service account `ugstar-ai-user@ugstar.iam.gserviceaccount.com` (`roles/aiplatform.user`) to the Cloud Run service.
* **Deployment Details**:
  - Service Name: `ug-scripts`
  - Project: `ugstar` (363767463375)
  - Region: `asia-southeast1` (low-latency hub for Bangladesh/South Asia)
  - Memory: 1 GiB | CPU: 1 vCPU | Timeout: 120s
* **Live Verification**:
  - Verified `GET /` serves React frontend HTML and bundled JS/CSS assets.
  - Verified `GET /health` returns HTTP 200 `{"status": "healthy", "project_configured": true}`.
  - Verified `POST /regenerate/line/rephrase` executes Gemini on Vertex AI keylessly via Application Default Credentials (ADC), generating authentic spoken Bengali dialogue in `<2.5s`.

---

## Log Entry: Security, Access Gating, Telemetry, Audit Logging & Demo Catalog

**Date**: 2026-11-11  
**Status**: Implemented, Seeded, Tested (34/34 Backend Tests Passing, 0 Frontend Warnings/Errors)

### 1. Architecture & Background Execution Model
* **FastAPI `BackgroundTasks` Architecture**:
  - `starlette.background.BackgroundTasks` runs tasks **after** the HTTP response has been flushed to the network client.
  - When an `async def` task is added (such as `_log_generation_audit`), Starlette awaits it on the **same `asyncio` event loop** in the main thread (cooperative, non-blocking asynchronous I/O). It does **not** spawn a new OS thread, preserving memory and avoiding thread race conditions.
  - If a regular synchronous `def` function is passed, Starlette automatically offloads it to a threadpool worker (`anyio.to_thread.run_sync`).
  - This ensures script generation latency is never burdened by audit database writes or Cloud Storage image archiving.

---

### 2. Access Control & Invitation-Gated Modal (`auth.py`, `AccessGateModal.tsx`)
* **Backend**:
  - [`apps/api/auth.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/auth.py): Implements in-memory TTL caching (60 seconds) for Firestore access code lookups, minimizing read latency.
  - Validates `X-Access-Code` header against the `access_codes` Firestore collection, checking active status.
  - Admin/CI bypass supported via `X-API-Key`.
  - Added `POST /auth/verify` to validate codes during login and return remaining token allowance.
  - Added `POST /auth/request-access` to capture demo leads into Firestore collection `access_requests` with sliding-window IP rate limiting (max 3 submissions / hour).
  - Webhook dispatch configured to notify admins via Slack/Discord if `LEAD_NOTIFICATION_WEBHOOK_URL` is set.
* **Frontend**:
  - [`apps/web/src/components/AccessGateModal.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/AccessGateModal.tsx): Dual-mode modal (Enter Code & Request Access). Persists validated codes in `localStorage.ug_access_code`.
  - Global `ug:unauthorized` event handler automatically evicts expired/revoked codes and re-prompts the modal.

---

### 3. Token Telemetry & Usage Tracking (`usage.py`, `useTokenTracker.ts`)
* **Backend**:
  - [`apps/api/usage.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/usage.py): Request-scoped `ContextVar` token accumulator (`TokenAccumulator`).
  - Automatically intercepts Vertex AI Gemini `response.usage_metadata` across initial generation and granular regenerations (extracts `prompt_token_count`, `candidates_token_count`, and `total_token_count`).
  - Granular endpoints return usage in the custom `X-Token-Usage: {"prompt_tokens":..., "candidates_tokens":..., "total_tokens":...}` HTTP response header.
  - Streaming endpoints (`/generate-stream`, `/regenerate/section-stream`) emit the final token tally in the SSE `event: done` payload.
* **Frontend**:
  - [`apps/web/src/hooks/useTokenTracker.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/hooks/useTokenTracker.ts): Custom React hook listening for `ug:token-usage` custom events.
  - Tracks both session tokens (current browser tab) and lifetime tokens (persisted in `localStorage.ug_lifetime_tokens`).
  - Displayed prominently in the application masthead as an informative live pill badge (`Tokens: 1,240 session · 14.8k total`).

---

### 4. Generation Audit Logging & Cloud Storage Archival (`audit.py`, `firebase.py`)
* **Backend**:
  - [`apps/api/firebase.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/firebase.py): Lazy-initialized Google Cloud Firestore (`AsyncClient`) and Cloud Storage client with test mock injection hooks.
  - [`apps/api/audit.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/audit.py):
    - Archives user-uploaded product images to Google Cloud Storage (`gs://ugstar-images/audit/{run_id}.jpg`).
    - Records comprehensive generation documents in Firestore collection `generation_logs` (storing prompt inputs, segment outputs, scripts, tokens used, latency, timestamp, client IP, and access code ID).
    - Atomically increments token usage and generation counts on the associated `access_codes` document using `firestore.Increment`.

---

### 5. Curated Demo Products Catalog (`demo_products.py`, `DemoProductPicker.tsx`)
* **Backend**:
  - [`apps/api/demo_products.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/demo_products.py): Added `GET /demo-products`.
  - Queries Firestore `demo_products` collection ordered by display order.
  - Features robust fallback to **exactly 3 curated products** (`keshabati-hair-oil`, `sundarban-wild-honey`, `saffron-glow-serum`) if Firestore is unreachable or unseeded.
  - [`apps/api/scripts/seed_firestore.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/scripts/seed_firestore.py): CLI database seeder that populates all 12 diverse Bangladeshi and global products (apparel, electronics, natural food, cookware, skincare) and default access code `BETA-DHAKA-01`.
* **Frontend**:
  - [`apps/web/src/components/DemoProductPicker.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/DemoProductPicker.tsx): Interactive drawer with category filtering pills (Skincare, Tech, Fashion, Food, Home).
  - Clicking a demo card autofills product name, description, category, market, and language, and binds high-quality preset imagery without requiring image file uploads.
  - [`apps/web/src/components/ProductForm.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ProductForm.tsx): Integrated demo picker banner and image preview with "Upload custom" toggle.

---

### 6. Verification & Quality Assurance
* **Backend Unit & Integration Suite**:
  - 34/34 tests passing (`apps/api/.venv/bin/python3 -m pytest apps/api/tests/`).
  - Added [`apps/api/tests/test_auth.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/tests/test_auth.py) (access code verification, lead capture rate-limiting, demo product catalog fallback).
  - Added [`apps/api/tests/test_telemetry.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/tests/test_telemetry.py) (token header verification).
* **Frontend Build & Linter**:
  - `bun run build:web` cleanly compiled Vite bundle with no TypeScript errors.
  - `oxlint` reports 0 errors and 0 warnings across all 32 source files.

---

## Log Entry: Modal UI Simplification & Local Auth Fallback Resolution

**Date**: 2026-11-11  
**Status**: Completed & Verified in Container on `localhost:8080`

### 1. UI Simplification
* **Background & Modal Layout**:
  - Replaced the opaque pitch-black SVG backdrop with a modern blurred translucent overlay (`background: rgba(15, 23, 42, 0.45); backdrop-filter: blur(8px);`), keeping the underlying script assistant software visible.
  - Completely removed the bulky left-side `gate-cover` (film slate, mock video player, marketing pitch).
  - Streamlined the modal into a clean, centered single card (`max-width: 440px`) with clean brand badge and tabs.
  - Moved the demo video link into a clean header button: `View demo video` with play icon.
* **Shadcn-Style OTP Code Input**:
  - Removed the carnival ticket stub ("Admit One", notches, perforations).
  - Built a standard shadcn-style segmented OTP slot component with individual rounded cells (`[B][E][T][A] - [D][H][A][K][A] - [0][1]`), dark focus ring, blinking caret, and native keyboard/paste accessibility.

### 2. Resolution of Local Container Auth Rejection
* **Root Cause**:
  - `apps/api/.env` contained a lingering path `GOOGLE_APPLICATION_CREDENTIALS=/home/bast0k/projects/ug-script-writer/docs/ugstar-94b38dd789aa.json`.
  - When the Docker container started, `load_dotenv()` loaded this non-existent file path into `os.environ`, causing the Google Cloud client library to crash with `FileNotFoundError` during credentials initialization.
* **Resolution**:
  - Removed the invalid `GOOGLE_APPLICATION_CREDENTIALS` line from `apps/api/.env`.
  - Added defensive sanitization in [`apps/api/firebase.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/firebase.py) to automatically prune non-existent file paths before SDK initialization.
  - Added `FALLBACK_ACCESS_CODES` in [`apps/api/auth.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/auth.py) mirroring `demo_products.py`, ensuring local offline Docker runs without mounted GCP keys still recognize valid demo codes like `BETA-DHAKA-01`.
  - Tested and verified: `POST /auth/verify` returns HTTP 200 OK and unlocks the app.

---

## Log Entry: UI Polish, Access Gate Re-alignment & Shelf Product Square Redesign

**Date**: 2026-11-11  
**Status**: Completed & Verified (TypeScript + Vite build passed, Oxlint 0 errors/0 warnings, 34/34 Pytest passed)

### 1. Access Gate Modal Re-alignment & Polish
* **5-Character Code Input**:
  - Transitioned OTP input to exactly 5 boxes (`maxLength={5}`).
  - Used a CSS grid (`grid-template-columns: repeat(5, 1fr); width: 100%; gap: 10px;`) aligning the first box flush with the "Access Code" label above and the last box flush with the full-width submit button.
  - Added 5-character codes (`DEMO1`, `DHAKA`, `BETA1`, `UG001`) to Firestore and in-memory fallback dictionary.
* **Header & Tabs Reordering**:
  - Reordered the modal structure: brand masthead (`UG-Scripts v0.4.1`) -> `gate-header` with inline lock icon (`[🔒] Private demo access`) -> `gate-tabs` (`I have a code` | `Request access`) -> input form.
  - Softened background backdrop blur to `blur(4px)` with `rgba(15, 23, 42, 0.25)`, keeping underlying sections clearly discernible without visual interference.
* **Secondary "View demo video" Button**:
  - Moved "View demo video" from top right to directly underneath `button.gate-submit`.
  - Styled as a full-width secondary button: white background, light gray outline (`border: 1px solid #cbd5e1`), dark text, and an up-right diagonal external link arrow (`IconArrowUpRight`).

### 2. Sample Product Shelf Fixes
* **Outline Contrast Softening**:
  - Replaced high-contrast black borders (`var(--ink)`) on `.shelf-sheet` and `.shelf-bar.is-open` with subtle muted gray (`var(--line-strong)` / `#b4bdb7`) and softened elevation shadow.
* **Toolbar Overflow & Scrollbar Glitch Resolution**:
  - Fixed visual artifact cutting into the "Home & Living" category tab by adding `overflow-y: hidden`, `scrollbar-width: none; -ms-overflow-style: none`, and hiding `::-webkit-scrollbar` on `.shelf-tabs`.
* **Square Product Cards**:
  - Changed `.shelf-photo` from portrait `4 / 5` to a clean `1 / 1` square aspect ratio with `object-fit: cover`.

---

## Log Entry: Sprint Final Polish: Contained Rail Scrollbars, Direct Request Access & Root .env Docker Automation

**Date**: 2026-11-11  
**Status**: Completed & Verified in Container on `localhost:8080`

### 1. Rounded Shelf Sheet Boundary Containment
* **Problem**: The horizontal scrollbar on `.shelf-rail` rendered to the extreme rectangular bounds of the sheet (0% to 100% width), causing the scrollbar track/thumb to stick out past the 16px rounded corners at the bottom left and bottom right.
* **Resolution**:
  - Added `overflow: hidden` to `.shelf-sheet` to strictly clip all internal content and tracks to the 16px corner radii.
  - Added horizontal margin and track insets to `.shelf-rail`: `margin: 0 12px; padding: 16px 6px 12px;` and `.shelf-rail::-webkit-scrollbar-track { margin: 0 16px; }`.
  - The scrollbar now stays completely within the flat horizontal interior of the sheet, cleanly recessed from both rounded corners.

### 2. Direct "Request Access" Tab Activation from Masthead
* **Problem**: Clicking the masthead `.access-btn` always opened the modal to the default "I have a code" tab, requiring an extra click to switch to "Request access".
* **Resolution**:
  - Added `initialMode?: 'enter_code' | 'request_access'` prop to [`AccessGateModal.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/AccessGateModal.tsx).
  - In [`App.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.tsx), clicking `.access-btn` sets `accessInitialMode = 'request_access'`, automatically opening the modal with the "Request access" form active.
  - 401 unauthorized events automatically reset `accessInitialMode = 'enter_code'`, prioritizing entering a valid code.

### 3. Root `.env` & Automated Docker Configuration
* **Files Created & Modified**:
  - [`.env`](file:///home/bast0k/projects/ug-script-writer/.env): Root environment configuration with `GOOGLE_CLOUD_PROJECT=ugstar`, `GOOGLE_CLOUD_LOCATION=global`, `API_KEY`, `ALLOWED_ORIGINS`, and `PORT=8080`.
  - [`.env.example`](file:///home/bast0k/projects/ug-script-writer/.env.example): Sanitized template for team members and CI.
  - [`.dockerignore`](file:///home/bast0k/projects/ug-script-writer/.dockerignore): Updated to include root `.env*` in the Docker build context while keeping local Vite dev overrides (`apps/web/.env.local`) ignored.
  - [`Dockerfile`](file:///home/bast0k/projects/ug-script-writer/Dockerfile): Automatically copies root `.env*` into `/app/.env` during the build with a fallback to `.env.example`.
  - **Verification**: Built and ran `docker run -d -p 8080:8080 ug-scripts:local` without any manual `-e` flags or credentials. Tested `GET /health` (returned `project_configured: true`) and `POST /auth/verify` with code `DEMO1` (returned HTTP 200 OK).
