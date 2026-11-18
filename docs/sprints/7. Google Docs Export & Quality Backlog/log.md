# Sprint 7 Changelog: Google Docs Export, Cost Meter & Quality Backlog

**Sprint Objective**: Integrate 1-click Export to Google Docs, display estimated BDT session cost in the masthead `TokenMeter`, and implement prioritized quality/UX backlog items (Phase 3 ratings & feedback, `/regenerate/section` SSE streaming, offline claim verification check).

---

## Log Entry 1: Sprint 7 Initialization & Planning

**Date**: 2026-11-18  
**Status**: Planned

### Summary
- Audited deferred backlog items from Sprints 2–4 and evaluated Sprint 4 Phase 5a (`ScriptPlan` CoT) against Phase 2 (`phase2_grounding`):
  - `phase5_ugc` achieved `100.0%` hard-rules pass rate (up from `88.9%`), `0` banned cliché hits (down from `2`), `1.0` Bengali script ratio, and `17.8%` lower average tokens per product (`21,614` vs `26,301`).
  - Decided **against** adding Phase 5b (an extra sequential angle-brief call before Stage 2).
- Scoped out Visual Scenes/Storyboarding (Phase 6), distributed rate limiting, admin dashboard, and per-code token quotas.
- Created [`goals.md`](file:///home/bast0k/projects/ug-script-writer/docs/sprints/7.%20Google%20Docs%20Export%20&%20Quality%20Backlog/goals.md) to track implementation across Google Docs export, BDT cost meter updates, and remaining backlog items.


---

## Log Entry 2: Sprint 7 Implementation & Verification

**Date**: 2026-11-18  
**Status**: Implemented & Verified (live Vertex AI claim-check and final demo video URL pending external inputs)

### Summary of Changes

1. **Backend `log_id`, Public OAuth Config & Phase 3 Script Feedback (`apps/api/`, `packages/api-types/`)**
   - Pre-generated `log_id` (UUID) before LLM execution across `/generate`, `/generate-stream`, and `/regenerate/*` endpoints in [`apps/api/main.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/main.py) and passed it into [`log_generation_task`](file:///home/bast0k/projects/ug-script-writer/apps/api/audit.py#L19-L38); exposed `X-Log-Id` in CORS `expose_headers` and SSE `done` events.
   - Added `GET /auth/config` (`AuthConfigResponse`) returning `VITE_GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_ID` without ever reading or exposing any OAuth client secret.
   - Added rate-limited, auth-protected `POST /feedback` and `POST /feedback/signal` endpoints (`feedback_limiter` in [`apps/api/rate_limiter.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/rate_limiter.py), Pydantic schemas in [`apps/api/schemas.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/schemas.py)) writing idempotently to Firestore `script_feedback/{log_id}_{script_index}` with `merge=True`, atomic `firestore.Increment(1)` for `copy`/`save`/`regenerate` signals, and graceful offline fallback.
   - Added [`apps/api/scripts/export_feedback.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/scripts/export_feedback.py) for UTF-8 JSONL export and [`apps/api/tests/test_feedback.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/tests/test_feedback.py) (14 tests).
   - Regenerated `apps/api/openapi.json` and [`packages/api-types/src/`](file:///home/bast0k/projects/ug-script-writer/packages/api-types/src/index.ts).

2. **Google Docs Export, BDT Cost Meter, BrandLogo & Frontend Wiring (`apps/web/`)**
   - **Google Docs Export**: Implemented on-demand GIS OAuth2 (`https://www.googleapis.com/auth/drive.file`), `GET /auth/config` fallback, UTF-8/Bengali-safe HTML formatter, Drive v3 multipart upload, "Open Doc" link/toast, and `.md` download fallback across [`googleDocs.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/lib/googleDocs.ts), [`useGoogleDocsExport.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/hooks/useGoogleDocsExport.ts), [`ScriptCard.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptCard.tsx), and [`SavedScriptsDrawer.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/SavedScriptsDrawer.tsx). Verified zero references to `VITE_GOOGLE_CLIENT_SECRET` or any secret in `apps/web/src/`.
   - **BDT Cost Meter**: Added centralized Gemini Flash rate constants (`$0.15/1M` input, `$0.60/1M` output, blended `$0.285/1M`, `USD_TO_BDT = 122`) in [`pricing.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/state/pricing.ts), session/lifetime cost tracking in [`useTokenTracker.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/hooks/useTokenTracker.ts), and updated [`TokenMeter.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/TokenMeter.tsx) + [`App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css).
   - **Brand Logo**: Created [`BrandLogo.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/BrandLogo.tsx) from `docs/ug-scripts-logo-v1.svg` and replaced all `rec-dot` spans in `App.tsx`, `ProductForm.tsx`, and `ResultsView.tsx`.
   - **Feedback UI & Section SSE**: Added `logId` capture in [`useGenerateScript.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/hooks/useGenerateScript.ts) and [`useRegenerate.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/hooks/useRegenerate.ts) (plus `regenerateSectionStream`), [`useFeedback.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/hooks/useFeedback.ts), and [`FeedbackBar.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/FeedbackBar.tsx), wired into [`App.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.tsx), `ScriptCard.tsx`, and [`ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx).

3. **Offline Claim Verification Eval — Phase 5c (`apps/api/evals/`)**
   - Added [`apps/api/evals/claim_check.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/claim_check.py) (supporting dict/model/string facts, `--mock` bilingual heuristic, and live Vertex AI Gemini mode) and [`apps/api/tests/test_claim_check.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/tests/test_claim_check.py) (10 tests).
   - Generated mock report [`claim_check_report.md`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/results/phase5_ugc/claim_check_report.md) against `phase5_ugc/results.jsonl` (11 products, 33 scripts: 61/99 claims supported, 38 unsupported, 0 contradicted); live Vertex AI run skipped in sandbox without credentials/network.

### Verification Results (Integrated Main Workspace)
- **Backend Tests**: `apps/api/.venv/bin/python3 -m pytest apps/api/tests/` → **86 passed**, 3 pre-existing Starlette deprecation warnings in 49.22s (`test_feedback.py` and `test_claim_check.py` included).
- **API Types Sync**: `bun run --cwd packages/api-types gen` → succeeded with 0 diff against `apps/api/openapi.json` and `packages/api-types/src/schema.d.ts`.
- **Frontend Build**: `bun run --cwd apps/web build` (`tsc -b && vite build`) → succeeded (7,192 modules transformed in 1.11s).
- **Frontend Lint**: `bun run --cwd apps/web lint` (`oxlint`) → **0 errors**, 2 pre-existing warnings in `src/components/AngleChips.tsx`.
- **Security Scan**: `rg -n "SECRET|secret|CLIENT_SECRET" apps/web/src/` → **0 matches**.


---

## Log Entry 3: Google Docs & Markdown Export Formatting Refinement

**Date**: 2026-11-18  
**Status**: Implemented & Verified (`bun run --cwd apps/web build` & `lint` passing)

### Summary of Changes (`apps/web/src/lib/googleDocs.ts`)
- **Removed Clutter Sections**: Removed **Verified Facts**, **Creative Angles**, and **Marketing Rationales** from both [`buildGoogleDocHtml`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/lib/googleDocs.ts#L286-L398) and [`buildMarkdownDocument`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/lib/googleDocs.ts#L403-L441).
- **Streamlined Customer Segment Persona**: Kept **Segment**, **Who They Are**, and the **Pain Point** callout; removed **Recommended Platforms** and **Lead Angles**.
- **Clean Script Line Formatting**: Removed line numbering (`1.`, `2.`), role tags (`[HOOK]`, `[CONCEPT]`, `[CTA]`), and timestamps (`0:00`), keeping only **Speaker**, **Visual Direction**, and the spoken dialogue.
- **Google Docs Table-Based Aesthetics**: Replaced `<div>` cards and `<blockquote>` (whose borders/padding Google Docs' HTML importer strips) with structured `<table>` layouts featuring a `#2a5c45` accent left border, soft `#f4f7f5` header/label shading, clean row dividers, and generous cell padding for Product Info, Customer Segment Persona, and each script beat card.
- **Verification**: `bun run --cwd apps/web build` (`tsc -b && vite build`) passed in 1.30s; `bun run --cwd apps/web lint` (`oxlint`) passed with 0 errors (2 pre-existing warnings in `AngleChips.tsx`).

### Export Layout Iteration 2 (`apps/web/src/lib/googleDocs.ts`)
- Removed **Visual Appearance** (`productAppearance`) from the **Product Info** table and Markdown output.
- Removed outer boxes around spoken dialogue lines; retained a lightweight `#f4f7f5` callout box (`border: none; border-left: 2.5pt solid #2a5c45`) strictly for **Speaker** and **Visual Direction**.
- Restored clean numbered lines (`1.`, `2.`, …) directly beneath each direction box for readable dialogue delivery.
