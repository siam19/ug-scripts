# Sprint 2: Component Designs (TSX) and the Line Toolbar Decision

Companion to `frontend-design-guide-sprint-2.md`. That guide defines behavior and state; this file gives concrete TSX for the components that were only wireframes there, plus the library decision for the line toolbar and its menu.

The TSX was syntax-checked with the TypeScript compiler but **not type-checked or run**, since the sandbox has no network to install React, Base UI or Tabler. Expect to fix small type errors on first build. Imports from `../state/types` (`FactItem`) come from the guide's section 2.2.

---

## 1. Decision: use Base UI for the toolbar and menu; do not use shadcn/ui

### The deciding facts

- **shadcn/ui is built on Tailwind.** Its components are copied into your repo with Tailwind utility classes, which is a hard conflict with the sprint rule "do not install Tailwind". Using it would mean rewriting every class string into CSS, at which point you are only using the primitives underneath.
- **The primitives underneath are what you actually need.** For a toolbar with one dropdown menu, the hard parts are focus management, arrow-key navigation, Esc, collision-aware positioning (the menu flips near the viewport bottom), portaling, and ARIA. Those live in the headless layer, not in shadcn's styling.
- **Base UI is the best headless fit today.** It is unstyled, so it styles with plain CSS through `className` and `data-*` attributes. As of 2026 it is stable, and new shadcn projects default to it over Radix. It ships a `Toolbar` that composes directly with `Menu`: `<Toolbar.Button render={<Menu.Trigger />} />`, which is exactly our `… | ⋯` shape, so the dots button is part of the toolbar's roving tab stop with no glue code.
- **The package was renamed.** Use `@base-ui/react` (older docs show `@base-ui-components/react`).

### Options considered

| Option | Verdict |
|---|---|
| **shadcn/ui** | No. Tailwind-coupled; conflicts with project rules. |
| **Radix primitives directly** | Works with plain CSS and is still supported, but Base UI is the newer default and has the documented Toolbar + Menu composition. Choose this only if you already depend on Radix elsewhere. |
| **React Aria Components** | Also excellent and accessible. A heavier API surface than we need for one menu. |
| **Hand-rolled** | Toolbar roving focus is about 30 lines, but a correct menu (collision flip, focus return, typeahead, Esc, outside click) is the classic accessibility trap. Not worth owning. |

### What stays hand-rolled

Everything else in the sprint (chips, tabs, stale bar, version rail, scope badge, reason refresh, line editing) is plain React and CSS, because none of it needs popup or focus-trap logic. If the Saved drawer or toasts later become painful, Base UI also has Dialog and Toast; add them then, not now.

### Install

```bash
cd apps/web && bun add @base-ui/react
```

Base UI parts used: `Toolbar.Root`, `Toolbar.Button`, `Toolbar.Separator`, `Menu.Root`, `Menu.Trigger`, `Menu.Portal`, `Menu.Positioner`, `Menu.Popup`, `Menu.Item`, `Menu.Separator`. State is styled through attributes such as `[data-highlighted]` (menu item under focus), `[data-disabled]`, and `[data-popup-open]` (trigger while its menu is open); all are used in the CSS below.

### Things to know

- `Menu.Portal` renders the popup at the end of `<body>`. Our CSS variables are on `:root`, so styling carries over; the portaled popup needs its own `z-index` (`.menu-positioner`, 30).
- React events bubble through portals. The line `<li>` therefore must not have an `onClick`; only the inner `.line-hit` does. `ScriptLine` is built that way.
- Disabled `Toolbar.Button`s stay focusable by default, which is good for accessibility and is intended here (the busy state shows "Rephrasing…" instead of removing the button).
- If `align="end"` is rejected by the installed version's types, check the `Menu.Positioner` props in the Base UI docs; the alignment prop has been renamed once.

---

## 2. Components

Place each file in `apps/web/src/components/`. Not covered here: `SegmentCard` edit mode, the Saved drawer, `ToastHost` and the workspace reducer, which follow the guide.

### How the pieces connect

```
ScriptCard
 ├─ VersionRail                  (scope = selection, or whole script when nothing selected)
 └─ ol.lines
     ├─ ScriptLine × n           (LineView built by ScriptCard from the workspace tree)
     │   ├─ ScopeBadge           (only when selected and the line has >1 version)
     │   └─ LineToolbar          (Base UI Toolbar + Menu)
     └─ LineTombstone            (deleted lines)
ReasonList  └─ ReasonItem × 3
SegmentTabs └─ SegmentTab × 3
FactChips + Collapse/StaleBar    (facts section)
```

`ScriptLine`, `ReasonItem` and `SegmentTab` are deliberately **presentational**: they take view models and callbacks and never see the version tree. The derivation (display numbers, timecodes, version labels, `canUndo`, which lines are lit) lives in the selectors from guide section 2, so the tree logic stays unit-testable without React.


---

### `apps/web/src/components/LineToolbar.tsx`

