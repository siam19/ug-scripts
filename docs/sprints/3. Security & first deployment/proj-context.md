# Project Context & AI Agent Reference Manual

> **Document Location**: `docs/sprints/3. Security & first deployment/proj-context.md`  
> **Target Audience**: AI Agents, Pair Programmers, and Developers entering Sprint 3  
> **Last Updated**: 2026-11-11 (Post-Sprint 2 completion)

---

## 1. What This App Does

**UG-Scripts** is an AI-powered User-Generated Content (UGC) video ad script generation platform designed for direct-to-consumer (D2C) brands, creators, and performance marketers creating short-form ads (TikTok, Instagram Reels, YouTube Shorts).

### Core Features & Workflow

1. **Multimodal Extraction (Stage 1)**:
   - The user inputs product name, category, description, target market (e.g. Bangladesh, US), language (`en` or `bn`), and uploads a product photo (JPEG, PNG, WebP up to 5 MB).
   - Gemini on Vertex AI analyzes the image (reading packaging, claims, ingredients, color cues) combined with metadata.
   - It outputs 5–8 concrete, verifiable **product facts** and 3 distinct **customer segment personas** (name, demographics/situation, pain point in their own words, active platforms).

2. **Parallelized Script Generation (Stage 2)**:
   - Three customized video scripts (one for each customer segment) are generated concurrently.
   - Scripts are optimized for 20–35 seconds spoken length (~60–90 words) and follow short-form UGC ad architecture:
     - **Hook** (first 3 seconds, scroll-stopper) with specific hook styles (curiosity question, problem callout, demo / before-after).
     - **Concept** lines (delivering core value proposition and social proof).
     - **Call to Action (CTA)** (direct, single conversion action).
   - Each script includes exactly 3 **marketing rationale techniques** ("Why this script should work") that cite specific contiguous line IDs explaining why that technique converts that segment.

3. **Granular In-Place Interactivity & Regeneration (Sprint 2)**:
   - **Fact Management**: Users can edit, delete, or add facts dynamically without re-uploading the product image. Content-hash tracking alerts the user via a `StaleBar` when scripts are based on outdated facts.
   - **Segment Regeneration (`POST /regenerate/segment`)**: Replace any single customer persona with a fresh angle while guaranteeing uniqueness against the other active segments.
   - **Full Script Rewrite (`POST /regenerate/script`)**: Regenerate an entire script for an edited or replaced segment.
   - **Reason Line-Group Rewriting (`POST /regenerate/reason-lines`)**: Clicking the refresh icon on a technique card rewrites only the lines cited by that rationale while preserving surrounding narrative flow. Replaced lines are wrapped in versioned group nodes.
   - **Single-Line Rephrasing (`POST /regenerate/line/rephrase`)**: Rephrase individual sentences across 4 distinct tones (`punchy`, `casual`, `authentic`, `direct`).
   - **Single-Line Regeneration (`POST /regenerate/line/regenerate`)**: Replace an individual line with a completely new angle matching its kind (`hook`, `concept`, `cta`).
   - **Interactive Line Editing**: Click to edit any line with inline text editing, live word/duration calculation, `Enter` to save, `Shift+Enter` for newlines, `Escape` to cancel, and click-outside line deselection.
   - **Hierarchical History Tree & Version Rail**: Complete non-destructive versioning supporting undo, redo, and version stepping across single lines, reason groups, and full script revisions.
   - **Saved Scripts Drawer**: Bookmark and inspect favorite script versions persisted in browser `localStorage`.

4. **Language Policy & Strict Partitioning**:
   - **Script Dialogue Lines**: Generated strictly in the selected language (`en` or `bn` - natural spoken Bengali script `বাংলা`).
   - **Personas, Facts, and Rationale**: Strictly kept in **English** across all languages, preserving marketing terminology clarity.

5. **Dual-Layer Anti-Spam & Rate Limiting**:
   - Client-side 1.2s burst debounce and 12 req/min sliding window with instant toast feedback.
   - Backend in-memory sliding-window limiter enforcing 15 req/min returning HTTP 429 (`Retry-After`).

---

## 2. System Architecture & Tech Stack

