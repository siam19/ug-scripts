# Sprint 2 Changelog: Refining Script Generation & Regenerations

**Sprint Objective**: Introduce granular customizability, in-place editing, lossless version history, and regeneration options across facts, customer segments, reasoning groups, and individual script lines.

---

## Log Entry: Frontend Implementation & Integration

**Date**: 2026-11-09  
**Status**: Completed & Verified (`tsc -b && vite build` & `oxlint` passing with 0 errors)

---

### 1. Dependencies & Package Additions

- **Installed `@base-ui/react` (v1.9.0)**:
  - Added headless, unstyled primitives for `Toolbar` and collision-flipping `Menu`.
  - Avoided Tailwind dependencies (`shadcn/ui` was rejected per sprint constraints).
  - Composed `<Toolbar.Button render={<Menu.Trigger />} />` for accessible roving focus and unified keyboard navigation.

---

### 2. State Architecture & Pure Engine (`apps/web/src/state/`)

Built a dedicated, testable state engine implementing the 5 core invariants from the design guide:
1. *The highlight is the scope* (actions apply strictly to what is currently lit).
2. *Nothing is destroyed* (lossless version arrays, deletions stored as tombstones).
3. *Stale is derived, never stored* (content hashing via `djb2`, no dirty flags to drift).
4. *Stale is a hatch, not a wall* (non-blocking passive badges and visual indicators).
5. *Identity is stable, numbers are derived* (stable UUIDs, render-time line numbering).

#### New Modules:
- **`src/state/types.ts`**:
  - Node hierarchy: `LineNode` (with `LineVersion[]`), `GroupNode` (with `GroupVersion[]`), and `ScriptDoc` (with `ScriptRevision[]`).
  - Slot tracking: `SegmentSlot` with `factsBasis`, `previous` segment for undo, and streaming status.
  - Selection states: `{ kind: 'none' } | { kind: 'reason'; reasonUid } | { kind: 'line'; uid }`.
- **`src/state/uid.ts`**:
  - `generateUid()` using `crypto.randomUUID()` with fallback for non-secure contexts (e.g. LAN testing).
- **`src/state/hash.ts`**:
  - Fast `djb2` string hashing algorithm.
  - `factsHash(facts)` and `segmentHash(segment)`.
  - Derived staleness helpers: `scriptStaleReasons(ws, slot)`, `slotNeedsRegen(ws, slot)`, and `scriptStaleMessage(reasons, replaced)`.
- **`src/state/script-tree.ts`**:
  - `getVisibleLineItems(doc)`: Traverses active versions and tombstones.
  - `getActiveLines(doc)`: Flattens visible non-deleted lines.
  - `resolveVisibleCover(doc, citedUids)`: Resolves overlapping reason citations and contiguous node spans by lifting cited UIDs to their lowest common ancestor.
  - `getActiveScope(ws)`: Derives whether chevrons and undo/redo operate on an active line, an active reason group, or the full script.
  - Word timing helpers: `countWords` and `formatTime` using `SECONDS_PER_WORD = 0.4`.
- **`src/state/workspace.ts`**:
  - Comprehensive reducer handling all mutations without destructive replacement:
    - Seeding from stream (`SEED_WORKSPACE`, `SCRIPT_READY`, `SCRIPT_ERROR`).
    - Fact operations (`EDIT_FACT`, `REMOVE_FACT`, `ADD_FACT`, `RESET_FACTS`).
    - Segment operations (`REPLACE_SEGMENT_START`, `REPLACE_SEGMENT_SUCCESS`, `REPLACE_SEGMENT_UNDO`, `EDIT_SEGMENT`).
    - Script operations (`REWRITE_SCRIPT_START`, `REWRITE_SCRIPT_SUCCESS`, `KEEP_SCRIPT_AS_IS`).
    - Line operations (`EDIT_LINE`, `REPHRASE_LINE`, `REGENERATE_LINE`, `DELETE_LINE`, `UNDO_LINE`, `REDO_LINE`).
    - Reason operations (`REWRITE_REASON_START`, `REWRITE_REASON_SUCCESS` with automatic group wrapping).
    - Scope stepping (`STEP_SCOPE` for chevrons).
- **`src/state/saved-scripts.ts`**:
  - `useSavedScripts()` hook backed by `localStorage` under `script-assistant:saved:v1`.
  - Snapshot hash generation and duplicate prevention.