**The decision in code.** Toolbar plus dots menu. Labels are visible next to icons, as requested. Menu hints show the shortcut by default and the version Undo returns to when `undoHint` is passed.

```tsx
// apps/web/src/components/LineToolbar.tsx
import { Menu } from '@base-ui/react/menu';
import { Toolbar } from '@base-ui/react/toolbar';
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconDots,
  IconPencil,
  IconRefresh,
  IconTrash,
  IconWand,
} from '@tabler/icons-react';

export type LinePending = 'rephrase' | 'regenerate';

export interface LineToolbarProps {
  pending?: LinePending;
  canUndo: boolean;
  canRedo: boolean;
  canDelete: boolean;
  /** Label of the version Undo returns to, e.g. "Original". */
  undoHint?: string;
  onEdit: () => void;
  onRephrase: () => void;
  onRegenerate: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onDelete: () => void;
}

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.userAgent);
export const MOD = isMac ? '⌘' : 'Ctrl+';
export const SHIFT = isMac ? '⇧' : 'Shift+';

/**
 * (Edit · Rephrase · Regenerate) | (⋯ menu)
 * Toolbar.Root gives roving arrow-key focus; Menu.Trigger is composed into
 * Toolbar.Button via `render`, so the dots button is part of the same tab stop.
 */
export function LineToolbar(p: LineToolbarProps) {
  const busy = p.pending !== undefined;

  return (
    <Toolbar.Root className="line-toolbar" aria-label="Line actions">
      <Toolbar.Button className="tb-btn" disabled={busy} onClick={p.onEdit}>
        <IconPencil size={16} aria-hidden="true" />
        <span>Edit</span>
      </Toolbar.Button>

      <Toolbar.Button className="tb-btn" disabled={busy} onClick={p.onRephrase}>
        <IconWand size={16} aria-hidden="true" />
        <span>{p.pending === 'rephrase' ? 'Rephrasing…' : 'Rephrase'}</span>
      </Toolbar.Button>

      <Toolbar.Button
        className={`tb-btn${p.pending === 'regenerate' ? ' is-spinning' : ''}`}
        disabled={busy}
        onClick={p.onRegenerate}
      >
        <IconRefresh size={16} aria-hidden="true" />
        <span>{p.pending === 'regenerate' ? 'Regenerating…' : 'Regenerate'}</span>
      </Toolbar.Button>

      <Toolbar.Separator className="tb-sep" />

      <Menu.Root>
        <Toolbar.Button
          render={<Menu.Trigger />}
          className="tb-btn tb-dots"
          aria-label="More line actions"
          disabled={busy}
        >
          <IconDots size={18} aria-hidden="true" />
        </Toolbar.Button>

        <Menu.Portal>
          <Menu.Positioner className="menu-positioner" side="bottom" align="end" sideOffset={6}>
            <Menu.Popup className="menu">
              <Menu.Item className="menu-item" disabled={!p.canUndo} onClick={p.onUndo}>
                <IconArrowBackUp size={16} aria-hidden="true" />
                <span>Undo</span>
                <span className="menu-hint">{p.undoHint ?? `${MOD}Z`}</span>
              </Menu.Item>
              <Menu.Item className="menu-item" disabled={!p.canRedo} onClick={p.onRedo}>
                <IconArrowForwardUp size={16} aria-hidden="true" />
                <span>Redo</span>
                <span className="menu-hint">{`${SHIFT}${MOD}Z`}</span>
              </Menu.Item>

              <Menu.Separator className="menu-sep" />

              <Menu.Item
                className="menu-item is-danger"
                disabled={!p.canDelete}
                onClick={p.onDelete}
              >
                <IconTrash size={16} aria-hidden="true" />
                <span>Delete line</span>
              </Menu.Item>
            </Menu.Popup>
          </Menu.Positioner>
        </Menu.Portal>
      </Menu.Root>
    </Toolbar.Root>
  );
}
```

---

### `apps/web/src/components/ScriptLine.tsx`

Selection, in-place editing (same typography, auto-growing textarea, Cmd/Ctrl+Enter saves, Esc cancels, IME-safe), pending state, flash on replace, and ⌘Z / ⇧⌘Z while focus is in the line. While editing, the hit area stops being a `role="button"` so no interactive element is nested. `onDraft` lets ScriptCard update the timeline live while typing.

