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

---

## Log Entry 7: Mobile Line Layout Polish, Selection Width Fix, & Loading Text Refinement

**Date**: 2026-11-11  
**Status**: Completed  
**Files Modified**: [`apps/web/src/components/LoadingState.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/LoadingState.tsx), [`apps/web/src/components/ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx), [`apps/web/src/components/LineToolbar.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/LineToolbar.tsx), [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css)

---

### 1. Plain Grey Activity Text with Moving Ellipsis (`LoadingState.tsx`)
* Replaced the blue pill container with plain editorial grey typography (`color: var(--ink-3); font-size: 0.8125rem; font-weight: 500;`).
* Integrated a dynamic moving ellipsis (`.` $\rightarrow$ `..` $\rightarrow$ `...`) cycling every 420ms alongside clean activity descriptions.

### 2. Gutter Width Optimization on Mobile (`ScriptLine.tsx`, `App.css`)
* **Problem**: `.ln-gutter` previously occupied `52px` with a `12px` gap (64px total), severely compressing dialogue line width on mobile screens and causing words to wrap awkwardly.
* **Resolution**:
  - In `@media (max-width: 699px)`, reduced gutter to `32px` with an `8px` gap (and `28px` with `6px` gap on `< 460px`).
  - Scaled line number `.ln-id` to `1.0625rem` and timestamp `.ln-time` to `0.6875rem`.
  - Reclaimed over 28px of horizontal width for Bengali/English dialogue text.

### 3. Selected Line Width Expansion Fix (`LineToolbar.tsx`, `App.css`)
* **Problem**: Selecting a line previously mounted `<LineToolbar />` with rigid unconstrained button widths (~339px min-content), pushing the parent `.line` and `.script-card` beyond viewport bounds and breaking mobile layouts.
* **Resolution**:
  - Enforced `box-sizing: border-box; width: 100%; max-width: 100%; min-width: 0;` on `.line`, `.line-hit`, `.ln-body`, and `.line-toolbar`.
  - Added `.tb-label-full` and `.tb-label-short` in [`LineToolbar.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/LineToolbar.tsx) so button labels collapse cleanly on mobile ("Regenerate" $\rightarrow$ "Regen") without horizontal overflow.
  - Adjusted mobile `.tb-btn` padding (`0 8px` on `< 699px`, `0 6px` on `< 460px`), keeping the entire toolbar securely within 250px on phones.

---

## Log Entry 8: Right-Edge Horizontal Scroll Chevrons & Damped Harmonic Motion Auto-Scroll

**Date**: 2026-11-12  
**Status**: Completed  
**Files Modified**: [`apps/web/src/components/DemoProductPicker.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/DemoProductPicker.tsx), [`apps/web/src/components/ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx), [`apps/web/src/hooks/useDampedAutoScroll.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/hooks/useDampedAutoScroll.ts), [`apps/web/src/App.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.tsx), [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css)

---

### 1. Right-Edge Scroll Chevron on Sample Products ([`DemoProductPicker.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/DemoProductPicker.tsx))
* Wrapped `.shelf-rail` inside `.shelf-rail-wrap` and added a right-edge floating circular button with `IconChevronRight`.
* Dynamically detects whether more product cards exist to the right (`scrollLeft + clientWidth < scrollWidth - 12`).
* When tapped or clicked, smoothly steps the rail rightward (`scrollRail(1)`), disappearing automatically when scrolled to the end.

### 2. Segment Tabs Horizontal Scroll Chevron ([`ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx))
* Wrapped customer segment `.tabs` inside `.tabs-wrap` and added `.tabs-scroll-chevron` with `IconChevronRight`.
* When segment tabs overflow on mobile screens, the chevron prominently floats on the right edge, indicating additional customer segments and enabling smooth one-touch stepping (`scrollBy({ left: 220 })`).

## Log Entry 9: Mobile Line Gutter Reclamation, Dynamic Script Format Submit Label, & Customer Segment Touch Carousel Overhaul

