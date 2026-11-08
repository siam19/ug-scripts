# Script Assistant: Frontend React Source & Architecture Reference

This document provides a complete, token-efficient reference of the frontend codebase for the **Sprint 2** engineering agent working on **Refining Script Generation & Regenerations** (`docs/sprints/2. Refining Script Generation & Regenerations/plan.md`).

To maximize agent context efficiency while preserving complete visibility of the UI, all HTML and CSS files are provided in full. In React/TypeScript components, internal function bodies and imperative algorithms are commented out with succinct descriptions. The entire component hierarchy, props, interfaces, state definitions, and JSX DOM structures are 100% intact.

---

## Table of Contents

1. [Sprint 2 Feature Context & Agent Goals](#1-sprint-2-feature-context--agent-goals)
2. [Project Directory Structure](#2-project-directory-structure)
3. [Shared Type Contracts & Schemas](#3-shared-type-contracts--schemas)
4. [HTML Source Files](#4-html-source-files)
   - [`apps/web/index.html`](#appswebindexhtml)
5. [CSS Stylesheet Source Files](#5-css-stylesheet-source-files)
   - [`apps/web/src/index.css`](#appswebsrcindexcss)
   - [`apps/web/src/App.css`](#appswebsrcappcss)
6. [React Components & Hooks (Frontend-Focused)](#6-react-components--hooks-frontend-focused)
   - [`apps/web/src/main.tsx`](#appswebsrcmaintsx)
   - [`apps/web/src/App.tsx`](#appswebsrcapptsx)
   - [`apps/web/src/types/form.ts`](#appswebsrctypesformts)
   - [`apps/web/src/hooks/useGenerateScript.ts`](#appswebsrchooksusegeneratescriptts)
   - [`apps/web/src/components/ErrorBanner.tsx`](#appswebsrccomponentserrorbannertsx)
   - [`apps/web/src/components/LoadingState.tsx`](#appswebsrccomponentsloadingstatetsx)
   - [`apps/web/src/components/ProductForm.tsx`](#appswebsrccomponentsproductformtsx)
   - [`apps/web/src/components/SegmentCard.tsx`](#appswebsrccomponentssegmentcardtsx)
   - [`apps/web/src/components/ResultsView.tsx`](#appswebsrccomponentsresultsviewtsx)
   - [`apps/web/src/components/ScriptCard.tsx`](#appswebsrccomponentsscriptcardtsx)
   - [`apps/web/src/components/ReasonList.tsx`](#appswebsrccomponentsreasonlisttsx)

---

## 1. Sprint 2 Feature Context & Agent Goals

The goal of Sprint 2 is to add customizability and regeneration options to refine the script generation experience:

1. **Editable Facts Chips**:
   - The chips in the first results section (`.chip-list`) become editable.
   - Show a faint edit icon and a cross icon to delete a chip.
   - Modifying facts renders the segment-section generation stale.
   - Allow regenerating the entire section with updated facts via an elegant, non-invasive visual cue (components inside remain interactable while stale).
2. **Customer Segment Regeneration**:
   - Tab buttons in the segment tablist show a regenerate icon (refresh icon) in the bottom-right corner on hover.
   - Clicking it requests a newly generated customer segment, replacing that specific tab and its `SegmentCard`.
3. **Segment Card Actions (Save & Edit)**:
   - Two buttons at the bottom-right corner of `.segment-main`:
     - **Save**: Adds this script to a "Saved Scripts" list (persisting even if the segment is replaced or edited).
     - **Edit**: Inline edit for the `h3` title, `segment-who`, and `tag-list`. Updating or regenerating marks its script stale with non-invasive regeneration options while keeping the workbench usable.
4. **Fine-Grained Workbench Line Group Regeneration & History**:
   - Reason buttons in `.reason-list` display a refresh icon at the bottom-right corner.
   - Clicking regenerates the associated lines referenced by `reason.line_ids`.
   - Each regeneration creates a new version for that highlighted group; a `< >` spinner selector appears halfway down the total height to switch between versions.
   - Clicking a line item (`li.line`) deselects the highlighted selection cleanly.
5. **Auto-Scroll Polish**:
   - Smoothly scroll down when customer segments are generated to bring customer segments and the workbench into full view.

### Engineering Notes & Constraints
- **Styling**: Handled in `apps/web/src/App.css` and `apps/web/src/index.css` using standard CSS and CSS custom properties (`--paper`, `--card`, `--ink`, `--concept`, `--hook`, `--cta`, etc.). Do not install Tailwind.
- **Icons**: Use `@tabler/icons-react` (already installed: `IconCopy`, `IconCheck`, `IconUsers`, and available icons like `IconRefresh`, `IconEdit`, `IconX`, `IconChevronLeft`, `IconChevronRight`, `IconBookmark`).
- **Data Types**: Re-exported strongly typed schemas from `packages/api-types` (`api-types`).

---

## 2. Project Directory Structure

```text
.
├── README.md
├── apps
│   ├── api                                  # FastAPI backend & streaming SSE
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── main.py                          # /generate and /generate-stream endpoints
│   │   ├── openapi.json
│   │   ├── prompts.py                       # Gemini system prompts & schemas
│   │   ├── pytest.ini
│   │   ├── requirements.txt
│   │   ├── schemas.py                       # Pydantic models (Segment, Script, etc.)
│   │   └── tests
│   │       ├── conftest.py
│   │       ├── test_generate.py
│   │       ├── test_health.py
│   │       └── test_validation.py
│   └── web                                  # React 18 + Vite frontend
│       ├── README.md
│       ├── index.html                       # HTML entry point
│       ├── package.json
│       ├── public
│       │   ├── favicon.svg
│       │   └── icons.svg
│       ├── src
│       │   ├── App.css                      # Complete application CSS styles
│       │   ├── App.tsx                      # Root component & form state
│       │   ├── index.css                    # Design system variables & resets
│       │   ├── main.tsx                     # React DOM root render
│       │   ├── components
│       │   │   ├── ErrorBanner.tsx          # Error display & retry banner
│       │   │   ├── LoadingState.tsx         # Staged animated loading panel
│       │   │   ├── ProductForm.tsx          # Inputs, drag-and-drop & paste photo
│       │   │   ├── ReasonList.tsx           # Interactive reasoning card list
│       │   │   ├── ResultsView.tsx          # Staggered tabs, workbench & cards
│       │   │   ├── ScriptCard.tsx           # Timeline bar, word count & lines
│       │   │   └── SegmentCard.tsx          # Segment demographic card
│       │   ├── hooks
│       │   │   └── useGenerateScript.ts     # SSE stream consumer hook
│       │   └── types
│       │       └── form.ts                  # Form-specific interfaces & constants
│       ├── tsconfig.app.json
│       ├── tsconfig.json
│       ├── tsconfig.node.json
│       └── vite.config.ts
├── bun.lock
├── docs
│   ├── Script Assistant API Project Plan.md
│   ├── frontend-dev-guide.md
│   ├── frontend-react-files.md
│   ├── sprints
│   │   └── 2. Refining Script Generation & Regenerations
│   │       ├── frontend-react-files-v2.md   # This document
│   │       ├── image.png                    # Editable facts chip mockup
│   │       ├── image-1.png                  # Reason line group version spinner (< >)
│   │       ├── plan.md                      # Sprint 2 specifications
│   │       └── script-line-select.png       # Line selection visual mockup
│   └── ugstar-94b38dd789aa.json
├── package.json
└── packages
    └── api-types                            # Shared OpenAPI TypeScript definitions
        ├── package.json
        ├── src
        │   ├── index.ts                     # TypeScript re-exports
        │   └── schema.d.ts                  # openapi-typescript generated schemas
        └── tsconfig.json
```

---

## 3. Shared Type Contracts & Schemas

### `packages/api-types/src/index.ts`

```ts
/**
 * Re-exports strongly typed schemas generated from the FastAPI OpenAPI specification.
 */
import type { components, paths } from './schema.d.ts';

export type GenerateResponse = components['schemas']['GenerateResponse'];
export type Segment = components['schemas']['Segment'];
export type Script = components['schemas']['Script'];
export type Line = components['schemas']['Line'];
export type Reason = components['schemas']['Reason'];
export type LineKind = components['schemas']['Line']['kind'];

export interface ProgressiveGenerateResponse {
  facts: string[];
  segments: Segment[];
  scripts: (Script | null)[];
}

export type { components, paths };
```

### TypeScript Schema Details

```ts
export interface Segment {
  name: string;        // e.g. "Exhausted Working Parents"
  who: string;         // Demographics, daily context, and life situation
  pain_point: string;  // Core frustration or unmet desire in their own words
  platforms: string[]; // e.g. ["TikTok", "Instagram Reels", "YouTube Shorts"]
}

export type LineKind = 'hook' | 'concept' | 'cta';

export interface Line {
  id: number;          // 1-based sequential line index
  kind: LineKind;      // 'hook' (0-3s), 'concept' (body), or 'cta' (action)
  text: string;        // Spoken dialogue or voiceover text
}

export interface Reason {
  title: string;       // Short name of performance marketing technique
  why: string;         // Explanation of why this technique resonates
  line_ids: number[];  // 1-based line IDs from the script cited by this reason
}

export interface Script {
  segment: string;     // Customer segment name this script belongs to
  lines: Line[];       // Ordered sequence of script lines
  reasons: Reason[];   // Exactly 3 reasons explaining the script structure
}

export interface ProgressiveGenerateResponse {
  facts: string[];
  segments: Segment[];
  scripts: (Script | null)[];
}
```

---

## 4. HTML Source Files

### `apps/web/index.html`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>UG-Scripts</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

---

## 5. CSS Stylesheet Source Files

### `apps/web/src/index.css`

```css
/* apps/web/src/index.css */
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Hanken+Grotesk:wght@400;500;600;700&family=Hind+Siliguri:wght@400;500;600&display=swap');

:root {
  /* Surfaces */
  --paper: #e9edea;
  --card: #fbfcfb;
  --tint: #f0f3f1;
  --line: #d3dad5;
  --line-strong: #b4bdb7;

  /* Text */
  --ink: #14181a;
  --ink-2: #444d51;
  --ink-3: #66707a;

  /* Accents: color is reserved for meaning */
  --rec: #e5352b;
  --hook: #d95a07;
  --hook-bg: #fce8d9;
  --concept: #2a55d4;
  --concept-bg: #e2eafc;
  --cta: #12805a;
  --cta-bg: #d8f1e5;

  --err-bg: #fcebe9;
  --err-line: #e4b0aa;
  --err-ink: #85201a;

  --font-display: 'Bricolage Grotesque', 'Hind Siliguri', system-ui, sans-serif;
  --font-body: 'Hanken Grotesk', 'Hind Siliguri', system-ui, sans-serif;

  color-scheme: light;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  -webkit-text-size-adjust: 100%;
}

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

h1,
h2,
h3,
p,
figure,
blockquote {
  margin: 0;
}

ol,
ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

button,
input,
select,
textarea {
  font: inherit;
  color: inherit;
}

button {
  cursor: pointer;
}

:focus-visible {
  outline: 2px solid var(--concept);
  outline-offset: 2px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

### `apps/web/src/App.css`

```css
/* apps/web/src/App.css */

/* ---------- Kind colors (hook / concept / cta) ---------- */
[data-kind='hook'] {
  --kind: var(--hook);
  --kind-bg: var(--hook-bg);
}
[data-kind='concept'] {
  --kind: var(--concept);
  --kind-bg: var(--concept-bg);
}
[data-kind='cta'] {
  --kind: var(--cta);
  --kind-bg: var(--cta-bg);
}

/* ---------- Layout ---------- */
.shell {
  max-width: 1120px;
  margin: 0 auto;
  padding: 28px 24px 96px;
}

.masthead {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.0625rem;
}

.rec-dot {
  flex: none;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--rec);
}

.hero {
  padding: 56px 0 36px;
}

.hero h1 {
  max-width: 20ch;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(2.1rem, 5vw, 3.6rem);
  line-height: 1.04;
  letter-spacing: -0.025em;
}

.hero p {
  max-width: 54ch;
  margin-top: 16px;
  color: var(--ink-2);
  font-size: 1.125rem;
}

.panel {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 28px;
}

.hint {
  color: var(--ink-3);
  font-size: 0.8125rem;
  line-height: 1.45;
}

/* ---------- Buttons ---------- */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  height: 46px;
  padding: 0 20px;
  border: 1px solid transparent;
  border-radius: 10px;
  font-weight: 600;
  transition: background-color 0.15s, border-color 0.15s, color 0.15s;
}

.btn-primary {
  background: var(--ink);
  color: #fff;
}
.btn-primary:hover:not(:disabled) {
  background: #2b3337;
}
.btn-primary:disabled {
  background: #aeb6b1;
  cursor: not-allowed;
}

.btn-quiet {
  height: 38px;
  padding: 0 14px;
  background: transparent;
  border-color: var(--line-strong);
  font-size: 0.9375rem;
}
.btn-quiet:hover {
  border-color: var(--ink);
}
.btn-quiet.is-done {
  color: var(--cta);
  border-color: var(--cta);
}

/* ---------- Form ---------- */
.form-grid {
  display: grid;
  gap: 32px;
}

.form-fields {
  display: grid;
  gap: 20px;
  align-content: start;
}

.field-row {
  display: grid;
  gap: 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.field > label,
.field > .label {
  font-size: 0.875rem;
  font-weight: 600;
}

.field input[type='text'],
.field select,
.field textarea {
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
}

.field textarea {
  resize: vertical;
  line-height: 1.5;
}

.field input::placeholder,
.field textarea::placeholder {
  color: var(--ink-3);
}

.field-error {
  color: var(--err-ink);
  font-size: 0.875rem;
}

.segmented {
  display: inline-flex;
  align-self: flex-start;
  padding: 3px;
  background: #fff;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
}

.segmented label {
  position: relative;
  cursor: pointer;
}

.segmented input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.segmented span {
  display: block;
  padding: 8px 18px;
  border-radius: 7px;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--ink-2);
  transition: background-color 0.15s, color 0.15s;
}

.segmented input:checked + span {
  background: var(--ink);
  color: #fff;
}

.segmented input:focus-visible + span {
  outline: 2px solid var(--concept);
  outline-offset: 2px;
}

/* Photo upload */
.photo-field {
  min-height: 280px;
}

.dropzone {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 240px;
  padding: 24px;
  text-align: center;
  color: var(--ink-2);
  background: var(--tint);
  border: 1.5px dashed var(--line-strong);
  border-radius: 14px;
  cursor: pointer;
  transition: background-color 0.15s, border-color 0.15s;
}
.dropzone strong {
  color: var(--ink);
}
.dropzone:hover,
.dropzone.is-dragging {
  background: #fff;
  border-color: var(--ink);
}

.file-input:focus-visible + .dropzone {
  outline: 2px solid var(--concept);
  outline-offset: 2px;
}

.photo-preview {
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  background: var(--tint);
  border: 1px solid var(--line);
  border-radius: 14px;
}

.photo-preview img {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 200px;
  max-height: 300px;
  flex: 1;
  object-fit: contain;
  background: var(--tint);
}

.photo-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--card);
  border-top: 1px solid var(--line);
}

.photo-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.9375rem;
  font-weight: 500;
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid var(--line);
}

/* ---------- Output area ---------- */
.output {
  margin-top: 40px;
  scroll-margin-top: 16px;
}

.empty {
  max-width: 56ch;
  padding: 32px 0;
}
.empty h2 {
  font-family: var(--font-display);
  font-size: 1.375rem;
}
.empty p {
  margin-top: 8px;
  color: var(--ink-2);
}

/* Loading */
.loading {
  display: grid;
  gap: 24px;
}

.loading-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.loading-head h2 {
  font-family: var(--font-display);
  font-size: 1.375rem;
}

.progress {
  height: 6px;
  overflow: hidden;
  background: var(--line);
  border-radius: 3px;
}
.progress span {
  display: block;
  height: 100%;
  background: var(--ink);
  transition: width 0.4s ease-out;
}

.stages {
  display: grid;
  gap: 16px;
}

.stage {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.stage p {
  color: var(--ink-3);
  font-size: 0.9375rem;
}
.stage.is-pending {
  opacity: 0.5;
}

.stage-mark {
  flex: none;
  width: 14px;
  height: 14px;
  margin-top: 4px;
  border: 2px solid var(--line-strong);
  border-radius: 50%;
}
.stage.is-active .stage-mark {
  border-color: var(--rec);
  background: var(--rec);
  animation: pulse 1.2s ease-in-out infinite;
}
.stage.is-done .stage-mark {
  border-color: var(--cta);
  background: var(--cta);
}

@keyframes pulse {
  50% {
    opacity: 0.35;
  }
}

.skeleton {
  display: grid;
  gap: 10px;
}
.skeleton span {
  display: block;
  height: 14px;
  background: var(--tint);
  border-radius: 7px;
}
.skeleton span:nth-child(1) {
  width: 92%;
}
.skeleton span:nth-child(2) {
  width: 78%;
}
.skeleton span:nth-child(3) {
  width: 60%;
}

/* Error */
.error-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 20px 24px;
  background: var(--err-bg);
  border: 1px solid var(--err-line);
  border-left: 4px solid var(--rec);
  border-radius: 14px;
  color: var(--err-ink);
}
.error-copy {
  display: grid;
  gap: 4px;
  max-width: 62ch;
}
.error-copy .hint {
  color: #9a4a44;
}
.error-actions {
  display: flex;
  gap: 10px;
}

/* ---------- Results ---------- */
.results {
  display: grid;
  gap: 40px;
}

.results-section {
  display: grid;
  gap: 16px;
}

.section-head h2 {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-display);
  font-size: 1.375rem;
  line-height: 1.2;
}
.section-head p {
  margin-top: 4px;
  color: var(--ink-2);
}

.section-title-icon {
  flex: none;
  color: var(--rec);
}

@keyframes popIn {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.chip-animated {
  animation: popIn 0.28s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.tab-animated {
  animation: popIn 0.32s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.segment-section-animated {
  animation: popIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@media (prefers-reduced-motion: reduce) {
  .chip-animated,
  .tab-animated,
  .segment-section-animated {
    animation: none;
  }
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  padding: 7px 12px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 0.9375rem;
}

/* Tabs */
.tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.tab {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 16px;
  text-align: left;
  background: transparent;
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.25;
  transition: background-color 0.15s, border-color 0.15s, color 0.15s;
}
.tab:hover {
  border-color: var(--ink);
}
.tab.is-active {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}

.tab-status-dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--rec);
  animation: pulse 1.2s ease-in-out infinite;
}

.script-skeleton-card {
  display: grid;
  gap: 16px;
  padding: 28px;
  background: var(--card);
  border: 1px dashed var(--line-strong);
  border-radius: 20px;
}

.script-skeleton-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.script-skeleton-head h3 {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 600;
}

.tab-panel {
  display: grid;
  gap: 20px;
}

/* Segment card */
.segment-card {
  display: grid;
  gap: 24px;
}
.segment-main {
  display: grid;
  gap: 12px;
  align-content: start;
}
.segment-main h3 {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-display);
  font-size: 1.5rem;
  line-height: 1.15;
}

.segment-title-icon {
  flex: none;
  color: var(--rec);
}
.segment-who {
  max-width: 60ch;
  color: var(--ink-2);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tag {
  padding: 3px 11px;
  background: #e5eae7;
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--ink-2);
}

.pain {
  display: grid;
  gap: 8px;
  align-content: start;
  padding: 20px;
  background: var(--tint);
  border-radius: 14px;
}
.pain figcaption {
  color: var(--ink-3);
  font-size: 0.8125rem;
}
.pain blockquote {
  font-family: var(--font-display);
  font-size: 1.1875rem;
  font-weight: 600;
  line-height: 1.35;
}

/* Workbench: script + reasons */
.workbench {
  display: grid;
  gap: 20px;
  align-items: start;
}

.script-card h3,
.reasons h3 {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-display);
  font-size: 1.25rem;
  line-height: 1.2;
}

.script-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

/* Timeline: the script's structure at a glance */
.timeline-wrap {
  position: relative;
  margin: 22px 0 8px;
  padding-bottom: 22px;
}
.timeline {
  display: flex;
  gap: 3px;
  height: 10px;
  animation: wipe 0.8s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
.tl-seg {
  min-width: 6px;
  background: var(--kind);
  border-radius: 3px;
  opacity: 0.5;
  transition: opacity 0.15s;
}
.tl-seg.is-on {
  opacity: 1;
}
.tl-tick {
  position: absolute;
  top: -5px;
  width: 2px;
  height: 20px;
  margin-left: -1px;
  background: var(--ink);
}
.tl-tick-label {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  color: var(--ink-2);
  font-size: 0.75rem;
  white-space: nowrap;
}

@keyframes wipe {
  from {
    clip-path: inset(0 100% 0 0);
  }
  to {
    clip-path: inset(0 0 0 0);
  }
}

/* Script lines */
.lines {
  display: grid;
  gap: 4px;
}

.line {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 12px;
  padding: 14px 14px 14px 12px;
  border-left: 3px solid transparent;
  border-radius: 12px;
  transition: background-color 0.12s, opacity 0.12s, border-color 0.12s;
}
.line.is-hover {
  background: var(--tint);
}
.line.is-lit {
  background: var(--kind-bg);
  border-left-color: var(--kind);
}
.line.is-dim {
  opacity: 0.45;
}

.ln-gutter {
  display: grid;
  gap: 2px;
  align-content: start;
  justify-items: start;
}
.ln-id {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.2;
}
.ln-time {
  color: var(--ink-3);
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
}

.ln-body {
  display: grid;
  gap: 6px;
  justify-items: start;
}
.kind {
  padding: 2px 9px;
  background: var(--kind-bg);
  border-radius: 6px;
  color: var(--kind);
  font-size: 0.8125rem;
  font-weight: 700;
}
.line.is-lit .kind {
  background: #fff;
}
.ln-text {
  font-size: 1.1875rem;
  line-height: 1.55;
}

/* Reasons */
.reasons {
  display: grid;
  gap: 10px;
}
.reason-list {
  display: grid;
  gap: 10px;
  margin-top: 6px;
}

.reason {
  display: grid;
  gap: 8px;
  width: 100%;
  padding: 16px;
  text-align: left;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  transition: background-color 0.12s, border-color 0.12s;
}
.reason:hover {
  border-color: var(--line-strong);
}
.reason.is-lit,
.reason[aria-pressed='true'] {
  background: var(--tint);
  border-color: var(--ink);
}

.reason-title {
  font-family: var(--font-display);
  font-size: 1.0625rem;
  font-weight: 600;
  line-height: 1.25;
}
.reason-why {
  color: var(--ink-2);
  font-size: 0.9375rem;
  line-height: 1.5;
}
.reason-lines {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.line-ref {
  padding: 2px 9px;
  background: var(--kind-bg, #e5eae7);
  border-radius: 6px;
  color: var(--kind, var(--ink-2));
  font-size: 0.8125rem;
  font-weight: 700;
}

/* ---------- Responsive ---------- */
@media (min-width: 700px) {
  .field-row {
    grid-template-columns: 1fr 1fr;
  }
  .segment-card {
    grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
    gap: 32px;
  }
}

@media (min-width: 900px) {
  .form-grid {
    grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
    gap: 36px;
  }
}

@media (min-width: 980px) {
  .workbench {
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  }
  .reasons {
    position: sticky;
    top: 20px;
  }
}

@media (max-width: 699px) {
  .shell {
    padding: 20px 16px 72px;
  }
  .hero {
    padding: 36px 0 24px;
  }
  .panel {
    padding: 20px;
  }
  .tabs {
    grid-template-columns: none;
    grid-auto-flow: column;
    grid-auto-columns: minmax(180px, 70%);
    overflow-x: auto;
    padding-bottom: 4px;
  }
  .form-actions .btn {
    width: 100%;
  }
  .script-head {
    flex-wrap: wrap;
  }
}
```

---

## 6. React Components & Hooks (Frontend-Focused)

> **Context-Saving Note**: All function inner bodies and computational loops have been commented out with descriptions of their behavior. The entire component tree, JSX markup, state hooks, element classNames, ARIA roles, and event bindings are completely preserved.

### `apps/web/src/main.tsx`

```tsx
// apps/web/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

---

### `apps/web/src/App.tsx`

```tsx
// apps/web/src/App.tsx
import { useRef, useState } from 'react';
import './App.css';
import { ProductForm } from './components/ProductForm';
import { LoadingState } from './components/LoadingState';
import { ResultsView } from './components/ResultsView';
import { ErrorBanner } from './components/ErrorBanner';
import { useGenerateScript } from './hooks/useGenerateScript';
import { INITIAL_VALUES } from './types/form';
import type { FormValues } from './types/form';

export default function App() {
  // Form values live here, so they survive loading, errors and retries.
  const [values, setValues] = useState<FormValues>(INITIAL_VALUES);
  const { status, data, error, runId, generate, retry, clearError } = useGenerateScript();
  const outputRef = useRef<HTMLElement>(null);

  function patch(update: Partial<FormValues>) {
    /* Updates form values: setValues((v) => ({ ...v, ...update })); */
  }

  function scrollToOutput() {
    /* Smooth scrolls outputRef into view */
  }

  function handleSubmit() {
    /* void generate(values); scrollToOutput(); */
  }

  function handleRetry() {
    /* retry(); scrollToOutput(); */
  }

  return (
    <div className="shell">
      <header className="masthead">
        <span className="rec-dot" aria-hidden="true" />
        Script Assistant
      </header>

      <section className="hero">
        <h1>UG-Scripts</h1>
        <p>
          Describe the product, add its photo, and get three customer segments with a
          phone-ready UGC ad script for each.
        </p>
      </section>

      <ProductForm
        values={values}
        onChange={patch}
        onSubmit={handleSubmit}
        submitting={status === 'loading' || status === 'streaming'}
      />

      <section ref={outputRef} className="output" aria-label="Generated scripts">
        {status === 'idle' && (
          <div className="empty">
            <h2>Your scripts will appear here</h2>
            <p>
              Fill in the product details and add a photo. You will get 3 customer
              segments, one script for each, and 3 reasons per script.
            </p>
          </div>
        )}

        {status === 'loading' && !data && <LoadingState />}

        {status === 'error' && error && (
          <ErrorBanner error={error} onRetry={handleRetry} onDismiss={clearError} />
        )}

        {data && <ResultsView key={runId} data={data} isStreaming={status === 'streaming'} />}
      </section>
    </div>
  );
}
```

---

### `apps/web/src/types/form.ts`

```ts
// apps/web/src/types/form.ts

export type Language = 'en' | 'bn';

export interface FormValues {
  name: string;
  description: string;
  category: string;
  market: string;
  language: Language;
  image: File | null;
}

export const INITIAL_VALUES: FormValues = {
  name: '',
  description: '',
  category: 'Skincare',
  market: 'Bangladesh',
  language: 'en',
  image: null,
};

export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export const ACCEPTED_IMAGE_TYPES: string[] = ['image/jpeg', 'image/png', 'image/webp'];
export const MAX_MARKET_LENGTH = 60;
```

---

### `apps/web/src/hooks/useGenerateScript.ts`

```tsx
// apps/web/src/hooks/useGenerateScript.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ProgressiveGenerateResponse, Script, Segment } from 'api-types';
import type { FormValues } from '../types/form';

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_KEY: string = import.meta.env.VITE_API_KEY ?? '';
const TIMEOUT_MS = 90_000;

export type Status = 'idle' | 'loading' | 'streaming' | 'success' | 'error';

export interface FriendlyError {
  title: string;
  message: string;
}

interface SegmentsEvent {
  event: 'segments';
  facts: string[];
  segments: Segment[];
}

interface ScriptEvent {
  event: 'script';
  index: number;
  script: Script;
}

interface DoneEvent {
  event: 'done';
}

interface ErrorEvent {
  event: 'error';
  detail: string;
}

type StreamEvent = SegmentsEvent | ScriptEvent | DoneEvent | ErrorEvent;

const TIMEOUT_ERROR: FriendlyError = {
  title: 'This took too long',
  message: 'The server did not answer within 90 seconds. Try again; if it keeps happening, the AI service may be busy.',
};

const NETWORK_ERROR: FriendlyError = {
  title: "Can't reach the server",
  message: 'Check your connection and that the API is running, then try again.',
};

const BAD_RESPONSE_ERROR: FriendlyError = {
  title: 'Unexpected response',
  message: 'The server replied, but the result was incomplete. Try again.',
};

function errorForStatus(status: number, detail?: string): FriendlyError {
  /* Maps HTTP 401, 413, 415, 422, 502, 503, 504 status codes to user-facing FriendlyError */
  return { title: 'Something went wrong', message: detail ?? `The server responded with status ${status}.` };
}

export function useGenerateScript() {
  const [status, setStatus] = useState<Status>('idle');
  const [data, setData] = useState<ProgressiveGenerateResponse | null>(null);
  const [error, setError] = useState<FriendlyError | null>(null);
  const [runId, setRunId] = useState(0);

  const lastValues = useRef<FormValues | null>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => {
    /* Cleanup / abort on unmount: controller.current?.abort() */
  }, []);

  const generate = useCallback(async (values: FormValues) => {
    /* Initiates multipart POST to `${API_URL}/generate-stream` with 90s timeout.
       Consumes Server-Sent Events (SSE):
       - 'segments': initializes data.facts and data.segments, scripts array filled with nulls.
       - 'script': progressively updates data.scripts[index] with received script object.
       - 'done': transitions status to 'success'.
       - 'error': handles error response or payload. */
  }, []);

  const retry = useCallback(() => {
    /* Re-executes generate with lastValues.current */
  }, [generate]);

  const clearError = useCallback(() => {
    /* Clears error and reverts status from 'error' to 'idle' */
  }, []);

  return { status, data, error, runId, generate, retry, clearError };
}
```

---

### `apps/web/src/components/ErrorBanner.tsx`

```tsx
// apps/web/src/components/ErrorBanner.tsx
import type { FriendlyError } from '../hooks/useGenerateScript';

interface Props {
  error: FriendlyError;
  onRetry: () => void;
  onDismiss: () => void;
}

export function ErrorBanner({ error, onRetry, onDismiss }: Props) {
  return (
    <div className="error-banner" role="alert">
      <div className="error-copy">
        <strong>{error.title}</strong>
        <p>{error.message}</p>
        <p className="hint">Your form is unchanged, so you can retry or edit it first.</p>
      </div>
      <div className="error-actions">
        <button type="button" className="btn btn-primary" onClick={onRetry}>
          Try again
        </button>
        <button type="button" className="btn btn-quiet" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}
```

---

### `apps/web/src/components/LoadingState.tsx`

```tsx
// apps/web/src/components/LoadingState.tsx
import { useEffect, useState } from 'react';

const STAGES = [
  {
    title: 'Analyzing packaging and verifying facts',
    note: 'Reading the photo and your description for claims the scripts can safely use.',
  },
  {
    title: 'Writing 3 creator scripts',
    note: 'One script per customer segment, each with its own hook style.',
  },
];

const STAGE_ONE_SECONDS = 7;

export function LoadingState() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    /* 250ms interval timer tracking elapsed time in seconds */
  }, []);

  const stage = elapsed < STAGE_ONE_SECONDS ? 0 : 1;
  const percent = Math.round(92 * (1 - Math.exp(-elapsed / 12)));

  return (
    <div className="panel loading" role="status" aria-live="polite">
      <div className="loading-head">
        <h2>Writing your scripts</h2>
        <span className="hint">{Math.floor(elapsed)}s elapsed. Usually 10 to 20 seconds.</span>
      </div>

      <div className="progress" aria-hidden="true">
        <span style={{ width: `${percent}%` }} />
      </div>

      <ol className="stages">
        {STAGES.map((s, i) => {
          const state = i < stage ? 'done' : i === stage ? 'active' : 'pending';
          return (
            <li key={s.title} className={`stage is-${state}`}>
              <span className="stage-mark" aria-hidden="true" />
              <div>
                <strong>{s.title}</strong>
                <p>{s.note}</p>
              </div>
            </li>
          );
        })}
      </ol>

      {elapsed > 25 && (
        <p className="hint">
          This is taking longer than usual. The request is still running.
        </p>
      )}

      <div className="skeleton" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
```

---

### `apps/web/src/components/ProductForm.tsx`

```tsx
// apps/web/src/components/ProductForm.tsx
import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, FormEvent } from 'react';
import {
  ACCEPTED_IMAGE_TYPES,
  MAX_IMAGE_BYTES,
  MAX_MARKET_LENGTH,
} from '../types/form';
import type { FormValues, Language } from '../types/form';

const CATEGORIES = [
  'Skincare',
  'Tech / Gadgets',
  'Fashion',
  'Food & Beverage',
  'Home & Living',
];
const OTHER = '__other__';

const LANGUAGES: { value: Language; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'bn', label: 'Bangla' },
];

interface Props {
  values: FormValues;
  onChange: (patch: Partial<FormValues>) => void;
  onSubmit: () => void;
  submitting: boolean;
}

function formatBytes(bytes: number): string {
  /* Returns formatted size string (e.g. "120 KB", "2.4 MB") */
  return bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function ProductForm({ values, onChange, onSubmit, submitting }: Props) {
  const uid = useId();
  const id = (key: string) => `${uid}-${key}`;

  const [customCategory, setCustomCategory] = useState(
    !CATEGORIES.includes(values.category),
  );
  const [dragging, setDragging] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  // Thumbnail preview derived from values.image; object URLs revoked on change or unmount.
  const previewUrl = useMemo(() => {
    /* Derives object URL from values.image */
    if (!values.image) return null;
    return URL.createObjectURL(values.image);
  }, [values.image]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const acceptFile = useCallback(
    (file: File | undefined) => {
      /* Validates file type and size (<=5MB), sets imageError or calls onChange({ image: file }) */
    },
    [onChange],
  );

  // Listen for Ctrl+V / Cmd+V paste events containing image data
  useEffect(() => {
    /* Global window paste listener for clipboard image data */
  }, [acceptFile]);

  function handleFileInput(e: ChangeEvent<HTMLInputElement>) {
    /* Calls acceptFile(e.target.files?.[0]) and resets value */
  }

  function handleDrop(e: DragEvent<HTMLLabelElement>) {
    /* Handles dropzone drop, cancels dragging state, and calls acceptFile */
  }

  function removeImage() {
    /* setImageError(null); onChange({ image: null }); fileInput reset */
  }

  function handleCategory(e: ChangeEvent<HTMLSelectElement>) {
    /* Handles category change; toggles customCategory if OTHER selected */
  }

  const missing: string[] = [];
  if (!values.name.trim()) missing.push('product name');
  if (!values.category.trim()) missing.push('category');
  if (!values.market.trim()) missing.push('market');
  if (!values.description.trim()) missing.push('description');
  if (!values.image) missing.push('photo');
  const canSubmit = missing.length === 0 && !submitting;

  function handleSubmit(e: FormEvent) {
    /* e.preventDefault(); if (canSubmit) onSubmit(); */
  }

  return (
    <form className="panel product-form" onSubmit={handleSubmit} noValidate>
      <div className="form-grid">
        <div className="form-fields">
          <div className="field-row">
            <div className="field">
              <label htmlFor={id('name')}>Product name</label>
              <input
                id={id('name')}
                type="text"
                required
                value={values.name}
                placeholder="GlowHydrate Serum"
                onChange={(e) => onChange({ name: e.target.value })}
              />
            </div>

            <div className="field">
              <label htmlFor={id('category')}>Category</label>
              <select
                id={id('category')}
                value={customCategory ? OTHER : values.category}
                onChange={handleCategory}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
                <option value={OTHER}>Other</option>
              </select>
              {customCategory && (
                <input
                  type="text"
                  aria-label="Custom category"
                  value={values.category}
                  placeholder="Type a category"
                  onChange={(e) => onChange({ category: e.target.value })}
                />
              )}
            </div>
          </div>

          <div className="field-row">
            <div className="field">
              <label htmlFor={id('market')}>Market</label>
              <input
                id={id('market')}
                type="text"
                required
                maxLength={MAX_MARKET_LENGTH}
                value={values.market}
                onChange={(e) => onChange({ market: e.target.value })}
              />
              <span className="hint">
                {values.market.length}/{MAX_MARKET_LENGTH} characters
              </span>
            </div>

            <div className="field">
              <span className="label" id={id('lang')}>
                Script language
              </span>
              <div className="segmented" role="radiogroup" aria-labelledby={id('lang')}>
                {LANGUAGES.map((l) => (
                  <label key={l.value}>
                    <input
                      type="radio"
                      name={id('language')}
                      value={l.value}
                      checked={values.language === l.value}
                      onChange={() => onChange({ language: l.value })}
                    />
                    <span>{l.label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="field">
            <label htmlFor={id('description')}>Product description</label>
            <textarea
              id={id('description')}
              rows={5}
              required
              value={values.description}
              placeholder="What it is, who it's for, key ingredients or specs, size, price. The more specific, the better the scripts."
              onChange={(e) => onChange({ description: e.target.value })}
            />
          </div>
        </div>

        <div className="field photo-field">
          <span className="label">Product photo</span>

          <input
            ref={fileInput}
            id={id('image')}
            className="sr-only file-input"
            type="file"
            accept={ACCEPTED_IMAGE_TYPES.join(',')}
            onChange={handleFileInput}
          />

          {values.image && previewUrl ? (
            <div className="photo-preview">
              <img src={previewUrl} alt="Product preview" />
              <div className="photo-meta">
                <span className="photo-name" title={values.image.name}>
                  {values.image.name}
                </span>
                <span className="hint">{formatBytes(values.image.size)}</span>
                <button type="button" className="btn btn-quiet" onClick={removeImage}>
                  Remove
                </button>
              </div>
            </div>
          ) : (
            <label
              htmlFor={id('image')}
              className={`dropzone${dragging ? ' is-dragging' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              <strong>Drop the product photo here</strong>
              <span>choose a file, or paste with Ctrl+V</span>
              <span className="hint">JPEG, PNG or WebP, up to 5 MB</span>
            </label>
          )}

          {imageError && (
            <p className="field-error" role="alert">
              {imageError}
            </p>
          )}
        </div>
      </div>

      <div className="form-actions">
        <p className="hint">
          {missing.length > 0
            ? `Still needed: ${missing.join(', ')}`
            : 'Takes 10 to 20 seconds'}
        </p>
        <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
          <span className="rec-dot" aria-hidden="true" />
          {submitting ? 'Generating…' : 'Generate UGC scripts'}
        </button>
      </div>
    </form>
  );
}
```

---

### `apps/web/src/components/SegmentCard.tsx`

```tsx
// apps/web/src/components/SegmentCard.tsx
import type { Segment } from 'api-types';
import { IconUsers } from '@tabler/icons-react';

interface Props {
  segment: Segment;
}

export function SegmentCard({ segment }: Props) {
  return (
    <article className="panel segment-card">
      <div className="segment-main">
        <h3>
          <IconUsers size={24} className="segment-title-icon" aria-hidden="true" />
          <span>{segment.name}</span>
        </h3>
        <p className="segment-who">{segment.who}</p>
        <ul className="tag-list" aria-label="Recommended platforms">
          {segment.platforms.map((p) => (
            <li key={p} className="tag">
              {p}
            </li>
          ))}
        </ul>
      </div>

      <figure className="pain">
        <figcaption>In their words</figcaption>
        <blockquote>&ldquo;{segment.pain_point}&rdquo;</blockquote>
      </figure>
    </article>
  );
}
```

---

### `apps/web/src/components/ResultsView.tsx`

```tsx
// apps/web/src/components/ResultsView.tsx
import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { ProgressiveGenerateResponse } from 'api-types';
import { SegmentCard } from './SegmentCard';
import { ScriptCard } from './ScriptCard';
import { ReasonList } from './ReasonList';

interface Props {
  data: ProgressiveGenerateResponse;
  isStreaming?: boolean;
}

export function ResultsView({ data, isStreaming = false }: Props) {
  const uid = useId();
  const [active, setActive] = useState(0);
  const [pinnedReason, setPinnedReason] = useState<number | null>(null);
  const [hoverReason, setHoverReason] = useState<number | null>(null);
  const [hoverLine, setHoverLine] = useState<number | null>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const totalFacts = data.facts.length;
  const totalSegments = data.segments.length;

  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Staggered population: populate facts chips first, then customer segments
  const [visibleFactsCount, setVisibleFactsCount] = useState(() =>
    prefersReducedMotion ? totalFacts : 0,
  );
  const [visibleSegmentsCount, setVisibleSegmentsCount] = useState(() =>
    prefersReducedMotion ? totalSegments : 0,
  );

  useEffect(() => {
    /* Timer logic that staggers revealing facts first, then customer segments */
  }, [
    visibleFactsCount,
    visibleSegmentsCount,
    totalFacts,
    totalSegments,
    prefersReducedMotion,
  ]);

  const segment = data.segments[active];
  const script = data.scripts[active];

  function selectSegment(index: number) {
    /* Updates active segment tab index and resets hover/pinned reason & line state */
  }

  function handleTabKey(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    /* ArrowRight/ArrowLeft keyboard navigation across active tabs */
  }

  // Bi-directional highlighting:
  // Reason -> lines: hovered reason wins over pinned reason
  const focusedReason = hoverReason ?? pinnedReason;
  const litLineIds = new Set<number>(
    focusedReason !== null ? (script?.reasons[focusedReason]?.line_ids ?? []) : [],
  );

  // Line -> reasons: hovering a line highlights all reasons referencing it
  const litReasonIndexes = new Set<number>();
  if (hoverLine !== null && script) {
    script.reasons.forEach((r, i) => {
      if (r.line_ids.includes(hoverLine)) litReasonIndexes.add(i);
    });
  } else if (focusedReason !== null) {
    litReasonIndexes.add(focusedReason);
  }

  return (
    <div className="results">
      {totalFacts > 0 && (
        <section className="results-section">
          <div className="section-head">
            <h2>Facts the scripts rely on</h2>
            <p>Pulled from your description and photo. The scripts only use these.</p>
          </div>
          <ul className="chip-list">
            {data.facts.slice(0, visibleFactsCount).map((fact, i) => (
              <li key={i} className="chip chip-animated">
                {fact}
              </li>
            ))}
          </ul>
        </section>
      )}

      {visibleSegmentsCount > 0 && (
        <section className="results-section segment-section-animated">
          <div className="section-head">
            <h2>Customer segments</h2>
            <p>
              Auto-generated target demographics based on your product details and packaging.
              Each segment has its own tailored script—switch between them without waiting.
            </p>
          </div>

          <div className="tabs" role="tablist" aria-label="Customer segments">
            {data.segments.slice(0, visibleSegmentsCount).map((s, i) => {
              const isReady = Boolean(data.scripts[i]);
              return (
                <button
                  key={`${s.name}-${i}`}
                  ref={(el) => {
                    tabRefs.current[i] = el;
                  }}
                  type="button"
                  role="tab"
                  id={`${uid}-tab-${i}`}
                  aria-selected={active === i}
                  aria-controls={`${uid}-panel`}
                  tabIndex={active === i ? 0 : -1}
                  className={`tab tab-animated${active === i ? ' is-active' : ''}`}
                  onClick={() => selectSegment(i)}
                  onKeyDown={(e) => handleTabKey(e, i)}
                >
                  <span>
                    {i + 1}. {s.name}
                  </span>
                  {isStreaming && !isReady && (
                    <span
                      className="tab-status-dot"
                      title="Generating script…"
                      aria-label="Generating script"
                    />
                  )}
                </button>
              );
            })}
          </div>

          <div
            className="tab-panel"
            role="tabpanel"
            id={`${uid}-panel`}
            aria-labelledby={`${uid}-tab-${active}`}
          >
            {segment && <SegmentCard segment={segment} />}

            {script ? (
              <div className="workbench">
                <ScriptCard
                  key={active}
                  script={script}
                  litLineIds={litLineIds}
                  hoveredLineId={hoverLine}
                  reasonFocused={focusedReason !== null}
                  onLineHover={setHoverLine}
                />
                <ReasonList
                  reasons={script.reasons}
                  lines={script.lines}
                  litIndexes={litReasonIndexes}
                  pinnedIndex={pinnedReason}
                  onHover={setHoverReason}
                  onPin={(i) => setPinnedReason((p) => (p === i ? null : i))}
                />
              </div>
            ) : isStreaming ? (
              <div className="panel script-skeleton-card">
                <div className="script-skeleton-head">
                  <span className="rec-dot" aria-hidden="true" />
                  <h3>Writing script for {segment?.name ?? 'segment'}…</h3>
                </div>
                <p className="hint">Crafting hook, timestamped lines, and psychological reasoning…</p>
                <div className="skeleton" aria-hidden="true">
                  <span style={{ height: '20px', width: '92%' }} />
                  <span style={{ height: '20px', width: '78%' }} />
                  <span style={{ height: '20px', width: '85%' }} />
                  <span style={{ height: '20px', width: '60%' }} />
                </div>
              </div>
            ) : (
              <p className="hint">No script came back for this segment. Try generating again.</p>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
```

---

### `apps/web/src/components/ScriptCard.tsx`

```tsx
// apps/web/src/components/ScriptCard.tsx
import { useEffect, useMemo, useRef, useState } from 'react';
import type { LineKind, Script } from 'api-types';
import { IconCopy, IconCheck } from '@tabler/icons-react';

const SECONDS_PER_WORD = 0.4; // roughly 2.5 spoken words per second
const HOOK_WINDOW_SECONDS = 3;

const KIND_LABEL: Record<LineKind, string> = {
  hook: 'Hook',
  concept: 'Concept',
  cta: 'Call to action',
};

function countWords(text: string): number {
  /* Counts words separated by whitespace */
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function mmss(seconds: number): string {
  /* Formats seconds to mm:ss */
  const total = Math.round(seconds);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

async function copyToClipboard(text: string): Promise<void> {
  /* Copies text using navigator.clipboard or fallback textarea */
}

interface Props {
  script: Script;
  /** Line ids highlighted because a reason is hovered or pinned. */
  litLineIds: ReadonlySet<number>;
  hoveredLineId: number | null;
  /** True while a reason is active, so unrelated lines can fade back. */
  reasonFocused: boolean;
  onLineHover: (id: number | null) => void;
}

export function ScriptCard({
  script,
  litLineIds,
  hoveredLineId,
  reasonFocused,
  onLineHover,
}: Props) {
  const [copied, setCopied] = useState(false);
  const copyTimer = useRef<number | null>(null);

  useEffect(() => () => {
    /* Clears copyTimer on unmount */
  }, []);

  const timed = useMemo(() => {
    /* Sorts lines by id, calculates cumulative words, line duration, and start time */
    const lines = [...script.lines].sort((a, b) => a.id - b.id);
    let cursor = 0;
    let totalWords = 0;
    const rows = lines.map((line) => {
      const words = countWords(line.text);
      const duration = Math.max(words * SECONDS_PER_WORD, 0.8);
      const start = cursor;
      cursor += duration;
      totalWords += words;
      return { line, words, duration, start };
    });
    return { rows, total: cursor, words: totalWords };
  }, [script.lines]);

  async function handleCopy() {
    /* Formats all lines, copies to clipboard, and sets copied flag for 2 seconds */
  }

  const tickPercent = Math.min(HOOK_WINDOW_SECONDS / (timed.total || 1), 1) * 100;

  return (
    <article className="panel script-card">
      <header className="script-head">
        <div>
          <h3>Script</h3>
          <p className="hint">
            About {Math.round(timed.total)} seconds spoken, {timed.words} words
          </p>
        </div>
        <button
          type="button"
          className={`btn btn-quiet${copied ? ' is-done' : ''}`}
          onClick={handleCopy}
        >
          {copied ? (
            <>
              <IconCheck size={16} aria-hidden="true" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <IconCopy size={16} aria-hidden="true" />
              <span>Copy script</span>
            </>
          )}
        </button>
      </header>

      <div className="timeline-wrap">
        <div className="timeline" aria-hidden="true">
          {timed.rows.map(({ line, duration }) => (
            <span
              key={line.id}
              className={`tl-seg${
                litLineIds.has(line.id) || hoveredLineId === line.id ? ' is-on' : ''
              }`}
              data-kind={line.kind}
              style={{ flexGrow: duration }}
            />
          ))}
        </div>
        <span className="tl-tick" style={{ left: `${tickPercent}%` }} aria-hidden="true">
          <span className="tl-tick-label">3s</span>
        </span>
      </div>

      <ol className="lines">
        {timed.rows.map(({ line, start }) => {
          const lit = litLineIds.has(line.id);
          const cls = [
            'line',
            lit ? 'is-lit' : '',
            reasonFocused && !lit ? 'is-dim' : '',
            hoveredLineId === line.id ? 'is-hover' : '',
          ]
            .filter(Boolean)
            .join(' ');

          return (
            <li
              key={line.id}
              className={cls}
              data-kind={line.kind}
              tabIndex={0}
              onMouseEnter={() => onLineHover(line.id)}
              onMouseLeave={() => onLineHover(null)}
              onFocus={() => onLineHover(line.id)}
              onBlur={() => onLineHover(null)}
            >
              <div className="ln-gutter">
                <span className="ln-id">{line.id}</span>
                <span className="ln-time">{mmss(start)}</span>
              </div>
              <div className="ln-body">
                <span className="kind">{KIND_LABEL[line.kind] ?? line.kind}</span>
                <p className="ln-text">{line.text}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </article>
  );
}
```

---

### `apps/web/src/components/ReasonList.tsx`

```tsx
// apps/web/src/components/ReasonList.tsx
import type { Line, Reason } from 'api-types';

interface Props {
  reasons: Reason[];
  lines: Line[];
  /** Reason indexes to highlight (hovered/pinned reason, or reasons citing a hovered line). */
  litIndexes: ReadonlySet<number>;
  pinnedIndex: number | null;
  onHover: (index: number | null) => void;
  onPin: (index: number) => void;
}

export function ReasonList({
  reasons,
  lines,
  litIndexes,
  pinnedIndex,
  onHover,
  onPin,
}: Props) {
  const kindById = new Map(lines.map((l) => [l.id, l.kind]));

  return (
    <aside className="panel reasons">
      <h3>Why this script should work</h3>
      <p className="hint">
        Hover or select a reason to light up the lines it points to. This is the
        model&rsquo;s reasoning for how the script is built, not measured performance.
      </p>

      <ul className="reason-list">
        {reasons.map((reason, i) => (
          <li key={`${reason.title}-${i}`}>
            <button
              type="button"
              className={`reason${litIndexes.has(i) ? ' is-lit' : ''}`}
              aria-pressed={pinnedIndex === i}
              onMouseEnter={() => onHover(i)}
              onMouseLeave={() => onHover(null)}
              onFocus={() => onHover(i)}
              onBlur={() => onHover(null)}
              onClick={() => onPin(i)}
            >
              <span className="reason-title">{reason.title}</span>
              <span className="reason-why">{reason.why}</span>
              <span className="reason-lines">
                {reason.line_ids.map((id) => (
                  <span key={id} className="line-ref" data-kind={kindById.get(id)}>
                    Line {id}
                  </span>
                ))}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
```
