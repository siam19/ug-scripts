# UI Changes & Component Discrepancy Context

> **Sprint 6: UI Harmonization & Polish**  
> **Document Purpose:** Complete audit and context specification of all newly created and modified frontend components from **Sprint 3 (Security & Deployment)** and **Sprint 4 (Pipeline Optimization & Format Engine)**.  
> **Goal:** Identify all visual and design system divergences from the original base UI and provide actionable guidelines for harmonizing styling, mobile ergonomics, and visual hierarchy.

---

## 1. Executive Summary & Problem Diagnosis

The base web application (`ug-script-writer`) was originally built with an **editorial, warm, organic design language**:
- **Palette**: Paper and warm linen surfaces (`--paper: #e9edea`, `--card: #fbfcfb`, `--tint: #f0f3f1`, `--line: #d3dad5`), high-contrast ink typography (`--ink: #14181a`), and semantic-only color accents (`--hook: #d95a07`, `--concept: #2a55d4`, `--cta: #12805a`).
- **Typography**: Display typography using *Bricolage Grotesque* and *Hind Siliguri*; UI body using *Hanken Grotesk*.
- **Shape Language**: Soft, organic containers (`border-radius: 20px` for panels, `12px` for cards/chips, `999px` full pills for badges and tags).

During **Sprint 3** (access gating, demo picker, token telemetry) and **Sprint 4** (angle chips, format toggles, speaker chips, visual cue banners), new components were added. While functionally robust, they introduced noticeable **styling divergences**:
1. **Generic Tailwind / Cold Slate Bleed**: Hardcoded hexes (e.g. `#0ea5e9`, `#0369a1`, `#cbd5e1`, `rgba(15, 23, 42, ...)`) instead of design system tokens (`var(--tint)`, `var(--line)`, `var(--ink-2)`).
2. **Inconsistent Badge & Chip Geometry**: Rectangular, tight-radius badges (`border-radius: 4px` - `6px`) clashing with organic full pills (`border-radius: 999px` or `12px`).
3. **Disjointed Sibling Styling**: In `<ScriptLine />`, the `.kind` pill and `.ln-speaker-badge` chip sit in the same meta row but look like they come from two different component libraries.
4. **Harsh Left Borders**: `.ln-visual-cue` uses a sharp flat `border-left: 3px solid #0ea5e9` with zero left radius inside an elegant, curved 12px line card.
5. **Bland, Flat Layouts**: The **Creative Angles** section renders as an uninspired desktop grid and collapses into an endless, monotonous vertical column of 6–9 cards on mobile, pushing key results offscreen.
6. **Mobile Sizing & Input Friction**: `<AccessGateModal />` overflows mobile viewports horizontally and requires a manual button tap instead of auto-submitting on the 5th OTP character.

---

## 2. Visual Discrepancy Evidence

### Case 1: Script Line Chips & Visual Cue Clash
*(Referencing user screenshot `uploaded_media_0_1794413238533.png`)*

```
+-----------------------------------------------------------------------------------------+
| 2    [ Concept ]  [ Voiceover (VO) ]                                                   |
| 0:04 | Close-up of PRAN Mango Tetra Pack being pulled out of a bag.                     |
|      এ সময়ে চাই এক চিমটি সতেজতা...                                                       |
|                                         [ Edit ] [ Rephrase ] [ Regenerate ] [ ... ]   |
+-----------------------------------------------------------------------------------------+
```

* **Chip Contrast**:
  - `[Concept]` is styled with `.kind`: `padding: 2px 9px; background: #fff; border-radius: 6px; color: #2a55d4; font-weight: 700;`.
  - Sibling `[Voiceover (VO)]` is styled with `.ln-speaker-badge`: `padding: 2px 8px; background: rgba(15,23,42,0.06); border: 1px solid #cbd5e1; border-radius: 5px; font-size: 0.75rem; font-weight: 500; color: #444d51;`.
  - **Issue:** One has a prominent colored type badge with clean bold white contrast; the other looks like a muted, low-contrast grey outline button with different height, radius, and typography.