```
┌─────────────────────────────────────────────────────────────┐
│                      Monorepo (Bun)                         │
└─────────────────────────────────────────────────────────────┘
          │                                     │
          ▼                                     ▼
┌──────────────────┐                  ┌──────────────────┐
│    apps/web      │  HTTP / SSE      │    apps/api      │
│  React 19 + Vite │ ───────────────> │     FastAPI      │
│  TypeScript 5.9  │                  │  Python 3.12+    │
└──────────────────┘                  └──────────────────┘
          │                                     │
          │         ┌──────────────────┐        │
          └────────>│packages/api-types│<───────┘
                    │ OpenAPI TS Types │
                    └──────────────────┘
```

- **Monorepo Manager**: Bun Workspaces (`package.json`)
- **Backend (`apps/api`)**:
  - Framework: FastAPI + Uvicorn + Pydantic v2
  - AI Engine: `google-genai` SDK on Vertex AI (`gemini-2.5-flash`)
  - Streaming: Server-Sent Events (`StreamingResponse`, `text/event-stream`)
  - Testing: `pytest`, `pytest-asyncio`, `anyio` (28/28 tests passing)
- **Frontend (`apps/web`)**:
  - UI Library: React 19 + TypeScript (strict)
  - Bundler: Vite 8
  - Icons: `@tabler/icons-react`
  - Linter: `oxlint` (0 errors, 0 warnings across 29 files)
  - Styling: Pure CSS design system tokens (`App.css`, `index.css`) with custom typography:
    - Display: *Bricolage Grotesque*, *Hind Siliguri*
    - Body: *Hanken Grotesk*, *Hind Siliguri*
- **Shared (`packages/api-types`)**:
  - Auto-generated TypeScript interfaces derived directly from FastAPI's OpenAPI JSON specification (`openapi-typescript`).

---

## 3. Directory Structure

```
ug-script-writer/
├── package.json                         # Bun workspace root configuration
├── apps/
│   ├── api/                             # FastAPI Backend Service
│   │   ├── Dockerfile                   # Backend Docker container definition
│   │   ├── main.py                      # FastAPI app, endpoints, Vertex AI integration
│   │   ├── schemas.py                   # Pydantic v2 request/response models
│   │   ├── prompts.py                   # LLM prompt templates and language blocks
│   │   ├── rate_limiter.py              # In-memory sliding-window rate limiter (15 req/min)
│   │   ├── openapi.json                 # Exported OpenAPI schema
│   │   ├── requirements.txt             # Python dependencies
│   │   ├── pytest.ini                   # Pytest async & runner configuration
│   │   └── tests/                       # Automated backend test suite
│   │       ├── conftest.py              # Pytest fixtures and test client setup
│   │       ├── test_health.py           # Health check endpoint tests
│   │       ├── test_validation.py       # Payload and image validation tests
│   │       ├── test_generate.py         # Full & streaming generation tests
│   │       ├── test_regenerate.py       # Granular regeneration endpoint tests
│   │       └── test_rate_limiter.py     # Unit & integration rate limiter tests
│   │
│   └── web/                             # React 19 Frontend Application
│       ├── index.html                   # HTML entry point with web font imports
│       ├── package.json                 # Web dependencies and scripts
│       ├── vite.config.ts               # Vite configuration
│       ├── tsconfig.json                # TypeScript project configuration
│       └── src/
│           ├── main.tsx                 # React DOM mount point
│           ├── App.tsx                  # Root application component
│           ├── App.css                  # Core component styles and theme variables
│           ├── index.css                # Base reset and font definitions
│           ├── components/              # UI components
│           │   ├── ProductForm.tsx      # Step 1 input form (file upload, market, language)
│           │   ├── ResultsView.tsx      # Main workbench coordinating facts, segments, script
│           │   ├── FactChips.tsx        # Editable/removable fact chips + additions
│           │   ├── SegmentTab.tsx       # Demographic persona tabs
│           │   ├── SegmentCard.tsx      # Persona card with refresh/edit actions
│           │   ├── ScriptCard.tsx       # Script panel, word count, copy action, click-outside
│           │   ├── ScriptLine.tsx       # Timestamped line with inline editing & keybindings
│           │   ├── LineToolbar.tsx      # Floating actions for rephrase, regenerate, delete
│           │   ├── VersionRail.tsx      # Side rail chevrons for stepping through history
│           │   ├── ReasonList.tsx       # "Why this script should work" technique cards
│           │   ├── ReasonItem.tsx       # Individual technique card with refresh action
│           │   ├── StaleBar.tsx         # Notification banner when facts or segments change
│           │   ├── SavedScriptsDrawer.tsx # Slide-out drawer for saved script bookmarks
│           │   ├── ToastHost.tsx        # Floating alert notifications with dismiss & undo
│           │   ├── LoadingState.tsx     # Full-page skeleton during initial generation
│           │   └── ErrorBanner.tsx      # Global error display banner
│           ├── hooks/                   # Custom React hooks
│           │   ├── useGenerateScript.ts # Handles initial full/streaming generation
│           │   └── useRegenerate.ts     # Typed HTTP API client for all granular regenerations
│           ├── state/                   # State engine & tree algorithms
│           │   ├── types.ts             # Workspace, ScriptDoc, Node, and Selection types
│           │   ├── workspace.ts         # Immutable workspace reducer & action handlers
│           │   ├── script-tree.ts       # Version tree navigation, coverage resolver, views
│           │   ├── hash.ts              # Content hashing for change detection
│           │   ├── keyboard.ts          # OS modifier key helpers
│           │   ├── saved-scripts.ts     # LocalStorage persistence for saved scripts
│           │   └── uid.ts               # Cryptographically safe unique ID generator
│           └── types/
│               └── form.ts              # Form value structures & validation defaults
│
├── packages/
│   └── api-types/                       # Shared API Type Definitions
│       ├── package.json                 # Type package configuration
│       ├── tsconfig.json                # TypeScript config
│       └── src/
│           ├── index.ts                 # Clean exported type aliases
│           └── schema.d.ts              # Generated OpenAPI TypeScript definitions
│
└── docs/
    └── sprints/
        ├── 1. Setup and Basic features/
        ├── 2. Refining Script Generation & Regenerations/
        │   ├── api-requirements-sprint-2.md
        │   └── log.md                   # Comprehensive Sprint 2 implementation log
        └── 3. Security & first deployment/
            ├── prompt.md                # Sprint 3 kickoff notes
            └── proj-context.md          # THIS FILE
```