**Date**: 2026-11-12  
**Status**: Completed  
**Files Modified**: [`apps/web/src/components/ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx), [`apps/web/src/components/ProductForm.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ProductForm.tsx), [`apps/web/src/components/ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx), [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css)

---

### 1. Mobile Line Gutter Empty Space Reclamation (`ScriptLine.tsx`, `App.css`)
* **Problem**: In previous layouts, `.ln-gutter` formed a rigid left column spanning the entire card height on mobile. Because the line number and timestamp only take ~28px vertically while dialogue and visual cue take significant vertical space, the space underneath the time in the left column remained completely empty, severely squashing dialogue text and visual cue cards to the right.
* **Resolution**:
  - Flattened `.line-hit` children (`ln-gutter`, `ln-meta-row`, `ln-visual-cue`, and `ln-text` / `ln-edit`) to direct grid items.
  - On desktop (`min-width: 700px`), `.ln-gutter` sits in column 1 spanning all rows (`grid-row: 1 / 4`), while metadata, visual cue (if present), and dialogue text flow sequentially in column 2.
  - On mobile (`@media (max-width: 699px)`):
    - Row 1: `.ln-gutter` (number and timestamp inline side-by-side, e.g. `2  0:04`) and `.ln-meta-row` (badges: `Concept`, `Voiceover (VO)`) sit inline together.
    - Row 2 & 3: `.ln-visual-cue` and `.ln-text` / `.ln-edit` use `grid-column: 1 / -1;`, expanding across 100% of the card width from the far-left edge without indentation, fully reclaiming the unused gutter space for dialogue text.
  - Removed `IconVideo` from `.ln-visual-cue` and converted it into a subtle editorial direction card (`background: var(--tint); border: 1px solid var(--line); border-radius: 8px; font-style: italic; color: var(--ink-2);`).

### 2. Format-Aware Dynamic Submit Button (`ProductForm.tsx`)
* **Requirement**: The primary action button text should adapt dynamically to `values.script_format`.
* **Resolution**:
  - In [`ProductForm.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ProductForm.tsx), bound the button label to:
    - `"Generate Commercial Script"` when `values.script_format === 'commercial_30s'`
    - `"Generate UGC Script"` when `values.script_format === 'ugc'` (or default)
    - Preserving `"Generating…"` during in-flight pipeline execution.

### 3. Customer Segments Touch Swipe, Right Chevron, & Mobile Card Containment (`ResultsView.tsx`, `App.css`)
* **Problem**:
  1. On mobile viewports, the customer segment tabs `.tabs` used `grid-auto-flow: column; grid-auto-columns: minmax(180px, 70%)` without explicit container bounds. This intrinsic grid layout pushed `.tabs-wrap` and `.shell` wider than the viewport (~550px on a 390px screen), creating a page-level horizontal scrollbar.
  2. Because the page container expanded to the combined width of all tabs, `.tabs.clientWidth` matched its `scrollWidth`, causing `canScrollTabsRight` to evaluate to `false`, hiding the right chevron, and breaking internal touch swiping.
  3. The `.segment-card` panel expanded to the widened container, causing content and quote text to blow out beyond the right screen edge.
* **Resolution**:
  - Converted mobile `.tabs` (`@media (max-width: 699px)`) to a dedicated scroll-snap flex rail:
    - `display: flex; overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; gap: 8px;`
    - Hidden scrollbars (`scrollbar-width: none; -ms-overflow-style: none;`) to keep the interface clean.
  - Styled `.tab-wrap` on mobile with `flex: 0 0 74%; max-width: 250px; min-width: 180px; scroll-snap-align: start; box-sizing: border-box;` so the active tab is prominent while the next tab peeks from the right edge.
  - Constrained `.tabs-wrap`, `.tab-panel`, `.segment-card`, `.segment-main`, and `.pain` to `width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; word-break: break-word;` with `flex-wrap: wrap;` on `h3` and `.segment-lead-angles`.
## Log Entry 10: Mobile Buyer Persona Cycler, Eased Auto-Scroll, Reveal Pacing, & Editbar Mobile Cleanup

**Date**: 2026-11-12  
**Status**: Completed  
**Files Modified**: [`apps/web/src/components/ScriptCard.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptCard.tsx), [`apps/web/src/components/ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx), [`apps/web/src/components/ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx), [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css), [`apps/web/src/App.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.tsx)

---

