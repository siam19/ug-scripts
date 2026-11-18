# Sprint 7 Goals: Google Docs Export, Cost Meter & Quality Backlog

**Sprint Objective**: Enable 1-click export of generated scripts (with facts, segment persona, visual cues, and marketing rationales) to Google Docs, surface estimated session cost in BDT inside the masthead `TokenMeter`, and ship high-value backlog items from Sprints 2–4.

**Explicitly Out of Scope**:
- Visual Scenes & Storyboarding (Sprint 4 Phase 6)
- Distributed Rate Limiting (Redis / Cloud Armor)
- Admin & Analytics Dashboard (`/admin`)
- Per-Code Token Quotas & Hard Caps

---

## Task Tracker

### 1. Export to Google Docs (Primary Feature)
- [x] **Google Identity Services (GIS) OAuth2 Integration (`apps/web`)**
  - Load GIS client (`https://accounts.google.com/gsi/client`) lazily or via script tag and request an OAuth2 access token with non-sensitive `https://www.googleapis.com/auth/drive.file` scope.
  - Support runtime config (`VITE_GOOGLE_CLIENT_ID` with optional backend fallback endpoint so Cloud Run builds work via `.env` without baking Vite build args).
  - Cache the short-lived OAuth token in memory for the browser session and handle popup dismissal / revoked tokens cleanly.
- [x] **Google Docs Document Formatter & Upload (`apps/web`)**
  - Convert a script + segment + product context (facts, creative angles, persona card, numbered lines with `Hook`/`Concept`/`CTA` tags, timestamps, `Visual Direction` cues, and marketing rationales with cited line numbers) into a cleanly structured Google Doc (via Drive multipart HTML-to-Doc import or Google Docs API `documents.create` + `batchUpdate`).
  - Ensure full UTF-8 / Bengali script (`বাংলা`) rendering fidelity.
- [x] **UI Controls & Fallback Download (`ScriptCard.tsx`, `SavedScriptsDrawer.tsx`)**
  - Add an **"Export to Google Docs"** button with loading/pending state, toast confirmation containing a clickable **"Open in Google Docs"** link (`https://docs.google.com/document/d/<id>/edit`), and friendly error reporting.
  - Provide a secondary **Download `.docx` / `.md`** (or printable) fallback option so users without Google sign-in can still export offline.

### 2. Masthead Token & BDT Cost Meter (`TokenMeter.tsx`, `useTokenTracker.ts`)
- [x] **Session Cost Estimation (`apps/web/src/state/pricing.ts` or `useTokenTracker.ts`)**
  - Compute rough USD and BDT (`৳`) cost from `sessionInput` and `sessionOutput` tokens (with a fallback blended rate if only `total_tokens` is reported).
  - Keep pricing constants (per-1M input/output USD rate and `USD_TO_BDT` exchange rate) centralized and easy to update.
- [x] **Masthead Pill & Receipt Popover UI (`TokenMeter.tsx`, `App.css`)**
  - Update the masthead pill so users see both session tokens and approximate session cost in BDT (e.g., `12.4k · ~৳0.45`) while staying compact on mobile breakpoints.
  - Expand the `TokenMeter` popover ledger to show session cost (`~৳...` / `$...`), all-time estimated cost, and a transparent note explaining the rate assumptions.

### 3. Script Ratings & Feedback — Phase 3 (`apps/api` & `apps/web`)
- [x] **Pre-generate `log_id` & Expose to Client (`apps/api/main.py`, `audit.py`)**
  - Generate `log_id` before Stage 1 runs and pass it into `log_generation_task` so SSE `done` events include `log_id` (and JSON endpoints return `X-Log-Id`).
- [x] **Feedback Endpoint & Export Script (`apps/api`)**
  - Add `POST /feedback` writing idempotently to Firestore `script_feedback/{log_id}_{script_index}` with rating (`1 | -1`), constrained tags (`bland`, `sounds_like_an_ad`, `wrong_tone`, `too_long`, `weak_hook`, `unrealistic`, `wrong_language`, `great_hook`), optional comment, and `script_snapshot`.
  - Track implicit quality signals (copy, save, regenerate counts) without blocking UI actions.
  - Add `apps/api/scripts/export_feedback.py` to export rated scripts to JSONL for future evals/few-shots.
- [x] **Frontend Rating Controls (`ScriptCard.tsx`, `ResultsView.tsx`)**
  - Add non-blocking thumbs up/down buttons and optional tag chips after thumbs-down on each script card.

### 4. Wire `POST /regenerate/section` SSE Streaming in Frontend (`apps/web`)
- [x] **Progressive Stale Regeneration (`useRegenerate.ts`, `ResultsView.tsx`)**
  - Replace the `Promise.all` `/regenerate/script` loop in `handleRegenerateStale` with `POST /regenerate/section` SSE streaming so regenerated segments/scripts appear progressively as each completes.

### 5. Offline Claim Verification Eval Check (Phase 5c Eval-Only)
- [ ] **Eval Script / Run (`apps/api/evals/`)** *(Offline script `claim_check.py`, 10 unit tests, and `--mock` run on `phase5_ugc/results.jsonl` completed: 61/99 supported, 38/99 unsupported, 0 contradicted; live Vertex AI Gemini run skipped pending `GOOGLE_CLOUD_PROJECT`/credentials and network access)*
  - Run an offline claim-verification pass on saved eval outputs (e.g., `phase5_ugc`) to measure real unsupported-claim rate before deciding whether runtime verification is warranted.

### 6. Minor Backlog & Polish
- [ ] **Demo Video URL (`AccessGateModal.tsx`)**: Replace placeholder/TODO if the final demo video URL is provided. *(Pending: final demo video URL not yet provided; `DEMO_VIDEO_URL` remains unset)*
- [x] **Verification**:
  - `bun run --cwd packages/api-types gen` (after any backend schema changes) — in sync (`0` diff)
  - `apps/api/.venv/bin/python3 -m pytest apps/api/tests/` — `86 passed` (`3` pre-existing Starlette deprecation warnings)
  - `bun run --cwd apps/web build` and `bun run --cwd apps/web lint` — `build` passed; `lint` passed with `0` errors (`2` pre-existing `AngleChips.tsx` warnings)