- **`src/state/keyboard.ts`**:
  - Cross-platform keyboard modifiers (`MOD` = ⌘/Ctrl, `SHIFT` = ⇧/Shift).

---

### 3. Design Tokens & Styling (`index.css` & `App.css`)

- **Design System Variables (`src/index.css`)**:
  - Added `--hatch: repeating-linear-gradient(135deg, rgba(20, 24, 26, 0.14) 0 1.5px, transparent 1.5px 6px)` for neutral stale cues.
  - Added `--pop-shadow: 0 8px 24px rgba(20, 24, 26, 0.16), 0 0 0 1px var(--line)` for floating controls.
- **Stylesheet Additions & Refactorings (`src/App.css`)**:
  - **Keyframes**: `spin` (refresh spinners), `slide` (line progress indicator), `flash` (600ms highlight flash on mutation), `fadeIn`, `slideLeft`, `slideUp`, and `toastIn`.
  - **Stale Visuals**: Added `.results-section[data-stale]` and `.script-card[data-stale]` hatched left rail indicators.
  - **Fact Chips**: Added styles for `.chip-fact`, `.chip-dot`, `.chip-actions`, `.chip-input`, and dashed `.chip-add`.
  - **Stale Bar & Collapse**: Added `.stale-bar`, `.stale-actions`, and grid-based height-animating `.collapse` wrapper.
  - **Tab Refresh**: Added `.tab-wrap` and absolute `.tab-refresh` button with hover/pending states and `.tab-stale-ring`.
  - **Segment Card Edit Mode**: Added `.segment-title-input`, `.segment-who-edit`, `.tag-edit-wrap`, `.tag-remove`, and `.tag-add-input`.
  - **Script Lines**: Refactored `.line` layout by moving grid columns to `.line-hit`, adding `.is-selected` with 16px bottom margin, `.is-pending` text dimming, `.ln-progress` rail animation, and `.line-tombstone`.
  - **Line Toolbar & Menu**: Added `.line-toolbar`, `.line-editbar`, `.tb-btn`, `.menu`, `.menu-item`, and `.menu-positioner`.
  - **Version Rails**: Added `.version-rail`, `.rail-btn`, `.scope-badge`, and inline `.stepper`.
  - **Reason Refresh**: Added `.reason-item` wrapper and `.reason-refresh` button.
  - **Saved Scripts Drawer**: Added `.saved-btn`, `.saved-count-pill`, `.drawer-backdrop`, `.drawer`, and `.saved-accordion`.
  - **Toast Notifications**: Added `.toast-host`, `.toast`, and `.toast-undo`.
  - **Mobile Breakpoints (`@media (max-width: 699px)`)**: Full-width in-flow line toolbar, drawer bottom-sheet transition, and inline version steppers.

---

### 4. Components Created & Updated