### 1. Mobile Buyer Persona Cycler in Workbench ([`ScriptCard.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptCard.tsx), [`ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx), [`App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css))
* **Problem**: On mobile phones, once users scroll down to review or edit dialogue lines in the script workbench, the customer segment tabs are off-screen above. Switching between buyer personas required repeatedly scrolling all the way back up to the top.
* **Resolution**:
  - Implemented `.workbench-persona-bar` at the top of [`ScriptCard.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptCard.tsx), active exclusively on mobile (`@media (min-width: 700px) { display: none !important; }`).
  - Displays circular navigation buttons (`<` and `>`), a clean uppercase kicker (`BUYER PERSONA 2 OF 3`), and the active persona name.
  - Tapping `<` or `>` wraps and cycles through all available customer segments, instantly updating dialogue lines, pacing meters, and words without scrolling.

### 2. Auto-Scroll "Glued to New Generations" with Ease-in-Out Cubic ([`ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx))
* **Diagnosis**: The previous `useDampedAutoScroll` stopped on frame 1 because it detected that the script data had already arrived over the network, leaving the screen frozen at the facts section while cards popped in below the fold.
* **Resolution**:
  - Replaced damped physics with a direct mathematical `easeInOutCubic` scroll animator directly inside [`ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx).
  - Actively tracks the newest popped-in elements (`lastChip`, `lastCard`, `segmentSectionRef`, and `workbenchRef`): whenever a newly generated card extends below the fold (`rect.bottom > window.innerHeight - 60`), the viewport smoothly glides down with ~80px padding to keep the newly born element in comfortable focus.
  - Preserves user control: any upward touch swipe, wheel scroll, or arrow key immediately cancels auto-scroll.

### 3. Lowered Artificial Generation Rate ([`ResultsView.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ResultsView.tsx))
* Relaxed pop-in pacing timers to allow users to comfortably read items as they appear:
  - Facts: `300ms` initial, `420ms` per item (previously 240ms).
  - Angles: `360ms` initial, `460ms` per card (previously 250ms).
  - Customer Segments: `400ms` initial, `540ms` per segment (previously 320ms).

### 4. Line Edit Toolbar Mobile Cleanup ([`App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css))
* **Requirement**: Hide keyboard shortcuts text (`↵ save · Shift+↵ newline · Esc cancel`) on mobile devices and position Cancel and Save buttons neatly at the side.
* **Resolution**:
  - In `@media (max-width: 699px)`, set `.tb-hint { display: none; }` and `.line-editbar { justify-content: flex-end; gap: 8px; }`.

---

## Log Entry 11: Speaker Badge Concealment, Visual Direction Lead Labeling, & Universal Visual Cues for UGC

**Date**: 2026-11-12  
**Status**: Completed  
**Files Modified**: [`apps/web/src/components/ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx), [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css), [`apps/api/prompts.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/prompts.py), [`apps/api/validation.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/validation.py), [`apps/api/tests/test_format_and_planning.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/tests/test_format_and_planning.py)

---

### 1. Speaker Badge Hidden in Line Cards ([`ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx))
* Commented out the `line.speaker` badge block (`.ln-speaker-badge`) in `ScriptLine.tsx` per user design request, keeping dialogue lines clean and focused on structural roles (`Hook`, `Concept`, `CTA`).
* Cleaned up unused `IconVolume` import.

### 2. Bold "Visual Direction: " Lead Label in Visual Cue ([`ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx), [`App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css))
* In [`ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx), prepended `<strong>Visual Direction: </strong>` inside `.ln-visual-cue` ahead of the shot description.
* In [`App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css), styled `.ln-visual-cue strong` with `font-weight: 700; font-style: normal; color: var(--ink); margin-right: 2px;`, establishing a crisp upright label preceding the italic direction cue text.

### 3. Enabled Visual Cues for UGC Video Scripts ([`prompts.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/prompts.py), [`validation.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/validation.py))
* Updated `FORMAT_SPECS["ugc"].use_speaker_visual = True` in [`prompts.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/prompts.py).
* In `build_script_prompt`, added clear visual cue instructions for UGC scripts:
  - `- visual: For each line, provide a concise visual direction cue (<= 12 words, in English) describing what the creator shows or does on camera (e.g. holding product, reacting to camera, demoing texture).`
* Updated [`validation.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/validation.py) and test suites so all 3 customer segments reliably receive visual cues across both UGC and 30s Commercial formats.