```tsx
// apps/web/src/components/ScriptLine.tsx
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { LineKind } from 'api-types';
import { IconArrowBackUp, IconCheck, IconX } from '@tabler/icons-react';
import { LineToolbar, MOD } from './LineToolbar';
import type { LinePending } from './LineToolbar';
import { ScopeBadge } from './VersionRail';
import type { ScopeVersion } from './VersionRail';

const KIND_LABEL: Record<LineKind, string> = {
  hook: 'Hook',
  concept: 'Concept',
  cta: 'Call to action',
};

/** View model: ScriptCard derives this from the workspace tree. This component never sees nodes. */
export interface LineView {
  uid: string;
  kind: LineKind;
  text: string;
  no: number; // display number, derived from position
  time: string; // "0:12"
  version: ScopeVersion;
  canUndo: boolean;
  canRedo: boolean;
  undoHint?: string;
  pending?: LinePending;
}

interface Props {
  line: LineView;
  selected: boolean;
  lit: boolean; // lit by a hovered/pinned reason
  dim: boolean; // a reason is focused and this line is not part of it
  hovered: boolean;
  flash: boolean; // just replaced
  canDelete: boolean;
  onSelect: (uid: string) => void;
  onHover: (uid: string | null) => void;
  onDraft?: (uid: string, text: string | null) => void; // live timeline while typing
  onEdit: (uid: string, text: string) => void;
  onRephrase: (uid: string) => void;
  onRegenerate: (uid: string) => void;
  onUndo: (uid: string) => void;
  onRedo: (uid: string) => void;
  onDelete: (uid: string) => void;
  onStep: (uid: string, delta: -1 | 1) => void;
}

export function ScriptLine(p: Props) {
  const { line, selected } = p;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(line.text);
  const area = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!editing) return;
    const el = area.current;
    el?.focus();
    el?.setSelectionRange(el.value.length, el.value.length);
  }, [editing]);

  // Auto-grow so the textarea occupies exactly the space the paragraph did.
  useLayoutEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [draft, editing]);

  function startEdit() {
    setDraft(line.text);
    setEditing(true);
  }

  function finishEdit(save: boolean) {
    const next = draft.trim();
    if (save && next && next !== line.text) p.onEdit(line.uid, next);
    setEditing(false);
    p.onDraft?.(line.uid, null);
  }

  function handleDraft(value: string) {
    setDraft(value);
    p.onDraft?.(line.uid, value);
  }

  function handleAreaKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.nativeEvent.isComposing) return; // Bangla / IME composition
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation(); // don't also deselect the line
      finishEdit(false);
    } else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      finishEdit(true);
    }
  }

  function handleHitClick() {
    if (window.getSelection()?.toString()) return; // user is selecting text to copy
    p.onSelect(line.uid);
  }

  function handleHitKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      p.onSelect(line.uid);
    }
  }

  // ⌘Z / ⇧⌘Z while focus is inside this line (native undo is untouched while typing).
  function handleLineKey(e: KeyboardEvent<HTMLLIElement>) {
    if (!selected || editing) return;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') {
      e.preventDefault();
      if (e.shiftKey) {
        if (line.canRedo) p.onRedo(line.uid);
      } else if (line.canUndo) {
        p.onUndo(line.uid);
      }
    }
  }

  const cls = [
    'line',
    selected && 'is-selected',
    p.lit && 'is-lit',
    p.dim && 'is-dim',
    p.hovered && 'is-hover',
    p.flash && 'is-flash',
    line.pending && 'is-pending',
  ]
    .filter(Boolean)
    .join(' ');

  // While editing, the hit area must not be a button (it would contain a textarea).
  const hitProps = editing
    ? {}
    : {
        role: 'button' as const,
        tabIndex: 0,
        'aria-pressed': selected,
        onClick: handleHitClick,
        onKeyDown: handleHitKey,
      };

  return (
    <li
      className={cls}
      data-kind={line.kind}
      onMouseEnter={() => !editing && p.onHover(line.uid)}
      onMouseLeave={() => p.onHover(null)}
      onKeyDown={handleLineKey}
    >
      <div className="line-hit" {...hitProps}>
        <div className="ln-gutter">
          <span className="ln-id">{line.no}</span>
          <span className="ln-time">{line.time}</span>
        </div>
        <div className="ln-body">
          <span className="kind">{line.pending ? 'Rewriting…' : KIND_LABEL[line.kind] ?? line.kind}</span>
          {editing ? (
            <textarea
              ref={area}
              className="ln-edit"
              rows={1}
              value={draft}
              aria-label={`Edit line ${line.no}`}
              onChange={(e) => handleDraft(e.target.value)}
              onKeyDown={handleAreaKey}
            />
          ) : (
            <p className="ln-text">{line.text}</p>
          )}
        </div>
      </div>

      {line.pending && <span className="ln-progress" aria-hidden="true" />}

      {selected && !editing && (
        <>
          <ScopeBadge
            scope={line.version}
            disabled={Boolean(line.pending)}
            onStep={(d) => p.onStep(line.uid, d)}
          />
          <LineToolbar
            pending={line.pending}
            canUndo={line.canUndo}
            canRedo={line.canRedo}
            canDelete={p.canDelete}
            undoHint={line.undoHint}
            onEdit={startEdit}
            onRephrase={() => p.onRephrase(line.uid)}
            onRegenerate={() => p.onRegenerate(line.uid)}
            onUndo={() => p.onUndo(line.uid)}
            onRedo={() => p.onRedo(line.uid)}
            onDelete={() => p.onDelete(line.uid)}
          />
        </>
      )}

      {editing && (
        <div className="line-toolbar line-editbar" role="group" aria-label="Editing line">
          <span className="tb-hint">{MOD}↵ save · Esc cancel</span>
          <button type="button" className="tb-btn" onClick={() => finishEdit(false)}>
            <IconX size={16} aria-hidden="true" />
            <span>Cancel</span>
          </button>
          <button type="button" className="tb-btn is-primary" onClick={() => finishEdit(true)}>
            <IconCheck size={16} aria-hidden="true" />
            <span>Save</span>
          </button>
        </div>
      )}
    </li>
  );
}

/** Deleted line: keeps its place, restores with one click. Skipped in numbering, timeline and Copy. */
export function LineTombstone({ onUndo }: { onUndo: () => void }) {
  return (
    <li className="line-tombstone">
      <span>Line deleted</span>
      <button type="button" className="link-btn" onClick={onUndo}>
        <IconArrowBackUp size={14} aria-hidden="true" />
        Undo
      </button>
    </li>
  );
}
```

