# Frontend Developer Guide: Script Assistant Web App

This guide is for frontend developers implementing the React application for the **Script Assistant** project. It specifies the monorepo structure, shared TypeScript types, backend API contract, expected UI components, and code conventions.

---

## 1. Project Overview & Architecture

Script Assistant is a Billo-style AI UGC video ad script writer:
1. **User Input**: Product name, description, category, target market, script language (`en` or `bn`), and a product image.
2. **Backend Execution**: A FastAPI service (`apps/api`) orchestrates two stages of Gemini 3.5 Flash on Vertex AI (Stage 1: multi-modal extraction of verifiable facts and 3 customer segments; Stage 2: parallel generation of 3 UGC scripts customized per segment with performance marketing rationales).
3. **Frontend Output**: Displays verified facts, 3 customer segments, and 3 production-ready scripts with interactive rationale highlighting.
4. **Latency Expectation**: 10–20 seconds end-to-end.

---

## 2. Monorepo Setup & Workspace Commands

The project uses **Bun workspaces**.

```bash
# Start Vite development server (runs on http://localhost:5173)
bun run dev:web

# Typecheck and build the web app for production
bun run build:web

# Run linter (oxlint)
bun run lint:web
```

---

## 3. Directory Layout & Where to Write Files

All frontend code belongs in [`apps/web/src/`](file:///home/bast0k/projects/ug-script-writer/apps/web/src).

Recommended structure:

```
apps/web/
├── .env.local                          # Local environment variables
├── index.html                          # HTML entry point
├── package.json                        # App dependencies & scripts
├── tsconfig.json                       # TypeScript config
├── vite.config.ts                      # Vite configuration
└── src/
    ├── main.tsx                        # React DOM root entry
    ├── App.tsx                         # Main page layout & state orchestrator
    ├── index.css                       # Global styles
    ├── App.css                         # App-specific layout styles
    ├── components/
    │   ├── ProductForm.tsx             # Input form with image upload & validations
    │   ├── LoadingState.tsx            # Animated 10-20s loading feedback
    │   ├── ResultsView.tsx             # Parent results view (facts chips + segment tabs)
    │   ├── SegmentCard.tsx             # Persona details (who, pain points, platforms)
    │   ├── ScriptCard.tsx              # Numbered script lines with kind badges & copy button
    │   ├── ReasonList.tsx              # 3 persuasion techniques with line-highlighting
    │   └── ErrorBanner.tsx             # Friendly error alerts with retry action
    ├── hooks/
    │   └── useGenerateScript.ts        # API communication & loading/error state hook
    └── types/                          # (Optional) Frontend-only UI state types
```

---

## 4. Shared API Types (`api-types`)

The monorepo contains a shared package called `api-types`, auto-generated from FastAPI's OpenAPI specification. **Do not handwrite duplicate API types.**

Import directly from `'api-types'`:

```typescript
import type {
  GenerateResponse, // Top-level API response payload
  Segment,          // Customer persona segment
  Script,           // Complete script with lines and reasons
  Line,             // Single spoken dialogue line
  Reason,           // Marketing technique rationale
  LineKind,         // 'hook' | 'concept' | 'cta'
} from 'api-types';
```

### Type Definitions Summary

```typescript
type LineKind = 'hook' | 'concept' | 'cta';

interface Line {
  id: number;       // 1-based sequential line number
  kind: LineKind;   // Role of this line in the video structure
  text: string;     // Spoken voiceover / creator dialogue
}

interface Reason {
  title: string;     // Technique name (e.g., 'Curiosity Question Hook')
  why: string;       // Segment-specific rationale
  line_ids: number[];// Array of line IDs that demonstrate this technique
}

interface Script {
  segment: string;   // Segment name this script was written for
  lines: Line[];     // Ordered sequence of lines
  reasons: Reason[]; // Exactly 3 rationale reasons
}

interface Segment {
  name: string;        // Segment title (e.g., 'Exhausted Working Parents')
  who: string;         // Demographics, daily context, life situation
  pain_point: string;  // Core frustration in customer's own words
  platforms: string[]; // ['TikTok', 'Instagram Reels', 'YouTube Shorts']
}

interface GenerateResponse {
  facts: string[];     // 5 to 8 concrete verifiable product facts
  segments: Segment[]; // Exactly 3 segments
  scripts: Script[];   // Exactly 3 scripts (same order as segments)
}
```

---

## 5. API Contract & Integration

### Environment Variables
Variables are loaded in [`apps/web/.env.local`](file:///home/bast0k/projects/ug-script-writer/apps/web/.env.local):

```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=mZqnDJo6p4z2qyGemeFzuV0n3-T1hU3YIZeolX-CxFM
```

Access them in code via `import.meta.env.VITE_API_URL` and `import.meta.env.VITE_API_KEY`.

### Request Specification

* **Endpoint**: `POST ${import.meta.env.VITE_API_URL}/generate`
* **Content-Type**: `multipart/form-data` (allow browser to set boundary automatically)
* **Headers**: `X-API-Key: ${import.meta.env.VITE_API_KEY}`

#### FormData Fields:
| Field | Type | Rules | Example |
| :--- | :--- | :--- | :--- |
| `name` | string | Non-empty | `"GlowHydrate Serum"` |
| `description` | string | Detailed product context | `"Hyaluronic acid hydrating serum..."` |
| `category` | string | Product category | `"Skincare"` |
| `market` | string | 1–60 chars, free text | `"Bangladesh"` (default) |
| `language` | string | `'en'` or `'bn'` | `'en'` |
| `image` | File | JPEG, PNG, or WebP; max 5 MB | `product.png` |

#### Fetch Implementation Example:

```typescript
const formData = new FormData();
formData.append('name', name);
formData.append('description', description);
formData.append('category', category);
formData.append('market', market);
formData.append('language', language);
formData.append('image', imageFile);

const response = await fetch(`${import.meta.env.VITE_API_URL}/generate`, {
  method: 'POST',
  headers: {
    'X-API-Key': import.meta.env.VITE_API_KEY,
  },
  body: formData,
});

if (!response.ok) {
  const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
  throw new Error(errorData.detail || `Server responded with status ${response.status}`);
}

const data: GenerateResponse = await response.json();
```

### HTTP Error Statuses to Handle:
* `401 Unauthorized`: Bad or missing API key.
* `413 Payload Too Large`: Image file exceeds 5 MB.
* `415 Unsupported Media Type`: Image is not JPEG, PNG, or WebP.
* `422 Unprocessable Entity`: Validation failure (empty field, market > 60 chars, invalid language).
* `502 Bad Gateway` / Network error: Upstream Gemini generation timeout or connection failure.

---

## 6. Required Screens & Component Details

### 1. `ProductForm`
* **Fields**:
  * Product Name (`<input type="text">`, required).
  * Category (`<select>` with common options like Skincare, Tech/Gadgets, Fashion, Food & Bev, Home & Living, or customizable input).
  * Market (`<input type="text">`, default value `"Bangladesh"`, max 60 characters).
  * Language (`Toggle` or `Radio` between **English (`en`)** and **Bangla (`bn`)**).
  * Product Description (`<textarea>`, required, 2–4 lines minimum).
  * Image Upload: Drag & drop zone with file picker, instant thumbnail preview, file remove button, and client-side validation (blocks files > 5 MB or wrong format before sending).
* **Submit Button**: Clear CTA (e.g., "Generate UGC Scripts"), disabled when submitting or when required fields are missing.

### 2. `LoadingState`
* Shown during the 10–20 second pipeline execution.
* Do not freeze the page. Display a progress indicator or spinner.
* Provide reassuring step indicators (e.g., "Stage 1: Analyzing image packaging and verifying facts...", "Stage 2: Writing 3 high-converting creator scripts...").

### 3. `ResultsView`
* **Facts Section**: Displays extracted `product_facts` as badges or tag chips at the top.
* **Segment Tabs/Selector**: 3 tabs allowing the user to switch between the 3 customer segments.
* **Persistence**: Retain the generated results in state so toggling between segments does not trigger re-fetching.

### 4. `SegmentCard`
* Displays segment persona information:
  * Segment Name
  * Target Demographics (`who`)
  * Pain Point (`pain_point`) in quotation/callout format
  * Recommended Short-Form Platforms (`platforms` as badges, e.g., TikTok, Reels, Shorts)

### 5. `ScriptCard`
* Displays the video ad script for the currently selected segment.
* Lists script lines in sequential order by `line.id`.
* **Kind Badges**:
  * `hook` (0–3s scroll-stopper): Highlight with an accent color (e.g. amber/orange badge).
  * `concept` (body/core value): Neutral/brand color (e.g. blue/slate badge).
  * `cta` (call to action): Distinct accent (e.g. emerald/green badge).
* **Copy Button**: "Copy Script" button that copies the clean spoken dialogue to the user's clipboard and displays a brief "Copied!" confirmation.

### 6. `ReasonList` & Interactive Line Highlighting
* Displays the 3 persuasion techniques (`reasons`) for the active script.
* **Bi-directional Highlighting**:
  * When a user hovers or clicks a **Reason card**, visually highlight all matching `Line` items in the script whose IDs are in `reason.line_ids`.
  * When a user hovers a **Script Line**, highlight the specific **Reason cards** that reference that line's ID.

### 7. `ErrorBanner`
* Informative alert box displaying clean, friendly error messages for 401, 413, 415, 422, or network timeouts.
* Include a "Retry" button that preserves the already-entered form inputs so the user doesn't have to retype everything.

---

## 7. Submission & Integration Format

When returning frontend code, please deliver:
1. **Modular Components**: Place components inside `apps/web/src/components/`, hooks in `apps/web/src/hooks/`, and root integration in `apps/web/src/App.tsx`.
2. **File Paths**: State the relative path for each file clearly at the top (e.g. `// apps/web/src/components/ProductForm.tsx`).
3. **Styling**: Standard CSS or CSS modules in `App.css` / `index.css`, with clean class names and mobile-friendly responsive layout.