* **Visual Cue Border**:
  - `.ln-visual-cue` has `background: rgba(14, 165, 233, 0.08); border-left: 3px solid #0ea5e9; border-radius: 0 6px 6px 0;`.
  - **Issue:** It creates a harsh blue bar cutting through the middle of the card. The parent `.line.is-selected` already has a curated 3px left border (`border-left-color: var(--kind)`) and `box-shadow: 0 0 0 1px var(--kind)`. Having a second, competing flat colored vertical slab inside it breaks visual calm.

### Case 2: Creative Angles Section Monotony
*(Referencing user screenshot `uploaded_media_1_1794413238533.png`)*

```
+-----------------------------------------------------------------------------------------+
| Creative angles                                                                         |
| Hooks, objection handling, and psychological moments connecting product facts...        |
| [ All (9) ] [ Claim-bearing (5) ] [ Framing (4) ]                         Show all 9 v  |
|                                                                                         |
| +------------------------------------+  +------------------------------------+          |
| | #1  [BENEFIT]  Fact #1, #6         |  | #2  [VISUAL DEMO]  Fact #3, #6     |          |
| | Satisfy your afternoon sweet tooth |  | Show how easily the compact 200 ml |          |
| +------------------------------------+  +------------------------------------+          |
+-----------------------------------------------------------------------------------------+
```

* **Desktop Issue**: Bland white cards with faint grey outlines and harsh pastel pills. Cards lack tactile feel, depth, or clear visual connection to the customer segments below.
* **Mobile Issue**: `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` turns into a single 9-card vertical stack. Users on phones must scroll through hundreds of pixels of static angle text before ever seeing the interactive customer segment tabs or the script!

---

## 3. Comprehensive Inventory of Sprint 3 & 4 Components

Below is the complete catalog of all components added or substantially modified across Sprints 3 and 4, their file locations, current implementations, and harmonization requirements.

---