---

### `apps/web/src/components/VersionRail.tsx`

Side chevrons (desktop) and the `2/3` badge (with its own steppers below 700px). One live region announces the version in both layouts.

```tsx
// apps/web/src/components/VersionRail.tsx
import { IconChevronLeft, IconChevronRight } from '@tabler/icons-react';

/** Position within the versions of whatever is selected (line, group, or whole script). */
export interface ScopeVersion {
  index: number; // 0-based cursor
  count: number;
  label: string; // e.g. "Rephrased · punchier"
}

interface RailProps {
  scope: ScopeVersion | null;
  disabled?: boolean;
  onStep: (delta: -1 | 1) => void;
}

/**
 * Chevrons at the script card's side edges, halfway down (desktop).
 * Render as a direct child of `.script-card` (which is position: relative).
 * The live region lives outside `.version-rail` so it still announces when the
 * rail is hidden on small screens.
 */
export function VersionRail({ scope, disabled = false, onStep }: RailProps) {
  if (!scope || scope.count < 2) return null;
  const atStart = scope.index === 0;
  const atEnd = scope.index === scope.count - 1;

  return (
    <>
      <div className="version-rail" role="group" aria-label="Versions">
        <button
          type="button"
          className="rail-btn rail-prev"
          aria-label="Previous version"
          disabled={disabled || atStart}
          onClick={() => onStep(-1)}
        >
          <IconChevronLeft size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="rail-btn rail-next"
          aria-label="Next version"
          disabled={disabled || atEnd}
          onClick={() => onStep(1)}
        >
          <IconChevronRight size={18} aria-hidden="true" />
        </button>
      </div>
      <span className="sr-only" role="status" aria-live="polite">
        Version {scope.index + 1} of {scope.count}: {scope.label}
      </span>
    </>
  );
}

/**
 * "2/3" pill that ties the far-away chevrons to the selected block.
 * Place it inside a `position: relative` block (line, group's first line).
 * Below 700px it also shows its own ‹ › steppers (the rail is hidden there).
 */
export function ScopeBadge({ scope, disabled = false, onStep }: RailProps) {
  if (!scope || scope.count < 2) return null;
  return (
    <span className="scope-badge" title={scope.label}>
      <button
        type="button"
        className="stepper"
        aria-label="Previous version"
        disabled={disabled || scope.index === 0}
        onClick={() => onStep(-1)}
      >
        <IconChevronLeft size={12} aria-hidden="true" />
      </button>
      <span>
        {scope.index + 1}/{scope.count}
      </span>
      <button
        type="button"
        className="stepper"
        aria-label="Next version"
        disabled={disabled || scope.index === scope.count - 1}
        onClick={() => onStep(1)}
      >
        <IconChevronRight size={12} aria-hidden="true" />
      </button>
    </span>
  );
}
```

---

### `apps/web/src/components/FactChips.tsx`

Faint pencil and cross, inline editor, edited-dot, optional **Add a fact** chip. Pressing ✓ or ✕ uses `onMouseDown` preventDefault so the textarea does not blur first, and a `done` ref makes save and cancel idempotent. Removal should show the Undo toast in the parent.

