# Sprint 6 Changelog: UI Harmonization & Mobile Ergonomics

## Log Entry 1: Design System Audit & Divergence Diagnosis

**Date**: 2026-11-11  
**Status**: Completed  
**Context Specification**: [`docs/sprints/6. UI/ui-changes-context.md`](file:///home/bast0k/projects/ug-script-writer/docs/sprints/6.%20UI/ui-changes-context.md)

---

### 1. Diagnosis & Problem Statement
* Following rapid feature additions in **Sprint 3** (Access gate, demo product shelf, token usage telemetry) and **Sprint 4** (Two-tier facts & creative angles, format engine, speaker metadata), noticeable visual divergences crept into the UI.
* **Core divergences identified**:
  1. **Color Token Drift**: Hardcoded hexes (e.g. `#0ea5e9`, `#cbd5e1`, `#334155`, `rgba(15, 23, 42, ...)`) instead of semantic and theme variables (`--paper`, `--card`, `--tint`, `--line`, `--ink-2`).
  2. **Geometry Mismatches**: Tight rectangular radiuses (`border-radius: 4px` - `6px`) clashing with the editorial warm design language's pill shapes (`border-radius: 999px` or `12px/14px` cards).
  3. **Sibling Disparity in Line Cards**: In [`ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx), the `.kind` pill and `.ln-speaker-badge` chip sat side-by-side but appeared to belong to two completely separate design systems.
  4. **Harsh Visual Cue Slab**: `.ln-visual-cue` utilized a flat `border-left: 3px solid #0ea5e9` with zero radius, clashing with the curated line card border.
  5. **Bland Desktop Grid & Endless Mobile Stacks**: Creative angles rendered as an uninspired desktop grid and collapsed into an 8–10 card vertical stack on mobile, pushing interactive workbench controls offscreen.

---

## Log Entry 2: Mobile Masthead Viewport & Overflow Containment

**Date**: 2026-11-11  
**Status**: Completed  
**Files Modified**: [`apps/web/src/App.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.tsx), [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css), [`apps/web/src/index.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/index.css)

---

### 1. Masthead Action Buttons Responsive Hierarchy
* **Issue**: On mobile viewports (< 480px and < 360px), the top masthead containing brand text, `TokenMeter`, `Access`, and `Saved scripts` exceeded screen width, causing horizontal scrolling and layout breakage.
* **Implementation Details**:
  - Restructured masthead into `.masthead-brand` (recording dot + title) and `.masthead-actions` with `justify-content: space-between;`.
  - Added responsive breakpoints:
    - **`< 640px`**: Hides `.meter-label` ("Tokens") and secondary text in `.saved-btn-full` ("scripts"), preserving compact pill heights (`34px`) and padding.
    - **`< 460px`**: Collapses `.access-btn` and `.saved-btn` into clean, accessible icon buttons with `aria-label` attributes (`IconKey`, `IconBookmark` + count badge).
    - **`< 360px`**: Compacts brand title font size (`0.875rem`) to guarantee zero overflow even on narrow devices like iPhone SE.
  - Constrained `.meter-pop` usage popover on mobile: `max-width: 292px; width: calc(100vw - 32px);`.
  - Added `overflow-x: clip;` on `html` and `body` in [`index.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/index.css) to eliminate phantom horizontal overscroll.

---

## Log Entry 3: ScriptLine Sibling Chip Harmonization & Visual Cue Polish

**Date**: 2026-11-11  
**Status**: Completed  
**Files Modified**: [`apps/web/src/components/ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx), [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css)

---

### 1. Chip Typography & Pill Unification
* **Issue**: `.kind` and `.ln-speaker-badge` had disparate heights, font weights, and border radiuses.
* **Resolution**:
  - Aligned `.kind` and `.ln-speaker-badge` to identical `padding: 3px 10px;`, `border-radius: 999px;`, and `font-size: 0.8125rem;`.
  - Kept `.kind` on semantic accent tokens (`--hook-bg`, `--concept-bg`, `--cta-bg`) and updated `.ln-speaker-badge` to soft warm tokens: `background: var(--tint); border: 1px solid var(--line); color: var(--ink-2);`.
  - Added `IconUser` / `IconVolume` inside speaker badges with `IconVideo` for visual cue rows.

### 2. Soft Editorial Visual Cue Callout
* Replaced the harsh `border-left: 3px solid #0ea5e9` with an indented, soft editorial direction card:
  - `background: var(--tint); border: 1px solid var(--line); border-radius: 8px;`
  - Integrated `IconVideo` icon in `var(--concept)` to provide visual clarity without breaking card harmony.

---

## Log Entry 4: Creative Angles Carousel, Tooltip Overhaul, & Mobile Tap Interaction

**Date**: 2026-11-11  
**Status**: Completed  
**Files Modified**: [`apps/web/src/components/AngleChips.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/AngleChips.tsx), [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css)

---

### 1. Angle Explanations & Meta Directory
* Defined comprehensive angle taxonomy metadata `ANGLE_TYPE_META` for all 7 angle types:
  - `benefit`: Claim-bearing direct utility and transformation.
  - `demo`: Claim-bearing sensory visual/physical demonstration.
  - `objection`: Claim-bearing barrier or friction resolution.
  - `use_moment`: Framing contextual consumption moment.
  - `identity`: Framing target persona values and aspiration.
  - `contrast`: Framing category alternative or competitor comparison.
  - `audience_context`: Framing situational urgency.

### 2. Responsive Mobile Scroll-Snap Rail
* Under `< 680px`, replaced the tall vertical stack with a horizontal swipe rail:
  - `.angles-grid { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; gap: 12px; }`
  - `.angle-card { flex: 0 0 84vw; max-width: 320px; scroll-snap-align: start; min-height: 120px; }`
  - Added header scroll buttons (`IconChevronLeft`, `IconChevronRight`) allowing smooth rail stepping.

### 3. Mobile Badge Tap Fix
* **Issue**: Tapping on `.angle-badge` on mobile did not show the info tooltip.
* **Root Causes Diagnosed**:
  1. *Synthetic Mouse Event Race*: On mobile touch, the browser triggers `mouseenter` / `focus` before `click`. When `showTooltip` was toggled with `setShowTooltip(prev => !prev)`, `onMouseEnter` set it to `true` and `click` immediately toggled it back to `false`.
  2. *CSS Overflow Clipping*: In mobile rail mode, `.angles-grid` has `overflow-x: auto`. In CSS, any non-visible horizontal overflow forces vertical overflow to `auto`. Tooltips positioned at `bottom: calc(100% + 8px)` were clipped above the grid boundary.
  3. *Missing Button Resets*: `<button className="angle-type-pill-wrap">` lacked native button resets.
* **Resolution**:
  - Separated `pinned` (click/tap pin) and `hovered` (desktop mouse enter) state in `AngleTypeBadge`.
  - Added outside-tap listener on `pointerdown` and `Escape` key handler to dismiss pinned tooltips.
  - Reset button styles: `background: transparent; border: none; padding: 0; font: inherit; outline: none; cursor: pointer;`.
  - On mobile (`@media (max-width: 680px)`), positioned `.angle-tooltip` at `top: calc(100% + 6px); left: 0; width: min(250px, calc(84vw - 28px));` with an inverted upward arrow so it renders comfortably inside the card bounds without overflow clipping.

---

## Log Entry 5: Paced Component Reveal & Bottom Auto-Scroll

**Date**: 2026-11-11  
**Status**: Completed  
**Files Modified**: [`apps/web/src/App.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.tsx), [`apps/web/src/components/ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx)

---

### 1. Generation Bottom Auto-Scroll
* Replaced `outputRef.current.scrollIntoView({ block: 'start' })` with `scrollToBottom()`.
* Automatically runs smooth window scrolling to `document.documentElement.scrollHeight` inside `requestAnimationFrame` and deferred timers so users immediately see output progress as soon as "Generate UGC Script" is tapped.

### 2. Gradual Component Reveal Pacing
* **Issue**: The previous reveal was too abrupt (`50ms/100ms` for facts, `120ms` for segments, `0ms` for angles).
* **Resolution**:
  - Added `visibleAnglesCount` state to sequence angles after facts.
  - Paced reveal timers:
    - Facts: `160ms` initial, `240ms` per item.
    - Angles: `180ms` initial, `250ms` per card (`angles.slice(0, visibleAnglesCount)`).
    - Segments: `220ms` initial, `320ms` per segment tab.
  - Automatically respects `prefers-reduced-motion` by revealing all items immediately.

---

## Log Entry 6: Loading Stage Dynamic Activity Ticker & Gating Polish

**Date**: 2026-11-11  
**Status**: Completed  
**Files Modified**: [`apps/web/src/components/LoadingState.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/LoadingState.tsx), [`apps/web/src/components/AccessGateModal.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/AccessGateModal.tsx), [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css)

---

### 1. Animated Activity Ticker (`LoadingState.tsx`)
* **Problem**: When users trigger generation, they stare at a pulsing red/green dot and a static title for 10–20 seconds without knowing what the model is doing under the hood, causing anxiety and impatience.
* **Implementation Details**:
  - Inserted a dynamic swipe-up activity ticker between `<strong>{s.title}</strong>` and `<p>{s.note}</p>` on the currently active stage.
  - **Stage 0 Activities** (Extraction & Angles):
    - `"Analyzing Image(s) & packaging details…"`
    - `"Detecting product features & visual cues…"`
    - `"Extracting core claims & ingredients…"`
    - `"Formulating creative psychological angles…"`
    - `"Grounding visual anchors from pack shot…"`
  - **Stage 1 Activities** (Segments & Dialogue Scriptwriting):
    - `"Envisioning Market Segments & buyer personas…"`
    - `"Crafting 3-second scroll-stopping hooks…"`
    - `"Drafting dialogue lines with psychological pacing…"`
    - `"Polishing natural speech rhythm & cadence…"`
    - `"Synthesizing conversion marketing rationales…"`
  - Paced ticker transitions every `2200ms` with `@keyframes stageTickerSwipeUp` (smooth slide up from `14px` and fade in).
  - Styled as an organic pill matching the warm design tokens (`background: var(--tint); border: 1px solid var(--line); border-radius: 999px; color: var(--concept);`) with an animated nudging chevron `›`.
  - Added full `prefers-reduced-motion` compliance.

### 2. Access Gate Mobile Width & OTP Auto-Unlock (`AccessGateModal.tsx`)
* In [`AccessGateModal.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/AccessGateModal.tsx), automatically blurs the input and triggers verification as soon as the 5th character is entered.
* In [`App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css), constrained `.gate-card` to `max-width: min(440px, calc(100vw - 32px))` and `.gate-backdrop` to `max-width: 100vw; overflow-x: hidden;` to eliminate horizontal overscroll on narrow mobile viewports.
* Standardized `.chip-val-tag` and `.shelf-lang` badges to `border-radius: 999px` full pills.