| File | Purpose & Changes |
|---|---|
| **`src/components/FactChips.tsx`** | New component. Renders editable fact chips with in-place auto-growing textarea editor, faint pencil/cross actions on hover/focus, IME-safe Bangla key handling, `.chip-dot` edited indicator, and "+ Add a fact" dashed chip. |
| **`src/components/StaleBar.tsx`** | New component. Passive, non-blocking hatched status bar for stale notifications; includes the `Collapse` animated container. |
| **`src/components/SegmentTab.tsx`** | New component. Wraps the tab in `.tab-wrap` (preventing invalid `<button>` nesting), renders `.tab-refresh` on hover, and shows the hollow `.tab-stale-ring`. |
| **`src/components/SegmentCard.tsx`** | Updated component. Added "Save" and "Edit" action buttons; in-place edit mode for `h3` title, `.segment-who` description, and platform tags; pain point blockquote preserved as read-only. |
| **`src/components/ReasonItem.tsx`** | New component. Wraps reason buttons with a bottom-right `.reason-refresh` button; pins reason on click; supports orphaned state banner if all cited lines are deleted. |
| **`src/components/ReasonList.tsx`** | Updated component. Refactored to map over `ReasonDisplayItem[]` using `ReasonItem`. |
| **`src/components/VersionRail.tsx`** | New component. Renders desktop side chevrons, `.scope-badge` pill (`2/3`), mobile inline steppers, and screen-reader `aria-live` announcements. |
| **`src/components/LineToolbar.tsx`** | New component. Headless Base UI toolbar and context menu: `(Edit · Rephrase · Regenerate) \| (⋯ menu)` with Undo (`⌘Z`), Redo (`⇧⌘Z`), and Delete line. |
| **`src/components/ScriptLine.tsx`** | New component. Separates selection hit target (`.line-hit`) from nested controls; in-place textarea editor with auto-grow; live timeline draft callback; delete tombstone (`LineTombstone`). |
| **`src/components/ScriptCard.tsx`** | Updated component. Integrates `VersionRail`, `ScriptLine`, and `LineTombstone`; calculates dynamic word counts and timeline durations from live drafts; handles copy-to-clipboard. |
| **`src/components/SavedScriptsDrawer.tsx`** | New component. Slide-over drawer listing saved scripts with accordion breakdowns, platform tags, reason technique chips, copy script, and remove actions. |
| **`src/components/ToastHost.tsx`** | New component. Non-intrusive floating toasts supporting auto-dismiss and undo callbacks for fact removal, segment replacement, line deletion, and script saving. |
| **`src/components/ProductForm.tsx`** | Bugfix. Fixed React 18 `StrictMode` double-mount issue where object URLs in `useMemo` were prematurely revoked on unmount. |
| **`src/components/ResultsView.tsx`** | Core integration. Connected `useReducer(workspaceReducer)`, progressive streaming ingestion, stale cause bars & effect rails, bi-directional hover/pin highlighting, and the auto-scroll bugfix. |
| **`src/App.tsx`** | Shell integration. Added "Saved scripts" trigger button with count pill in masthead; mounted `SavedScriptsDrawer`. |
| **`src/hooks/useRegenerate.ts`** | Bridge hook. Provided simulated client-side generator stubs for segment replacement, line group rewriting, rephrasing, and line regeneration until API endpoints are wired. |

---

### 5. Verification & Quality Assurance

1. **TypeScript Typecheck (`tsc -b`)**:
   - Zero errors across all modules in composite build mode.
2. **Production Bundle Build (`vite build`)**:
   - Built successfully in 642ms (`index.html`, `index.css`, and `index.js`).
3. **Linting (`oxlint`)**:
   - Passed with 0 errors and 0 warnings on all 29 source files.
4. **Backend Test Suite (`pytest`)**:
   - 16 passed in 1.18s (`test_generate.py`, `test_health.py`, `test_validation.py`).

---

## Log Entry: UI Refinements, Auto-Scroll Bugfix, & Interaction Polish

**Date**: 2026-11-09  
**Status**: Completed & Verified (`tsc -b && vite build` & `oxlint` passing with 0 errors, 0 warnings)

---

### 1. Keyboard Navigation & Selection Clearing (`ResultsView.tsx` & `ScriptLine.tsx`)
- **Global `Escape` Handler**: Added a window `keydown` listener in `ResultsView.tsx` to clear active selections (`SELECT_NONE`) when pressing `Escape`, deselecting highlighted lines or pinned reasons.
- **Synchronized Editing Cancellation**: In `ScriptLine.tsx`, added synchronization between `selected` and `editing` states. Pressing `Escape` in edit mode cancels draft changes and bubbles up to deselect the line immediately.

### 2. Vertically Centered Version Rail Chevrons (`ScriptCard.tsx` & `VersionRail.tsx`)
- **Active Section Alignment**: Rather than remaining fixed at 50% card height, `VersionRail` chevrons now dynamically center vertically alongside the active selection:
  - If a line is selected, computes vertical midpoint of the `[data-line-uid]` element.
  - If a reason is pinned/focused, calculates the bounding box midpoint spanning all lit lines (`.line.is-lit`).
  - Defaults to the card midpoint when viewing the whole script scope, clamped safely inside card boundaries.
- **Smooth Gliding Animation**: Added `ResizeObserver` tracking and CSS `transition: top 0.25s cubic-bezier(0.16, 1, 0.3, 1)` on `.rail-btn`, smoothly sliding chevrons to the active section.