---

## 4. Key Data Models

### 4.1 Backend Schemas (`apps/api/schemas.py`)

```python
class Segment(BaseModel):
    name: str = Field(..., description="Distinct persona title")
    who: str = Field(..., description="Demographics, daily context, and life situation")
    pain_point: str = Field(..., description="Core frustration or desire in their own words")
    platforms: list[str] = Field(..., description="Active short-form video platforms")

class Line(BaseModel):
    id: int = Field(..., description="1-based index")
    kind: Literal["hook", "concept", "cta"]
    text: str = Field(..., description="Spoken dialogue line")

class Reason(BaseModel):
    title: str = Field(..., description="Marketing technique name in English")
    why: str = Field(..., description="Why this works for the segment in English")
    line_ids: list[int] = Field(..., description="Contiguous line indices demonstrating this")

class Script(BaseModel):
    segment: str = Field(..., description="Segment persona name")
    hook: str = Field(..., description="Hook style used")
    lines: list[Line] = Field(..., min_length=3, max_length=6)
    reasons: list[Reason] = Field(..., min_length=3, max_length=3)

class GenerateResponse(BaseModel):
    product_facts: list[str]
    segments: list[Segment]
    scripts: list[Script]
```

### 4.2 Granular Regeneration Models (`apps/api/schemas.py`)

```python
class SegmentRegenerateRequest(BaseModel):
    name: str
    category: str
    market: str
    language: Literal["en", "bn"]
    facts: list[str]
    current_segment: Segment
    existing_segment_names: list[str] = []

class ScriptRewriteRequest(BaseModel):
    name: str
    category: str
    market: str
    language: Literal["en", "bn"]
    facts: list[str]
    segment: Segment
    hook_style: str = "curiosity question"

class ReasonLinesRewriteRequest(BaseModel):
    name: str
    market: str
    language: Literal["en", "bn"]
    facts: list[str]
    segment: Segment
    full_script: list[ScriptLineContext]
    target_line_ids: list[int]
    reason: ReasonInfo

class LineRephraseRequest(BaseModel):
    name: str
    market: str
    language: Literal["en", "bn"]
    facts: list[str]
    segment: Segment
    script_context: list[ScriptLineContext]
    line_id: int
    current_text: str
    kind: Literal["hook", "concept", "cta"]
    avoid_tones: list[str] = []
```

### 4.3 Frontend Versioned State Tree (`apps/web/src/state/types.ts`)