```tsx
// apps/web/src/components/FactChips.tsx
import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent, MouseEvent } from 'react';
import { IconCheck, IconPencil, IconPlus, IconX } from '@tabler/icons-react';
import type { FactItem } from '../state/types';

const MAX_FACT = 200;

// Keep the textarea focused when the ✓ / ✕ buttons are pressed, so blur doesn't fire first.
const keepFocus = (e: MouseEvent) => e.preventDefault();

interface EditorProps {
  initial: string;
  onSave: (text: string) => void; // '' means the user emptied it
  onCancel: () => void;
}

function ChipEditor({ initial, onSave, onCancel }: EditorProps) {
  const [draft, setDraft] = useState(initial);
  const ref = useRef<HTMLTextAreaElement>(null);
  const done = useRef(false); // blur can fire after Enter/Esc/unmount; act once

  useEffect(() => {
    const el = ref.current;
    el?.focus();
    el?.setSelectionRange(el.value.length, el.value.length);
  }, []);

  const save = () => {
    if (done.current) return;
    done.current = true;
    onSave(draft.trim().slice(0, MAX_FACT));
  };
  const cancel = () => {
    if (done.current) return;
    done.current = true;
    onCancel();
  };

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.nativeEvent.isComposing) return; // Bangla / IME composition
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      save();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancel();
    }
  }

  return (
    <>
      <textarea
        ref={ref}
        className="chip-input"
        rows={1}
        maxLength={MAX_FACT}
        value={draft}
        aria-label="Edit fact"
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKey}
        onBlur={save}
      />
      <span className="chip-actions is-visible">
        <button type="button" aria-label="Save fact" onMouseDown={keepFocus} onClick={save}>
          <IconCheck size={14} aria-hidden="true" />
        </button>
        <button type="button" aria-label="Cancel editing" onMouseDown={keepFocus} onClick={cancel}>
          <IconX size={14} aria-hidden="true" />
        </button>
      </span>
    </>
  );
}

interface Props {
  facts: FactItem[];
  onEdit: (id: string, text: string) => void;
  onRemove: (id: string) => void; // parent shows the "Fact removed · Undo" toast
  onAdd: (text: string) => void;
}

export function FactChips({ facts, onEdit, onRemove, onAdd }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  return (
    <ul className="chip-list">
      {facts.map((fact) => {
        if (editingId === fact.id) {
          return (
            <li key={fact.id} className="chip chip-fact is-editing">
              <ChipEditor
                initial={fact.text}
                onCancel={() => setEditingId(null)}
                onSave={(text) => {
                  setEditingId(null);
                  if (!text) onRemove(fact.id);
                  else if (text !== fact.text) onEdit(fact.id, text);
                }}
              />
            </li>
          );
        }

        // An edit back to the original text is "not edited" again (and un-stales the section).
        const edited = fact.original === null || fact.text !== fact.original;
        return (
          <li key={fact.id} className={`chip chip-fact chip-animated${edited ? ' is-edited' : ''}`}>
            {edited && (
              <span className="chip-dot" role="img" aria-label="Edited by you" title="Edited by you" />
            )}
            <span className="chip-text" onDoubleClick={() => setEditingId(fact.id)}>
              {fact.text}
            </span>
            <span className="chip-actions">
              <button
                type="button"
                aria-label={`Edit fact: ${fact.text}`}
                onClick={() => setEditingId(fact.id)}
              >
                <IconPencil size={14} aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label={`Remove fact: ${fact.text}`}
                onClick={() => onRemove(fact.id)}
              >
                <IconX size={14} aria-hidden="true" />
              </button>
            </span>
          </li>
        );
      })}

      {adding ? (
        <li className="chip chip-fact is-editing">
          <ChipEditor
            initial=""
            onCancel={() => setAdding(false)}
            onSave={(text) => {
              setAdding(false);
              if (text) onAdd(text);
            }}
          />
        </li>
      ) : (
        <li>
          <button type="button" className="chip chip-add" onClick={() => setAdding(true)}>
            <IconPlus size={14} aria-hidden="true" />
            Add a fact
          </button>
        </li>
      )}
    </ul>
  );
}
```

---

### `apps/web/src/components/StaleBar.tsx`

`StaleBar` is the shared hatched strip (facts cause bar and workbench script bar). `Collapse` animates its height. `scriptStaleMessage` builds the copy from the stale reasons.

```tsx
// apps/web/src/components/StaleBar.tsx
import type { ReactNode } from 'react';

export type StaleReason = 'facts' | 'segment';

export interface StaleAction {
  label: string;
  onClick: () => void;
  primary?: boolean;
}

interface BarProps {
  children: ReactNode;
  actions: StaleAction[];
  busy?: boolean;
}

/** Hatched, passive strip. Never wraps or blocks the content it describes. */
export function StaleBar({ children, actions, busy = false }: BarProps) {
  return (
    <div className="stale-bar" role="status">
      <p>{children}</p>
      <div className="stale-actions">
        {actions.map((a) => (
          <button
            key={a.label}
            type="button"
            className={`btn btn-sm ${a.primary ? 'btn-primary' : 'btn-quiet'}`}
            disabled={busy}
            onClick={a.onClick}
          >
            {a.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Height-animating wrapper (grid-template-rows 0fr -> 1fr) so the facts cause bar
 * slides open without a layout jump. Closed content is inert (not focusable).
 */
export function Collapse({ open, children }: { open: boolean; children: ReactNode }) {
  // `inert` is a boolean in React 19 types; React 18 needs the string form via spread.
  const inertProps = open ? {} : { inert: '' };
  return (
    <div className={`collapse${open ? ' is-open' : ''}`} {...inertProps}>
      <div className="collapse-inner">{children}</div>
    </div>
  );
}

export function scriptStaleMessage(reasons: StaleReason[], replaced: boolean): string {
  if (replaced) return 'This script was written for the previous segment.';
  const what =
    reasons.length === 2 ? 'the facts and the segment' : reasons[0] === 'facts' ? 'the facts' : 'the segment';
  return `Written before you changed ${what}.`;
}
```