### 3. Line Editbar Repositioning, Auto-Focus, & Softened Styling (`ScriptLine.tsx` & `App.css`)
- **External Toolbar Placement**: Moved `.line-editbar` outside the line box to `bottom: -20px; right: 14px;`, eliminating text occlusion on `.line-hit` and `.ln-body`.
- **Reserved Margin & Fluid Entrance**: Increased `.line.is-selected` bottom margin to `26px` with a cubic-bezier transition, and introduced `toolbarPop` and `editbarSlide` keyframes for seamless transitions between edit and viewing modes.
- **Reliable Cursor Placement**: Configured `autoFocus` on the `<textarea>` alongside `useLayoutEffect` and `requestAnimationFrame` selection-range setting, guaranteeing cursor placement at the end of the line text on edit start without focus loss.
- **Soft & Sharp Design**: Replaced stark black borders (`var(--ink)`) and harsh drop shadows with pill border-radii (`999px`), crisp subtle borders (`var(--line-strong)`), layered diffuse shadows, and softened button styling.

### 4. Generation Viewport Auto-Scroll (`ResultsView.tsx`)
- **Resolved Viewport Positioning**: Replaced the initial Facts section scroll with `segmentSectionRef` on `.segment-section-animated`.
- **Full View Window Calculation**: Dynamically computes target scroll position taking both the customer segment tabs and the generating script card box (`.script-skeleton-card` / `.script-card`) into full view of the window, eliminating the need for manual scrolling as customer segments generate.

---

### 5. Verification & Quality Assurance
1. **TypeScript Typecheck (`tsc -b`)**: 0 errors.
2. **Production Bundle Build (`vite build`)**: Built in ~499ms with 0 errors.
3. **Linter (`oxlint`)**: 0 errors, 0 warnings across all 29 files.

---

## Log Entry: Backend Granular Regeneration Endpoints, Schemas, & Code-Gen Pipeline

**Date**: 2026-11-09  
**Status**: Completed & Verified (26/26 Python tests passing, TypeScript build & lint passing with 0 errors)

---

### 1. Pydantic Data Models & Contracts (`apps/api/schemas.py`)
- **Shared Context Models**: Added `ReasonInfo`, `ScriptLineContext`, and `RewrittenLine`.
- **Segment Regeneration Models**: Added `SegmentRegenerateRequest` with `facts`, `current_segment`, and `existing_segment_names`.
- **Script Rewrite Models**: Added `ScriptRewriteRequest` for full script rewrites.
- **Reason Line-Group Models**: Added `ReasonLinesRewriteRequest` and `ReasonLinesRewriteResponse`.
- **Single Line Models**: Added `LineRephraseRequest`, `LineRephraseResponse`, `LineRegenerateRequest`, and `LineRegenerateResponse`.
- **Section Streaming Models**: Added `SlotConfig` with `keep_segment: bool` and `SectionRegenerateRequest`.
- **Language Typing**: Enforced `language: Literal["en", "bn"]` across all request models.

### 2. Prompt Engineering & Strict Language Enforcement (`apps/api/prompts.py`)
- **Shared `LANGUAGE_BLOCK`**: Enforced proper Bengali script (`বাংলা`) without English or Banglish transliterations when `language == "bn"`.
- **Dedicated Prompts**: Created `REGENERATE_SEGMENT_PROMPT`, `REWRITE_SCRIPT_PROMPT`, `REWRITE_REASON_LINES_PROMPT`, `REPHRASE_LINE_PROMPT` (with tone mappings), and `REGENERATE_LINE_PROMPT`.
- **Helper Utilities**: Added `get_language_block`, `format_facts_text`, `format_script_context`, and `format_avoid_tones`.

### 3. FastAPI Regeneration Endpoints (`apps/api/main.py`)
- **`POST /regenerate/segment`**: Generates a distinct customer segment persona differing from all existing segments.
- **`POST /regenerate/script`**: Generates a complete script for a target segment with contiguous rationale line citations.
- **`POST /regenerate/reason-lines`**: Rewrites lines cited by a marketing technique while preserving surrounding narrative flow.
- **`POST /regenerate/line/rephrase`**: Rephrases a single sentence into an alternative tone (`punchy`, `casual`, `authentic`, `direct`) while maintaining subject and object.
- **`POST /regenerate/line/regenerate`**: Replaces a single line with a fresh angle matching its kind (`hook`, `concept`, `cta`).
- **`POST /regenerate/section`**: SSE streaming endpoint running fact updates; preserves hand-edited segments (`keep_segment == True`) and parallelizes script rewrites.