```typescript
export interface LineVersion {
  id: Uid;
  label: 'Original' | 'Edited' | 'Rephrased' | 'Regenerated' | 'Deleted';
  detail?: string;
  text: string | null; // null represents deleted tombstone
}

export interface LineNode {
  type: 'line';
  uid: Uid;
  kind: 'hook' | 'concept' | 'cta';
  versions: LineVersion[];
  cursor: number;
  pending?: 'rephrase' | 'regenerate';
}

export interface GroupNode {
  type: 'group';
  uid: Uid;
  versions: GroupVersion[];
  cursor: number;
  pending?: boolean;
}

export type ScriptNode = LineNode | GroupNode;

export interface ReasonItem {
  uid: Uid;
  title: string;
  why: string;
  cites: Uid[]; // LineNode uids covered by this reason
  pending?: boolean;
}

export interface Workspace {
  meta: { name: string; market: string; language: 'en' | 'bn' };
  facts: FactItem[];
  slots: SegmentSlot[];
  activeSlotId: Uid;
  selection:
    | { kind: 'none' }
    | { kind: 'reason'; reasonUid: Uid }
    | { kind: 'line'; uid: Uid };
}
```

---

## 5. Critical Code Snippets

### 5.1 Backend: Gemini Client with Vertex AI Structured Outputs (`apps/api/main.py`)

```python
def get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_CLOUD_PROJECT environment variable is not configured.",
            )
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        _genai_client = genai.Client(vertexai=True, project=project, location=location)
    return _genai_client

async def ask_gemini(prompt: str, schema: type[Any], parts: Sequence[Any] = (), max_retries: int = 1) -> Any:
    client = get_genai_client()
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

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
            if response.parsed is not None:
                return response.parsed
            raise ValueError("Model response did not contain parsed structured data.")
        except Exception as e:
            if attempt == max_retries:
                raise HTTPException(status_code=502, detail=f"Vertex AI generation error: {str(e)}")
            await asyncio.sleep(1)
```

### 5.2 Backend: In-Memory Sliding Window Rate Limiter (`apps/api/rate_limiter.py`)

```python
class SlidingWindowRateLimiter:
    """Thread-safe sliding-window log rate limiter."""
    def __init__(self, max_requests: int = 15, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def hit(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            history = self._requests[key]
            self._requests[key] = [t for t in history if t > cutoff]
            history = self._requests[key]

            if len(history) >= self.max_requests:
                earliest = history[0]
                retry_after = max(1, int(self.window_seconds - (now - earliest)))
                return False, retry_after

            history.append(now)
            return True, 0
```

### 5.3 Backend: Language Policy Enforcement (`apps/api/prompts.py`)

```python
LANGUAGE_BLOCK = """LANGUAGE INSTRUCTION:
- ONLY the spoken video script dialogue lines (hook, concept, cta) must be written in {language_name} ({language_code}).
- Customer segments (name, who, pain_point, platforms), product facts, and marketing rationale (reasons: title, why) MUST ALWAYS be written in English.
- If language is 'Bangla' (bn):
  * Spoken video script dialogue lines (hook, concept, cta) must be written in proper, natural Bengali script (বাংলা).
  * Write dialogue in conversational, authentic spoken Bangla used by UGC creators in Bangladesh.
  * DO NOT transliterate English into Bengali script (no "Banglish").
  * DO NOT output English sentences for spoken dialogue lines.
  * Customer segments, marketing reasons, and platform names MUST remain strictly in English.
- If language is 'English' (en):
  * Use crisp, natural, conversational spoken English for script dialogue lines.
"""
```

### 5.4 Frontend: Non-Destructive Reason Grouping & Citation Repair (`apps/web/src/state/workspace.ts`)

```typescript
case 'REWRITE_REASON_SUCCESS': {
  const slot = state.slots.find((s) => s.id === state.activeSlotId);
  const doc = slot?.script;
  if (!doc) return state;

  const rev = doc.revisions[doc.cursor];
  const reason = rev?.reasons.find((r) => r.uid === action.reasonUid);
  if (!reason) return state;

  const cover = resolveVisibleCover(doc, reason.cites);
  if (!cover) return state;

  const newNodes: LineNode[] = action.newLines.map((nl) => ({
    type: 'line',
    uid: generateUid(),
    kind: nl.kind,
    cursor: 0,
    versions: [{ id: generateUid(), label: 'Original', text: nl.text }],
  }));

  const visibleUids = cover.coverNodes.flatMap(collectVisibleUids);
  const newUids = newNodes.map((n) => n.uid);
  
  // Augment cites on all affected reasons so none become orphans ("All cited lines were removed")
  const updatedReasons = rev.reasons.map((r) => {
    const touchesCover = r.uid === action.reasonUid || r.cites.some((id) => visibleUids.includes(id));
    return touchesCover
      ? {
          ...r,
          cites: Array.from(new Set([...r.cites, ...newUids])),
          pending: r.uid === action.reasonUid ? false : r.pending,
        }
      : r;
  });

  // Wrap cover nodes into a new GroupNode or append a new GroupVersion
  // ...
}
```