---

### `apps/web/src/components/SegmentTab.tsx`

Refresh control is a sibling of the tab button (a button cannot contain a button). Spinner, stale ring and generating dot share the corner without clashing: the dot or ring is top-right, the refresh icon bottom-right.

```tsx
// apps/web/src/components/SegmentTab.tsx
import type { KeyboardEvent } from 'react';
import { IconRefresh } from '@tabler/icons-react';

interface Props {
  index: number;
  name: string;
  active: boolean;
  outdated: boolean; // based on earlier facts
  generating: boolean; // script being written
  replacing: boolean; // this segment is being regenerated
  tabId: string;
  panelId: string;
  tabRef: (el: HTMLButtonElement | null) => void;
  onSelect: () => void;
  onKeyDown: (e: KeyboardEvent<HTMLButtonElement>) => void;
  onRefresh: () => void;
}

/**
 * A button can't contain a button, so the refresh control is a sibling of the tab.
 * The wrapper is role="presentation" so the tablist still only contains tabs.
 * Key the wrapper by `${slot.id}:${segmentRevision}` so a replacement replays the pop-in.
 */
export function SegmentTab(p: Props) {
  return (
    <div className={`tab-wrap tab-animated${p.replacing ? ' is-pending' : ''}`} role="presentation">
      <button
        ref={p.tabRef}
        type="button"
        role="tab"
        id={p.tabId}
        aria-selected={p.active}
        aria-controls={p.panelId}
        tabIndex={p.active ? 0 : -1}
        className={`tab${p.active ? ' is-active' : ''}`}
        onClick={p.onSelect}
        onKeyDown={p.onKeyDown}
      >
        <span>
          {p.index + 1}. {p.name}
        </span>
        {p.generating ? (
          <span className="tab-status-dot" role="img" aria-label="Generating script" title="Generating script…" />
        ) : p.outdated ? (
          <span className="tab-stale-ring" role="img" aria-label="Based on earlier facts" title="Based on earlier facts" />
        ) : null}
      </button>

      <button
        type="button"
        className="tab-refresh"
        aria-label={`Replace “${p.name}” with a new segment`}
        tabIndex={p.active ? 0 : -1}
        disabled={p.replacing}
        onClick={p.onRefresh}
      >
        <IconRefresh size={16} aria-hidden="true" />
      </button>
    </div>
  );
}
```

---

### `apps/web/src/components/ReasonItem.tsx`

Refresh control is a sibling of the reason card. Shows the orphaned state when every cited line was deleted. Clicking refresh should also pin the reason (done by the parent) so the span that will be replaced is visibly lit.

```tsx
// apps/web/src/components/ReasonItem.tsx
import type { LineKind } from 'api-types';
import { IconRefresh } from '@tabler/icons-react';

export interface ReasonRef {
  no: number; // display number of a visible cited line
  kind?: LineKind;
}

interface Props {
  title: string;
  why: string;
  refs: ReasonRef[]; // visible lines this reason's cover resolves to (deleted lines excluded)
  lit: boolean;
  pinned: boolean;
  pending: boolean;
  orphan: boolean; // every cited line was deleted
  onHover: (hovering: boolean) => void;
  onPin: () => void;
  onRefresh: () => void;
}

/** Replaces the inner <li> markup in ReasonList. The refresh control is a sibling of the card button. */
export function ReasonItem(p: Props) {
  return (
    <li className={`reason-item${p.pending ? ' is-pending' : ''}`}>
      <button
        type="button"
        className={`reason${p.lit ? ' is-lit' : ''}`}
        aria-pressed={p.pinned}
        onMouseEnter={() => p.onHover(true)}
        onMouseLeave={() => p.onHover(false)}
        onFocus={() => p.onHover(true)}
        onBlur={() => p.onHover(false)}
        onClick={p.onPin}
      >
        <span className="reason-title">{p.title}</span>
        <span className="reason-why">{p.why}</span>
        <span className="reason-lines">
          {p.orphan ? (
            <span className="hint">All cited lines were removed</span>
          ) : (
            p.refs.map((r) => (
              <span key={r.no} className="line-ref" data-kind={r.kind}>
                Line {r.no}
              </span>
            ))
          )}
        </span>
      </button>

      <button
        type="button"
        className="reason-refresh"
        aria-label={`Rewrite the lines for “${p.title}”`}
        title="Rewrite these lines using this technique"
        disabled={p.pending || p.orphan}
        onClick={p.onRefresh}
      >
        <IconRefresh size={16} aria-hidden="true" />
      </button>
    </li>
  );
}
```