### 4. Automated Testing Suite (`apps/api/tests/test_regenerate.py`)
- Created 10 new test cases covering authorization (401), validation (422), upstream AI handling, Bangla language retention, and SSE event streaming.
- Full test suite passed: **26 passed in 1.24s** (100% pass rate).

### 5. OpenAPI Dump & Type Synchronization (`packages/api-types`)
- Dumped `apps/api/openapi.json` from the updated FastAPI instance.
- Generated TypeScript types into `packages/api-types/src/schema.d.ts` and re-exported clean type aliases in `packages/api-types/src/index.ts`.

### 6. Frontend Hook Integration (`apps/web/src/hooks/useRegenerate.ts`)
- Replaced mock stubs with real, typed HTTP `fetch` calls to the `/regenerate/*` endpoints with API key authentication.
- Verified that `tsc -b && vite build` and `oxlint` pass with **0 errors and 0 warnings**.

---

## Log Entry: Removal of Fallback Simulations, Direct UI Error Reporting, & Toast Dismissal

**Date**: 2026-11-09  
**Status**: Completed & Verified (26/26 Python tests passing, TypeScript build & lint passing with 0 errors)

---

### 1. Fallback Simulation Code Removal (`apps/web/src/hooks/useRegenerate.ts`)
- **Removed Mocks & Delays**: Completely eliminated hardcoded mock variations (`variationsEn`, `variationsBn`, `toneVariantsEn`, `toneVariantsBn`) and artificial `setTimeout` fallbacks across all 5 regenerator functions (`regenerateSegment`, `rewriteReasonLines`, `rephraseLine`, `regenerateLine`, `rewriteScript`).
- **Direct Error Throwing**: Updated `postJson` to catch fetch connection failures and throw descriptive user-facing errors (`"Cannot connect to API server at ..."`), as well as parse and surface backend HTTP error details (`res.json().detail`).
- **Context Options**: Enhanced hooks with optional parameters for `fullScript`, `targetLineIds`, `scriptContext`, `lineId`, and `avoidTones` to maximize prompt context sent to the backend.

### 2. UI Pending State Recovery (`apps/web/src/state/workspace.ts` & `apps/web/src/state/types.ts`)
- Added dedicated failure actions to ensure UI buttons and indicators never get stuck spinning on error:
  - `REPLACE_SEGMENT_FAIL`: Resets `slot.pending = false`.
  - `REWRITE_SCRIPT_FAIL`: Resets `slot.script.pending = false`.
  - `REWRITE_REASON_FAIL`: Resets `reason.pending = false` and clears group-level pending flags.
  - `LINE_ACTION_FAIL`: Resets `line.pending = undefined`.
- Added `pending?: boolean` to `ReasonItem` in `apps/web/src/state/types.ts` for reliable pending tracking across reason group operations.

### 3. Toast Notifications & Close Button (`apps/web/src/components/ToastHost.tsx` & `apps/web/src/App.css`)
- **Dismiss (X) Button**: Added a dedicated cross icon (`IconX` from `@tabler/icons-react`) to all toast notifications allowing users to close lingering toasts on demand.
- **Refined Lifetimes**: Reduced linger durations for responsive feel (4s for standard notifications, 6s for error alerts, 7s for undoable actions).
- **Error Toasts**: Supported `isError?: boolean` with `role="alert"` and `aria-live="assertive"` styling using design system tokens (`--err-ink`, `--err-line`).

### 4. Results View Error Plumbing (`apps/web/src/components/ResultsView.tsx`)
- Wrapped all mutation triggers (`handleSegmentRefresh`, `handleRewriteScript`, `handleReasonRefresh`, `handleRephrase`, `handleRegenerateLine`) in `try ... catch` blocks that dispatch their respective failure action on error and pop an error toast displaying the actual failure reason.
- Forwarded full workspace metadata (`name`, `market`, `language`) into `useRegenerate(meta)`.

### 5. Verification
- `bun run --cwd apps/web build`: Built cleanly with 0 TypeScript errors.
- `bun run --cwd apps/web lint`: 0 warnings, 0 errors across all 29 files.
- `pytest apps/api/tests/`: 26 passed in 1.26s.