### Component 1: `ScriptLine.tsx` — Meta Row & Visual Cue
* **File**: [`apps/web/src/components/ScriptLine.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ScriptLine.tsx)
* **Styles**: [`apps/web/src/App.css#L892-L935`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css#L892-L935)
* **Parent Container**: `<ol className="lines">` inside `<ScriptCard />` (`ResultsView.tsx`)
* **Sprint Introduced**: Sprint 4 (Phase 4 Format Engine)
* **What It Renders**:
  - `ln-meta-row`: Contains `<span className="kind">` (e.g. `Hook`, `Pain`, `Concept`, `CTA`) and `<span className="ln-speaker-badge">` (e.g. `Creator`, `Voiceover (VO)`, `Host`).
  - `ln-visual-cue`: Visual direction block (e.g. `Close-up of PRAN Mango Tetra Pack...`).
* **Current Styling & Discrepancies**:
  ```css
  .kind {
    padding: 2px 9px;
    background: var(--kind-bg);
    border-radius: 6px;
    color: var(--kind);
    font-size: 0.8125rem;
    font-weight: 700;
  }
  .ln-speaker-badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    background: rgba(15, 23, 42, 0.06);
    border: 1px solid var(--line-strong, #cbd5e1);
    border-radius: 5px;
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--ink-2);
  }
  .ln-visual-cue {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    padding: 5px 10px;
    background: rgba(14, 165, 233, 0.08);
    border-left: 3px solid #0ea5e9;
    border-radius: 0 6px 6px 0;
    font-size: 0.8125rem;
    font-style: normal;
    color: #0369a1;
    line-height: 1.4;
    margin: 2px 0;
  }
  ```
* **Harmonization Recommendations**:
  1. **Speaker Chip**: Align height, font metrics, and border radius with `.kind` or `.tag`. Use a subtle muted chip matching the warm system: `background: var(--tint); border: 1px solid var(--line); border-radius: 999px; font-weight: 600; font-size: 0.75rem; color: var(--ink-2);`.
  2. **Visual Cue**: Remove the harsh vertical left bar (`border-left: 3px solid #0ea5e9`). Instead, style it as a soft, elegant direction callout: `background: var(--tint); border-radius: 8px; padding: 6px 12px; color: var(--ink-2); font-size: 0.8125rem; border: 1px solid var(--line);` with an optional subtle icon or prefix.

---

### Component 2: `AngleChips.tsx` — Creative Angles Shelf
* **File**: [`apps/web/src/components/AngleChips.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/AngleChips.tsx)
* **Styles**: [`apps/web/src/App.css#L1185-L1350`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css#L1185-L1350)
* **Parent Container**: `<section className="results-section">` in `ResultsView.tsx` (sits between FactChips and Customer Segments)
* **Sprint Introduced**: Sprint 4 (Phase 2 Creative Angles Presentation)
* **What It Renders**:
  - Filter bar: `All (N)`, `Claim-bearing (N)`, `Framing (N)`, plus a toggle button `Show all N / Show fewer`.
  - Angles Grid: 2-column card grid rendering up to 6–10 angle items (`#1`, type badge, fact linkage pills, angle premise text).
* **Current Styling & Discrepancies**:
  - Cards are plain white rectangles with faint border lines (`border: 1px solid var(--line)`).
  - Type badges use inconsistent pastel fills (`.angle-badge-benefit`, `.angle-badge-demo`, etc.) with 5px border radius.
  - On mobile screens, it renders as a long vertical stack of cards, pushing the script workbench below the fold.
* **Harmonization & Mobile Redesign Recommendations**:
  1. **Mobile Layout**: Convert the grid into a **horizontal swipeable carousel/rail** on mobile (`display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 12px;`) or a collapsible drawer, so mobile users can easily swipe through angles without excessive vertical page length.
  2. **Card Styling**: Elevate cards with warm editorial borders, a clear number indicator (`#1`), and matching pill badges (`border-radius: 999px`).
  3. **Visual Depth**: Use subtle accent left pinstripes or tinted headers that correspond to the angle family.

---

### Component 3: `SegmentCard.tsx` — Lead Angles Integration
* **File**: [`apps/web/src/components/SegmentCard.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/SegmentCard.tsx)
* **Styles**: [`apps/web/src/App.css#L605-L640`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css#L605-L640)
* **Parent Container**: Rendered right above `<div className="workbench">` in `ResultsView.tsx`
* **Sprint Modified**: Sprint 4 (Phase 2 & Phase 4)
* **What It Renders**:
  - Segment title, description, target platforms (`.tag-list`).
  - `.segment-lead-angles`: Renders lead angles cited by this segment as compact numbered pills (`#1`, `#3`) with tooltip on hover.
  - Right column: "In their words" customer pain quote.
* **Current Styling & Discrepancies**:
  - `.lead-angle-pill` uses `min-width: 26px; height: 20px; font-size: 0.75rem; border-radius: 9999px;`.
  - Contrast with `.tag` (`padding: 3px 11px; background: #e5eae7; border-radius: 999px; font-size: 0.8125rem;`).
* **Harmonization Recommendations**:
  - Ensure the `.segment-lead-title` and `.lead-angle-pill` group aligns seamlessly with the `.tag-list` directly above it.
  - Standardize font sizing (`0.8125rem`) and hover transitions.

---

### Component 4: `ProductForm.tsx` — Script Format Switcher
* **File**: [`apps/web/src/components/ProductForm.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ProductForm.tsx)
* **Styles**: [`apps/web/src/App.css#L225-L270`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css#L225-L270)
* **Parent Container**: Main generation form (`.form-grid`)
* **Sprint Introduced**: Sprint 4 (Phase 4 Format Setting)
* **What It Renders**:
  - Segmented toggle: `[ UGC Video ]` vs `[ 30s Commercial ]`.
  - Dynamic hint text placed in the adjacent column explaining word ranges and pacing.
* **Current Styling & Discrepancies**:
  - The toggle uses `.format-toggle-group` and `.format-toggle-btn`.
  - Needs verification against `.lang-toggle-group` to ensure exact matching button padding, pill shape, active shadow, and typography.

---

### Component 5: `AccessGateModal.tsx` — Gatekeeper & Access Verification
* **File**: [`apps/web/src/components/AccessGateModal.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/AccessGateModal.tsx)
* **Styles**: [`apps/web/src/App.css#L1360-L1620`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css#L1360-L1620)
* **Parent Container**: Top-level modal rendered in `App.tsx` when user has no stored access token
* **Sprint Introduced**: Sprint 3 (Security & Deployment)
* **What It Renders**:
  - Centered modal dialog (`.gate-card`) with blurred backdrop.
  - Tabs: "Enter Access Code" vs "Request Access".
  - 5-slot segmented OTP input component with auto-focus and paste handling.
  - "Unlock App" primary button.
  - Request access form (name, email, company, role, use-case).
* **Current Issues Noted in Sprint 6 Backlog**:
  1. **Width & Mobile Sizing**: `.gate-card` has `max-width: 440px`, but internal padding and slot spacing causes horizontal layout expansion or awkward padding on narrow mobile viewports (<380px).
  2. **Auto-Submit Friction**: The user must enter all 5 characters and then manually click "Unlock App". It should automatically trigger verification as soon as the 5th character is filled.
  3. **Color Tokens**: Uses cold slate styles (`rgba(15, 23, 42, 0.18)`, `#e2e8f0`, `#2563eb`) rather than the application's `--ink`, `--line`, and `--tint`.

---

### Component 6: `DemoProductPicker.tsx` — Sample Shelf
* **File**: [`apps/web/src/components/DemoProductPicker.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/DemoProductPicker.tsx)
* **Styles**: [`apps/web/src/App.css#L1625-L1810`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css#L1625-L1810)
* **Parent Container**: Embedded in `ProductForm.tsx` above the product photo field
* **Sprint Introduced**: Sprint 3 (Demo Catalog)
* **What It Renders**:
  - `.shelf-bar`: Collapsed bar with fanned thumbnail stack (`--i: 0, 1, 2`), title, and chevron.
  - Sheet popover: Category tabs (`All`, `Skincare`, `Fashion`, `Food & Beverage`, etc.) and horizontal scrolling rail of poster cards with images and language pills.
* **Current Styling & Discrepancies**:
  - Works well, but shelf poster cards use sharp corners and cold border lines that can be softened to match the warm card styling of the app.

---

### Component 7: `TokenMeter.tsx` — Live Telemetry Meter
* **File**: [`apps/web/src/components/TokenMeter.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/TokenMeter.tsx)
* **Styles**: [`apps/web/src/App.css#L1815-L1880`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css#L1815-L1880)
* **Parent Container**: Rendered in the top masthead / header bar in `App.tsx`
* **Sprint Introduced**: Sprint 3 (Token Telemetry)
* **What It Renders**:
  - Compact badge displaying session tokens (e.g. `1,420 tokens`) and stage tooltip breakdown (`Stage 1 extraction`, `Stage 2 generation`, `Regenerations`).
* **Harmonization Recommendations**:
  - Keep styling minimal and subtle (`--ink-3`, `font-variant-numeric: tabular-nums`).

---

### Component 8: `FactChips.tsx` — Value Indicator Badges
* **File**: [`apps/web/src/components/FactChips.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/FactChips.tsx)
* **Styles**: [`apps/web/src/App.css#L1120-L1180`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css#L1120-L1180)
* **Parent Container**: `<section className="results-section">` in `ResultsView.tsx`
* **Sprint Modified**: Sprint 4 (Phase 2 Two-Tier Grounding)
* **What It Renders**:
  - Editable chip list of extracted product facts.
  - Value badges: `.fact-value-core` (star/dot), `.fact-value-visual`, `.fact-value-trivia`.
* **Harmonization Recommendations**:
  - Verify indicator dots use warm accent tokens rather than harsh neon badges.

---

## 4. Base Design System Reference (The Source of Truth)

All harmonization updates must strictly reference the design tokens defined in [`apps/web/src/index.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/index.css):

### 4.1 Color Tokens
```css
/* Surfaces */
--paper: #e9edea;        /* Background of the entire page */
--card: #fbfcfb;         /* Base white for panels, cards, and modal sheets */
--tint: #f0f3f1;         /* Subtle neutral fill for hover states, inputs, and chips */
--line: #d3dad5;         /* Standard card and container borders */
--line-strong: #b4bdb7;  /* High-emphasis borders and active outlines */

/* Typography */
--ink: #14181a;          /* Primary dark headlines and body */
--ink-2: #444d51;        /* Secondary supporting text and metadata */
--ink-3: #66707a;        /* Muted hints, timestamps, and captions */

/* Semantic Meaning Accents (Reserved for function, never decoration) */
--rec: #e5352b;          /* Recording dot and critical warning */
--hook: #d95a07;         /* Hook line Kind and orange indicators */
--hook-bg: #fce8d9;
--concept: #2a55d4;      /* Concept/Body line Kind and blue indicators */
--concept-bg: #e2eafc;
--cta: #12805a;          /* CTA line Kind and green positive actions */
--cta-bg: #d8f1e5;
```

### 4.2 Typography & Fonts
- **Headlines & Masthead**: `'Bricolage Grotesque', 'Hind Siliguri', system-ui, sans-serif`
- **Body & Controls**: `'Hanken Grotesk', 'Hind Siliguri', system-ui, sans-serif`
- **Bangla Script Lines**: Clean font rendering with `lang="bn"` support and 1.55 line-height.

### 4.3 Corner Radii Hierarchy
- **Top-level Panels**: `border-radius: 20px;` (`.panel`, `.gate-card`)
- **Cards & Rows**: `border-radius: 12px;` (`.line`, `.angle-card`, `.tab`)
- **Buttons**: `border-radius: 10px;` (`.btn`, `.btn-primary`)
- **Chips, Pills, & Badges**: `border-radius: 999px;` or `border-radius: 6px;` (Must be standardized across kind, speaker, platform, and angle pills).

---

## 5. Sprint 6 Action Checklist for UI Harmonization

- [ ] **1. Script Line Meta Row & Visual Cue**:
  - Re-style `.ln-speaker-badge` to match `.kind` height, typography, and pill curvature.
  - Replace the sharp `border-left: 3px solid #0ea5e9` on `.ln-visual-cue` with an indented, soft editorial callout card using `var(--tint)` and `var(--line)`.
- [ ] **2. Creative Angles Section**:
  - Build responsive mobile presentation (horizontal swipeable rail or compact carousel with dot/snap paging).
  - Elevate `.angle-card` with warm borders, clean pill tags (`border-radius: 999px`), and tactile hover feedback.
- [ ] **3. Access Gate Modal**:
  - Wire auto-unlock on 5th OTP character completion.
  - Constrain mobile width with `max-width: min(440px, calc(100vw - 32px))` and responsive slot sizing.
  - Replace hardcoded Tailwind blues/slates with `--card`, `--line`, and `--ink`.
- [ ] **4. Lead Angle Pills in `SegmentCard.tsx`**:
  - Ensure `#1`, `#2` angle pills visually match the platform `.tag` components.
- [ ] **5. Verification**:
  - Test on viewport widths 360px (mobile), 768px (tablet), and 1280px (desktop).
  - Run `bun run lint:web` and `bun --filter web build`.