---

## 3. CSS

Append to `apps/web/src/App.css`. The existing `.line` rules must be **replaced** by the ones here: the grid moved from `.line` to `.line-hit` so the toolbar can sit beside it. Requires `--hatch`, `--pop-shadow` and `@keyframes spin` from the design guide (sections 1 and 4.2).

```css
/* Append to apps/web/src/App.css.
   Replaces the existing `.line` rules (the grid now lives on `.line-hit`).
   Tab refresh, reason refresh sizing and the version rail are in the design guide (4.2, 6.2);
   only the pieces those sections don't cover are here. Needs --hatch and --pop-shadow from the guide (section 1)
   and the `spin` keyframes from 4.2. */

/* ---------- Fact chips ---------- */
.chip-fact { display: inline-flex; align-items: flex-start; gap: 6px; padding-right: 6px; }
.chip-dot { flex: none; width: 6px; height: 6px; margin-top: 8px; border-radius: 50%; background: var(--ink); }
.chip-actions { display: inline-flex; gap: 2px; margin-left: 2px; opacity: 0.4; transition: opacity 0.12s; }
.chip-fact:hover .chip-actions,
.chip-fact:focus-within .chip-actions,
.chip-actions.is-visible { opacity: 0.9; }
@media (hover: none) { .chip-actions { opacity: 0.6; } }
.chip-actions button { display: grid; place-items: center; width: 22px; height: 22px; padding: 0; border: 0; border-radius: 50%; background: transparent; }
.chip-actions button:hover { background: var(--tint); }
.chip-fact.is-editing { flex: 1 1 min(100%, 520px); align-items: center; border-color: var(--ink); }
.chip-input { flex: 1; min-width: 12ch; padding: 0; border: 0; outline: 0; resize: none; background: transparent; font: inherit; line-height: 1.5; field-sizing: content; }
.chip-add { display: inline-flex; align-items: center; gap: 6px; background: transparent; border-style: dashed; color: var(--ink-2); }
.chip-add:hover { border-color: var(--ink); color: var(--ink); }

/* ---------- Stale bar + collapse ---------- */
.collapse { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.2s ease; }
.collapse.is-open { grid-template-rows: 1fr; }
.collapse-inner { min-height: 0; overflow: hidden; }
.collapse-inner > .stale-bar { margin-top: 4px; }
.stale-bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 14px; background-color: var(--tint); background-image: var(--hatch); border: 1px solid var(--line); border-radius: 12px; }
.stale-bar p { max-width: 62ch; padding: 2px 8px; background: var(--tint); border-radius: 6px; color: var(--ink-2); font-size: 0.9375rem; }
.stale-actions { display: flex; gap: 8px; }
.btn-sm { height: 32px; padding: 0 12px; font-size: 0.875rem; }
.tab-stale-ring { flex: none; width: 8px; height: 8px; border: 1.5px solid currentColor; border-radius: 50%; opacity: 0.6; }

/* ---------- Script line (replaces old .line rules) ---------- */
.line { position: relative; padding: 14px 14px 14px 12px; border-left: 3px solid transparent; border-radius: 12px; transition: background-color 0.12s, opacity 0.12s, border-color 0.12s; }
.line-hit { display: grid; grid-template-columns: 52px minmax(0, 1fr); gap: 12px; border-radius: 8px; cursor: pointer; }
.line-hit:focus-visible { outline: 2px solid var(--concept); outline-offset: 4px; }
.line.is-hover { background: var(--tint); }
.line.is-lit,
.line.is-selected { background: var(--kind-bg); border-left-color: var(--kind); }
.line.is-selected { margin-bottom: 16px; box-shadow: 0 0 0 1px var(--kind); }   /* reserved space for the toolbar */
.line.is-dim { opacity: 0.45; }
.line.is-pending .ln-text { opacity: 0.35; }
.line.is-flash { animation: flash 0.6s ease-out; }
@keyframes flash { from { background: var(--kind-bg); box-shadow: 0 0 0 2px var(--kind); } }
.ln-edit { width: 100%; padding: 0; border: 0; outline: 0; resize: none; background: transparent; font: inherit; font-size: 1.1875rem; line-height: 1.55; }
.ln-progress { position: absolute; left: -3px; top: 8px; bottom: 8px; width: 3px; overflow: hidden; border-radius: 2px; }
.ln-progress::after { content: ''; position: absolute; inset: 0 0 auto 0; height: 40%; background: var(--kind); animation: slide 1s ease-in-out infinite; }
@keyframes slide { from { transform: translateY(-100%); } to { transform: translateY(250%); } }

.line-tombstone { display: flex; align-items: center; gap: 10px; margin-left: 15px; padding: 6px 12px; border: 1px dashed var(--line-strong); border-radius: 10px; color: var(--ink-3); font-size: 0.875rem; }
.link-btn { display: inline-flex; align-items: center; gap: 4px; padding: 0; border: 0; background: none; color: var(--ink); font-weight: 600; text-decoration: underline; }

/* ---------- Line toolbar + menu ---------- */
.line-toolbar { position: absolute; right: 10px; bottom: -18px; z-index: 3; display: flex; align-items: center; gap: 2px; height: 36px; padding: 0 4px; background: #fff; border: 1px solid var(--ink); border-radius: 12px; box-shadow: var(--pop-shadow); }
.tb-btn { display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 10px; border: 0; border-radius: 8px; background: transparent; color: var(--ink); font-size: 0.8125rem; font-weight: 600; white-space: nowrap; }
.tb-btn:hover:not([data-disabled]) { background: var(--tint); }
.tb-btn[data-disabled] { opacity: 0.45; cursor: not-allowed; }
.tb-btn[data-popup-open] { background: var(--tint); }
.tb-btn.is-spinning svg { animation: spin 0.9s linear infinite; }
.tb-btn.is-primary { background: var(--ink); color: #fff; }
.tb-dots { padding: 0 6px; }
.tb-sep { width: 1px; height: 20px; margin: 0 4px; background: var(--line-strong); }
.tb-hint { padding: 0 8px; color: var(--ink-3); font-size: 0.75rem; }

.menu-positioner { z-index: 30; }
.menu { min-width: 220px; padding: 6px; border-radius: 12px; outline: 0; background: #fff; box-shadow: var(--pop-shadow); }
.menu-item { display: flex; align-items: center; gap: 10px; height: 36px; padding: 0 10px; border-radius: 8px; font-size: 0.9375rem; cursor: default; user-select: none; }
.menu-item[data-highlighted] { background: var(--tint); }
.menu-item[data-disabled] { opacity: 0.4; }
.menu-item.is-danger { color: var(--err-ink); }
.menu-item.is-danger[data-highlighted] { background: var(--err-bg); }
.menu-hint { margin-left: auto; color: var(--ink-3); font-size: 0.8125rem; }
.menu-sep { height: 1px; margin: 6px 4px; background: var(--line); }

/* ---------- Scope badge ---------- */
.scope-badge { position: absolute; top: -10px; right: 12px; z-index: 2; display: inline-flex; align-items: center; gap: 2px; height: 20px; padding: 0 8px; background: #fff; border: 1px solid var(--line-strong); border-radius: 999px; font-size: 0.75rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.scope-badge .stepper { display: none; place-items: center; width: 20px; height: 20px; padding: 0; border: 0; background: transparent; }

/* ---------- Reason refresh ---------- */
.reason-item { position: relative; }
.reason-lines { align-items: center; min-height: 28px; padding-right: 36px; }
.reason-refresh { position: absolute; right: 10px; bottom: 10px; display: grid; place-items: center; width: 28px; height: 28px; padding: 0; border: 0; border-radius: 50%; background: transparent; color: var(--ink-2); opacity: 0.5; transition: opacity 0.12s, background-color 0.12s; }
.reason-item:hover .reason-refresh,
.reason-item:focus-within .reason-refresh,
.reason-item.is-pending .reason-refresh { opacity: 1; }
.reason-refresh:hover:not(:disabled) { background: var(--tint); }
.reason-refresh:disabled { cursor: default; }
.reason-item.is-pending .reason-refresh svg { animation: spin 0.9s linear infinite; }

/* ---------- Small screens ---------- */
@media (max-width: 699px) {
  .scope-badge .stepper { display: grid; }
  .line.is-selected { margin-bottom: 0; }
  .line-toolbar { position: static; width: 100%; height: auto; margin-top: 12px; padding: 4px; justify-content: space-between; box-shadow: none; }
}
```

---

## 4. Wiring notes for ScriptCard

- Build one `LineView[]` per render from the selectors: numbers skip tombstones, `time` comes from cumulative word counts (the existing `ScriptCard` logic), `version` is `{ index, count, label }` from the line node, and `canUndo` / `canRedo` are `cursor > 0` / `cursor < versions.length - 1`.
- `selected`, `lit`, `dim`, `hovered` follow guide section 6.3: a selected line is a persistent hover for the reasons panel; only a pinned or hovered **reason** dims other lines.
- `flash` is true for about 600 ms after a node is replaced; keep a `Set<Uid>` of recently changed uids with a timeout.
- `canDelete` is false when only one non-deleted line remains.
- Pass `VersionRail` the scope from guide section 2.4 (selected line, selected reason group, or whole script with nothing selected), and `disabled` while that scope is pending or a line is being edited.
- The ScriptCard header meta ("About 32 seconds spoken") should use live drafts from `onDraft` so the timeline tracks typing.
- Esc handling: the menu closes first, then edit mode cancels (ScriptLine stops propagation), then a card-level handler deselects.