### 5.5 Frontend: Line Editing with Dedicated Snapshot Ref & Keybindings (`apps/web/src/components/ScriptLine.tsx`)

```typescript
export function ScriptLine(p: Props) {
  const { line, selected } = p;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(line.text);
  const initialText = useRef(line.text); // Prevents draft override bug

  function startEdit() {
    initialText.current = line.text;
    setDraft(line.text);
    setEditing(true);
  }

  function finishEdit(save: boolean) {
    const next = draft.trim();
    if (save && next && next !== initialText.current) {
      p.onEdit(line.uid, next);
    }
    setEditing(false);
    p.onDraft?.(line.uid, null);
  }

  function handleAreaKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.nativeEvent.isComposing) return; // IME safe
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      finishEdit(false);
    } else if (e.key === 'Enter') {
      if (e.shiftKey) return; // Shift+Enter allows newline
      e.preventDefault();
      finishEdit(true);      // Enter saves
    }
  }
  // ...
}
```

### 5.6 Frontend: Click-Outside Deselection (`apps/web/src/components/ScriptCard.tsx`)

```typescript
// Deselect line when clicking outside script-card
useEffect(() => {
  if (!selectedLineUid) return;

  function handlePointerDown(e: PointerEvent) {
    const card = cardRef.current;
    if (!card) return;
    if (e.target instanceof Node && card.contains(e.target)) {
      return;
    }
    onLineSelect(null);
  }

  document.addEventListener('pointerdown', handlePointerDown);
  return () => document.removeEventListener('pointerdown', handlePointerDown);
}, [selectedLineUid, onLineSelect]);
```

---

## 6. Environment Variables & Configuration

### Backend (`apps/api/.env`)
| Variable | Description | Example / Default |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID for Vertex AI | `ugstar-94b38dd789aa` |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI regional endpoint | `us-central1` or `global` |
| `GEMINI_MODEL` | Gemini Foundation Model | `gemini-2.5-flash` |
| `API_KEY` | Secret bearer key required in `X-API-Key` | Set in deployment secrets |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:5173,https://your-domain.com` |

### Frontend (`apps/web/.env`)
| Variable | Description | Example / Default |
|---|---|---|
| `VITE_API_URL` | Backend URL for API calls | `http://localhost:8000` |
| `VITE_API_KEY` | API Key passed in `X-API-Key` header | Matches backend `API_KEY` |

---

## 7. Developer & Build Commands

All commands can be run from the root using Bun:

```bash
# Start frontend development server (Vite on http://localhost:5173)
bun dev:web

# Build frontend production bundle (Typecheck + Vite build)
bun build:web

# Run frontend linter (oxlint)
bun lint:web

# Regenerate TypeScript types from backend OpenAPI JSON
bun gen:types

# Run backend Python test suite
bun test:api
# Or directly inside apps/api:
# cd apps/api && .venv/bin/pytest -v
```

---

## 8. Handoff Notes & Sprint 3 Focus Areas

1. **Security & Deployment Target**:
   - Sprint 3 focuses on hardening endpoints, reviewing secret handling, configuring production CORS, and setting up Docker / Cloud Run deployment.
   - `apps/api/rate_limiter.py` is currently in-memory. If scaling to multiple Uvicorn workers or serverless instances, consider Redis or Cloud Armor rate limiting.
   
2. **Pending UI Bug Noted in Sprint 3 Kickoff**:
   - In `docs/sprints/3. Security & first deployment/prompt.md`:
     `Clicking outside of workbench doesn't deselect any reason-item. It however deselects selected lines when clicked outside.`
   - In `ScriptCard.tsx`, clicking outside deselects lines, but `ResultsView.tsx` does not yet have an equivalent click-outside listener for the `ReasonList` panel.
