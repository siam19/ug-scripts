# Script Assistant: Sprint 2 Frontend Design Guide

Design guide for the local agent updating `apps/web`. It describes **what to build and why**, not full source. It builds on `frontend-react-files-v2.md` (the current code) and the three mockups (`image.png`, `image-1.png`, `script-line-select.png`). API changes are out of scope here; section 8 lists only the contract the UI assumes.

---

## 0. The five rules behind every decision

These resolve most of the clashes you flagged. When a case isn't covered below, apply them.

1. **The highlight is the scope.** Whatever is lit is exactly what the next action changes. The chevrons, undo/redo and regenerate all act on that same scope. Nothing selected means the whole script.
2. **Nothing is destroyed.** Every regeneration adds a version. Delete is a version too. Replaced segments get an undo toast. Saved scripts are independent snapshots.
3. **Stale is derived, never stored.** Each generated thing remembers a content hash of what it was built from. If the hash no longer matches, it is stale. Reverting an edit un-stales automatically; there are no dirty flags to drift.
4. **Stale is a hatch, not a wall.** A stale area gets a hatched rail and a passive badge. No dimming, no overlay, no disabled controls.
5. **Identity is stable, numbers are derived.** Lines, groups, tabs and facts get uids. "Line 3" is computed from position at render time, so reasons never break when lines are added or removed.

---

## 1. Visual language additions

Add to `:root` in `index.css`:

```css
--hatch: repeating-linear-gradient(135deg, rgba(20,24,26,.14) 0 1.5px, transparent 1.5px 6px);
--pop-shadow: 0 8px 24px rgba(20,24,26,.16), 0 0 0 1px var(--line);
```

- **Hatching** is the only "stale/outdated" cue. It is neutral on purpose: the palette's colors already mean hook, concept, CTA, generating (red) and error.
- **Floating elements** (line toolbar, menus, toasts, version buttons) are white with `--pop-shadow`. Nothing else in the UI floats, so floating reads as "this acts on something".
- **Motion** is only a response to a user action: a 600 ms background flash on a line or group that was just replaced, and the spinner on a refresh icon. No new entrance animations.
- **Icons** (`@tabler/icons-react`, size 16, stroke 1.75): refresh `IconRefresh`, edit `IconPencil`, remove `IconX`, confirm `IconCheck`, save `IconBookmark` / `IconBookmarkFilled` (fall back to `fill="currentColor"` if the filled export is missing), versions `IconChevronLeft` / `IconChevronRight`, line menu `IconDots`, `IconArrowBackUp`, `IconArrowForwardUp`, `IconTrash`, rephrase `IconWand`, add `IconPlus`.
- **Reduced motion:** the global rule freezes spinners. Every pending state therefore also changes its **label** ("Rewriting…") so the cue never depends on animation.

---

## 2. State architecture

Today `ResultsView` renders server data directly. Sprint 2 needs local state that diverges from it, so introduce a **workspace** seeded from the stream.

### 2.1 Files

```
src/state/types.ts           types below
src/state/hash.ts            hash(), factsHash(), segmentHash()
src/state/script-tree.ts     pure selectors: visibleLines, visibleCover, scopeOf, ...
src/state/workspace.ts       reducer + actions
src/state/WorkspaceContext.tsx
src/state/saved-scripts.ts   localStorage-backed hook
```

Keep `script-tree.ts` and the reducer **pure and unit-tested** (add `vitest`). Most bugs in this sprint will be in version/selection logic, not in JSX.

`ResultsView` keeps `key={runId}`. Inside it, `useReducer(workspaceReducer, ...)`. An effect seeds facts and segments once, then dispatches `SCRIPT_READY(index, script)` as each streamed script arrives. The stream hook itself stays unchanged.

### 2.2 Types

```ts
export type Uid = string; // crypto.randomUUID()

// --- script tree: lines and groups both carry versions ---
export interface LineVersion {
  id: Uid;
  label: 'Original' | 'Edited' | 'Rephrased' | 'Regenerated' | 'Deleted';
  detail?: string;          // e.g. the tone used for a rephrase
  text: string | null;      // null = deleted (tombstone)
}
export interface LineNode {
  type: 'line'; uid: Uid; kind: LineKind;
  versions: LineVersion[]; cursor: number;
  pending?: 'rephrase' | 'regenerate';
}
export interface GroupVersion { id: Uid; label: 'Original' | 'Rewritten'; children: ScriptNode[] }
export interface GroupNode {
  type: 'group'; uid: Uid;
  versions: GroupVersion[]; cursor: number; pending?: boolean;
}
export type ScriptNode = LineNode | GroupNode;

export interface ReasonItem { uid: Uid; title: string; why: string; cites: Uid[] } // LineNode uids at creation
export interface Basis { facts: string; segment: string }                         // content hashes
export interface ScriptRevision { id: Uid; label: 'Original' | 'Rewritten'; basis: Basis; nodes: ScriptNode[]; reasons: ReasonItem[] }
export interface ScriptDoc { revisions: ScriptRevision[]; cursor: number; pending?: boolean }

// --- the rest of the workspace ---
export interface FactItem { id: Uid; text: string; original: string | null } // original null = user-added
export interface SegmentSlot {
  id: Uid; segment: Segment; edited: boolean;
  factsBasis: string; previous?: Segment; pending?: boolean;
  script: ScriptDoc | null; scriptStatus: 'streaming' | 'ready' | 'error';
}
export type Selection =
  | { kind: 'none' }
  | { kind: 'reason'; reasonUid: Uid }
  | { kind: 'line'; uid: Uid };
export interface Workspace {
  meta: { name: string; market: string; language: 'en' | 'bn' };
  facts: FactItem[]; slots: SegmentSlot[]; activeSlotId: Uid; selection: Selection;
}
```

Server line ids (1..n) are converted to uids once, at ingestion. A server reason's `line_ids` become `cites`.

### 2.3 Staleness (derived)

```ts
export const hash = (s: string) => { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); };
export const factsHash   = (f: FactItem[]) => hash(f.map(x => x.text.trim()).sort().join('\n'));
export const segmentHash = (s: Segment) => hash(JSON.stringify([s.name.trim(), s.who.trim(), s.pain_point, [...s.platforms].sort()]));

export function scriptStaleReasons(ws: Workspace, slot: SegmentSlot): ('facts' | 'segment')[] {
  const rev = slot.script?.revisions[slot.script.cursor];
  if (!rev) return [];
  const out: ('facts' | 'segment')[] = [];
  if (rev.basis.facts   !== factsHash(ws.facts))     out.push('facts');
  if (rev.basis.segment !== segmentHash(slot.segment)) out.push('segment');
  return out;
}
// A slot needs regenerating if its script is stale, or its (unedited) segment predates the facts.
export const slotNeedsRegen = (ws: Workspace, s: SegmentSlot) =>
  scriptStaleReasons(ws, s).length > 0 || (!s.edited && s.factsBasis !== factsHash(ws.facts));
```

Consequences that come for free: editing a fact back to its original text un-stales everything. Regenerating one tab after a facts edit makes only that slot fresh. The section badge count (section 3.1) falls as the user refreshes slots one by one. A request that returns after the user edited facts again is immediately stale, because its basis was captured when the request started.

**Keep as is** (acknowledge) on a stale script sets `rev.basis` and `slot.factsBasis` to the current hashes.

### 2.4 Versions: one structure for lines, groups and whole scripts

Every node has `versions[]` and a `cursor`. Chevrons and Undo/Redo both move the cursor, so there is one concept:

- **Chevrons** move the cursor of the *selected scope* by ±1. Disabled at the ends (no wrap).
- **Undo / Redo** (line menu, `⌘Z` / `⇧⌘Z`) are the same cursor move, available as labelled actions and keyboard shortcuts. They are what restores a *deleted* line, since a tombstone has no chevrons to click.
- **Any new operation appends** a version and moves the cursor to it, even if the cursor was on an older version. Older versions stay reachable with ‹. Undo and redo mean "previous / next version in creation order".

**Scope** (what chevrons act on):

| Selection | Chevrons act on |
|---|---|
| none | the whole script (`ScriptDoc.cursor`), shown only if it has more than one revision |
| reason | that reason's group node, shown only once it has been regenerated (more than one version) |
| line | that line node, shown only if it has more than one version |

A **script revision** carries its own `reasons`. Switching revisions swaps reasons too. Group and line versions never change the reason list.

### 2.5 Reason regeneration: groups, nesting and overlap

This is the answer to "what if reason regenerations add or remove lines".

**The invariant (API contract):** a reason cites a **contiguous** range of lines. Add this to the prompt and to the existing validate-and-retry step. If a response violates it anyway, the frontend uses the covering span.

**Resolving a reason to what it highlights and replaces** (`visibleCover`):

1. Each cited uid that is not currently visible (it sits in an inactive version) is lifted to its visible ancestor.
2. All are lifted to the same sibling list (their lowest common ancestor's children).
3. Take the contiguous run from the first to the last of those siblings. That run is the **cover**.

**Regenerating a reason:**

- If the cover is exactly one existing group node, append a version to it.
- Otherwise **wrap** the cover's nodes in a new `GroupNode` whose version 0 is the original children, then append version 1 with the new lines (fresh uids, kinds as returned).

**Why this holds up:**

- *Overlap.* Reason A cites 1-2, reason B cites 2-3. After A is regenerated, line 2 lives in group G. B's cover resolves to `[G, line 3]`. Regenerating B wraps G and line 3 in a new group H, with G nested untouched inside version 0. Switching H to its old version brings G back, including any per-line edits made inside it. Nothing is lost, nothing needs merging.
- *Add or remove lines.* Display numbers come from position, so "Line 3" simply renumbers. Reasons cite uids, so they never dangle. The timeline and word count recompute.
- *Single-line edits inside a group* live inside that group version. Switching the group version swaps them out and back intact.
- *Reasons whose lines are replaced.* B's cites now resolve to the group, so B highlights the whole group. If a reason's cover contains lines it did not originally cite, that is visible in the highlight, which satisfies rule 1.
- *A reason whose cited lines were all deleted* shows "All cited lines were removed" in place of its line chips, with refresh disabled.
- *The reason text is not regenerated.* Refresh means "rewrite these lines using this technique again". The title and explanation stay.

**Selection exclusivity:** clicking a line deselects any pinned reason, and pinning a reason deselects any line. Hover stays transient and unchanged: hovering a reason previews its lines, hovering a line previews the reasons that cite it. A selected line counts as a persistent hover for the reasons panel, as in the mockup where reason 2 is outlined because line 2 is selected.

---

## 3. Feature 1: Editable fact chips and the stale section

### 3.1 Behavior

**Chip states**

| State | Look |
|---|---|
| Resting | text + faint pencil and cross at the right (opacity .4) |
| Hover / focus-within | icons at opacity .9; the icon under the pointer gets a `--tint` circle |
| Edited / added | a 6 px ink dot before the text, `title="Edited by you"` |
| Editing | the text becomes a seamless auto-growing textarea; icons become ✓ (commit) and ✕ (cancel) |

- Edit starts from the pencil, a double-click, or Enter while the chip is focused. Enter or blur commits. Esc cancels. Cmd/Ctrl+Enter also commits.
- Committing an empty chip removes it.
- Removing a chip shows a toast "Fact removed" with Undo.
- If edited text equals `original`, the chip returns to the resting state (and the section un-stales, rule 3).
- Optional addition, easy to drop: a dashed **+ Add a fact** chip at the end of the list. Users will know facts the photo missed.
- Cap fact length at 200 characters. No minimum number of facts is enforced in the UI.

**Touch:** icons are always visible at opacity .6.

### 3.2 Stale visualization: cause bar plus effect rail

Two cues, one near the cause and one at the consequence. Nothing blocks interaction.

```
Facts the scripts rely on
[● Net weight is 150g …  ✎ ✕] [Front shows a red chili …  ✎ ✕] [+ Add a fact]
┌─ hatched ────────────────────────────────────────────────────────────────┐
│ 2 facts changed. Segments and scripts still use the original facts.      │
│                                         [Reset facts]  [Regenerate]      │
└──────────────────────────────────────────────────────────────────────────┘

▌ Customer segments        ◌ 3 of 3 based on earlier facts   [Regenerate]
▌ [ 1. Gaming Crew ◌ ] [ 2. Night Owls ◌ ] [ 3. Dorm Snackers ◌ ]
▌ …everything below stays fully interactive…
```

1. **Cause bar** (`.facts-footer`) appears under the chips when `factsHash` differs from the generation basis. It slides open with the `grid-template-rows: 0fr → 1fr` trick so nothing jumps. Primary action **Regenerate** (re-runs segments and scripts with the current facts). Secondary **Reset facts** restores the model's originals, which un-stales everything. Text button, no dialog.
2. **Effect rail**: `.segment-section[data-stale]` gets a 4 px hatched vertical rail at its left edge (`left: -14px`, `-10px` on mobile). The section header shows a passive badge "N of 3 based on earlier facts" and a text button **Regenerate**. N is `slots.filter(slotNeedsRegen).length`.
3. **Tab marker**: a stale tab shows a hollow 8 px ring (`border: 1.5px solid currentColor`, opacity .6) in the same corner as the generating dot. Tooltip: "Based on earlier facts". Generating keeps the pulsing red dot. Different shape, different meaning.
4. **Script marker**: the script card gets the same hatched rail on its left edge, plus the in-workbench stale bar (section 5.1).

**Regenerate rules**

- Regenerates only slots where `slotNeedsRegen` is true. Slots the user acknowledged with "Keep as is" are skipped.
- **Hand-edited segments are kept.** Only their script is rewritten. (Flip in section 9 if you disagree.)
- The previous segments and scripts are snapshotted for one level of undo: toast "Segments regenerated" with Undo, 15 s. Saved scripts are unaffected.
- While running, slots reuse the existing streaming states (pulsing tab dot, script skeleton). The section keeps its place and the user can still switch tabs.

### 3.3 Components

- New `FactChips.tsx` (list + `FactChip` + add chip + cause bar). Replaces the inline `<ul className="chip-list">` in `ResultsView`.
- New `StaleBar.tsx`, a small presentational bar reused for the facts cause bar and the script stale bar.
- Keep `.chip-animated` for entry. Give chips `display: inline-flex; align-items: flex-start; max-width: 100%` so multi-line Bangla facts keep the icons top-right.

---

## 4. Feature 2: Regenerate a single segment from its tab

### 4.1 Structure

`.tab` is a `<button role="tab">`, and a button cannot contain a button. Wrap each tab:

```tsx
<div className="tab-wrap" role="presentation">
  <button role="tab" className="tab" /* existing props */>…</button>
  <button type="button" className="tab-refresh"
          aria-label={`Replace “${s.name}” with a new segment`}
          tabIndex={active ? 0 : -1} onClick={() => regenerateSegment(slot.id)}>
    <IconRefresh size={16} aria-hidden="true" />
  </button>
</div>
```

`.tabs` grid children become `.tab-wrap`. Use `slot.id` as the React key (not the index), since slots are replaced in place.

### 4.2 Visual spec

```
┌──────────────────────────────┐
│ 1. Midnight Gaming Crew    ● │  status dot / stale ring: top-right
│                           ⟳  │  refresh: bottom-right, 24 px, 8 px inset
└──────────────────────────────┘
```

```css
.tab-wrap { position: relative; }
.tab { width: 100%; height: 100%; padding-right: 40px; }   /* reserve the corner */
.tab-refresh { position: absolute; right: 8px; bottom: 8px; width: 24px; height: 24px;
  display: grid; place-items: center; border: 0; border-radius: 50%;
  background: transparent; color: var(--ink-2); opacity: 0; transition: opacity .12s, background-color .12s; }
.tab-wrap:hover .tab-refresh, .tab-wrap:focus-within .tab-refresh { opacity: 1; }
.tab-refresh:hover { background: var(--tint); }
.tab.is-active ~ .tab-refresh { color: #fff; }
.tab.is-active ~ .tab-refresh:hover { background: rgba(255,255,255,.18); }
.tab-wrap.is-pending .tab-refresh { opacity: 1; animation: spin .9s linear infinite; pointer-events: none; }
@keyframes spin { to { rotate: 360deg; } }
@media (hover: none) { .tab.is-active ~ .tab-refresh { opacity: 1; } }  /* touch: active tab only */
```

### 4.3 Behavior

- Works on any tab, active or not. It does not switch the active tab.
- While pending: the icon spins, the tab label dims to .6, and if the slot is active its `SegmentCard` shows a skeleton and `aria-busy="true"`.
- On success the tab and card are replaced in place (`tab-animated` pop-in). The slot's `previous` keeps the old segment for a toast Undo ("Segment replaced", 15 s). `edited` resets to false and `factsBasis` is set to the current facts.
- **The slot's script becomes stale** (its segment hash changed). The script stays visible and fully usable, with the stale bar in section 5.1. Per your spec it is not auto-regenerated. See the open question in section 9.
- Saved scripts are untouched.
- The new segment must differ from the others, so the request carries the other segments' names (section 8).

---

## 5. Feature 3: Segment card actions, edit mode, saved scripts

### 5.1 Stale bar inside the workbench

Rendered at the top of `.tab-panel`'s workbench whenever `scriptStaleReasons` is non-empty. It is a slim hatched row, not a banner, and the workbench below stays interactive.

```
┌─ hatched ───────────────────────────────────────────────────────────────┐
│ Written before you changed the segment.      [Keep as is] [Rewrite script] │
└─────────────────────────────────────────────────────────────────────────┘
```

Copy by reason: "…changed the segment", "…changed the facts", "…changed the facts and the segment". For a replaced segment (`previous` is set): "This script was written for the previous segment."

- **Rewrite script** pushes a new `ScriptRevision` (label "Rewritten"). The old script, with all its line edits, stays one chevron away: with nothing selected, the chevrons switch whole-script versions and the header shows "Version 2 of 2".
- **Keep as is** acknowledges (section 2.3).

### 5.2 Save and Edit buttons

```
┌───────────────────────────────────────────┬──────────────────────┐
│ Midnight Gaming Crew            edited    │ In their words       │
│ University students in Dhaka dorms …      │ “Everyone around me  │
│ [TikTok] [Reels]                          │  …”                  │
│                       [🔖 Save] [✎ Edit]  │                      │
└───────────────────────────────────────────┴──────────────────────┘
```

```css
.segment-main { grid-template-rows: auto auto auto 1fr; }
.segment-actions { align-self: end; justify-self: end; display: flex; gap: 8px; }
.btn-sm { height: 32px; padding: 0 12px; font-size: .875rem; }
```

- Buttons are icon plus a visible label ("Save", "Edit"); the label hides below 420 px.
- **Save is derived, not toggled by a stored flag.** `isSaved = savedScripts.some(s => s.hash === currentHash)`, where `currentHash` covers the segment fields plus the visible lines' kind and text. Saved shows a filled bookmark and "Saved". Any edit changes the hash, so the button reverts to "Save" and saving again creates a second snapshot. Clicking "Saved" removes that snapshot with an Undo toast.
- Save is disabled while the script is streaming, regenerating, or the card is in edit mode.
- A faint "edited" hint (`.hint`) sits after the title when `slot.edited`.

### 5.3 Edit mode (in place)

- **Edit** swaps the card to edit mode with no layout jump: the `h3` becomes an input with the same font and size and an underline-only border; `.segment-who` becomes an auto-growing textarea (`field-sizing: content`, with a JS fallback); tags become removable tag inputs with a ghost "+ Add platform" input (Enter adds, Backspace on empty removes the last).
- The action row becomes **Cancel** and **Done** (primary). Esc cancels, Cmd/Ctrl+Enter commits. Name is required; empty platforms are allowed.
- The pain point stays read-only: it is the customer's own words. Making it editable later is a one-line change.
- **Done** with changes sets `slot.edited = true`. The segment hash changes, which makes the script stale (section 5.1). The tab label updates live. No change means no staleness.

### 5.4 Saved scripts

**Entry point:** a **Saved scripts** button at the right end of the masthead (`margin-left: auto`) with a count pill. Saving bumps the pill (one 200 ms scale) and shows a toast "Saved" with a **View** action.

**Surface:** a right-hand **drawer** (420 px, full-width bottom sheet below 700 px), non-modal, Esc closes, focus moves in and returns to the button on close.

```
Saved scripts                                  ✕
──────────────────────────────────────────────
▸ Midnight Gaming Crew · Ruchi Jhal Chanachur
  “Why is your midnight gaming crew still …”   Nov 9
▾ Night Owls · Ruchi Jhal Chanachur
  [Hook] Why is your …   [Concept] When …   [CTA] Grab …
  Reasons: Curiosity Question Hook, Segment Specificity, …
  [Copy script]  [Remove]
```

- Newest first. Each row is an accordion: collapsed shows segment, product name, hook preview (2 lines) and date. Expanded shows the lines with kind badges, the reason titles, **Copy script** and **Remove** (with Undo toast).
- Empty state: "Save a script from any segment card. Saved scripts stay here even if you change or replace the segment."
- Persistence: `localStorage` key `script-assistant:saved:v1`, wrapped in try/catch, capped at 50.

```ts
interface SavedScript {
  id: Uid; savedAt: number; hash: string;
  product: string; market: string; language: 'en' | 'bn';
  segment: Segment;
  lines: { kind: LineKind; text: string }[];            // resolved visible lines, deleted excluded
  reasons: { title: string; why: string; lines: number[] }[]; // display numbers at save time
}
```

---

## 6. Feature 4: Fine-grained workbench tuning

### 6.1 Reason refresh

`.reason` is a `<button>`, so use the same wrapper pattern as the tabs:

```tsx
<li className="reason-item">
  <button className="reason" … />   {/* existing */}
  <button className="reason-refresh" aria-label={`Rewrite the lines for “${reason.title}”`}>
    <IconRefresh size={16} />
  </button>
</li>
```

- Bottom-right of the card, on the same row as the `Line N` chips. Visible at opacity .5, 1 on hover or focus (not hover-only, because it must work on touch).
- Add `padding-bottom` on `.reason` so the icon never overlaps chips.
- Click does two things: **pins this reason** (so the highlighted span is visibly what will be replaced, rule 1) and starts regeneration.
- While pending: the icon spins and the span uses the pending style below. The button is disabled for that reason only. Other reasons and lines stay usable, and parallel regenerations on different spans are allowed.
- Tooltip: "Rewrite these lines using this technique".

### 6.2 Version chevrons

Matches `image-1.png`: a pair of chevrons at the card edges, halfway down the script card.

```css
.script-card { position: relative; }                       /* no overflow:hidden on .panel */
.version-rail { position: absolute; inset: 0; pointer-events: none; }
.rail-btn { position: absolute; top: 50%; translate: 0 -50%; pointer-events: auto;
  width: 32px; height: 32px; display: grid; place-items: center; border-radius: 50%;
  background: #fff; border: 1px solid var(--line-strong); box-shadow: var(--pop-shadow); }
.rail-prev { left: -16px; }  .rail-next { right: -16px; }
.rail-btn:disabled { opacity: .35; }
@media (max-width: 699px) { .version-rail { display: none; } }   /* stepper moves into the badge */
```

Half-outside placement fits: the gap to the reasons panel is 20 px and the shell padding is 24 px. For tall scripts, an optional refinement is `position: sticky; top: calc(50vh - 16px)` inside the rail so the buttons stay centered in the viewport.

Because the chevrons sit far from the selection, add a **scope badge** that ties them together: a small pill `2/3` at the top-right corner of the selected line, the group's first line, or (for the whole script) in the card header as "Version 2 of 3".

- Badge tooltip and the `aria-live="polite"` region read the version's label, for example "Version 2 of 3: Rephrased, punchier".
- Below 700 px the badge becomes an inline `‹ 2/3 ›` stepper.
- Chevrons are hidden when the scope has one version, and disabled while the scope is pending or being edited.
- After a switch, flash the affected lines (600 ms) so the change is noticed.

### 6.3 Selecting a line

- Click a line to select it. This clears any pinned reason (as you specified). Click it again, with no text selected, or press Esc, to deselect.
- Selected style: reuse `.is-lit` (kind background, kind-colored left rail) plus a 1 px kind-colored outline. Unlike a pinned reason, **other lines are not dimmed**, matching your mockup.
- A selected line acts as a persistent hover for the reasons panel.
- Markup: keep `li.line`; make an inner `div.line-hit` (`role="button"`, `tabIndex={0}`, `aria-pressed`) the click and keyboard target (Enter or Space selects), and render the toolbar as a sibling inside the `li`, not inside the button.

### 6.4 The line toolbar

```
                           ┌──────────────────────────────────────────┐
line 2 text …              │ ✎ Edit  ✦ Rephrase  ⟳ Regenerate │  ⋯   │
                           └──────────────────────────────────────────┘
```

Section 1 `(edit, rephrase, regenerate) | (dots)`, with labels.

- **Placement.** The bar straddles the bottom edge of the selected line, right-aligned (`bottom: -18px; right: 10px`). On selection the line gets `margin-bottom: 16px`, so the bar sits in reserved space and never covers the next line's text. This is a deliberate 16 px shift in exchange for no occlusion. Your mockup floats it over the top of the line; this variant keeps the bar inside the block's own footprint and avoids covering the previous line.
- **Style.** White, 1 px ink border, radius 12, `--pop-shadow`. Buttons are 30 px high with icon plus 13 px/600 label. A 1 px vertical divider separates the two sections. `role="toolbar"` with arrow-key navigation.
- **Below 560 px** the bar is a full-width in-flow row of equal buttons, labels kept.

**Dots menu** (`role="menu"`, opens below the bar and flips up near the viewport bottom):

| Item | Notes |
|---|---|
| Undo | shows the label it returns to ("Original"), `⌘Z`, disabled at version 0 |
| Redo | `⇧⌘Z`, disabled at the newest version |
| Delete line | danger color. Disabled with the tooltip "A script needs at least one line" if it is the only visible line |

**Operations** (each appends a `LineVersion`, moves the cursor to it, and flashes the line):

- **Edit:** the text becomes a seamless textarea in place (same font, size and line height, so there is no jump). A compact `✓ Save` and `✕ Cancel` replace the toolbar, with the hint "⌘↵ to save · Esc to cancel". Enter inserts nothing special, so Bangla IME composition is safe; only Cmd/Ctrl+Enter saves. The timeline segment and word count update live while typing. Saving unchanged text creates no version. Label: "Edited".
- **Rephrase:** same subject and object, new tone. One click, no dialog. The API picks a tone different from the versions already tried, and the version `detail` records it ("punchier"). Label: "Rephrased".
- **Regenerate:** replaces the sentence with a new one that fits the surrounding script. The request includes the whole current script for context and keeps the line's `kind`. Label: "Regenerated".
- **Delete:** appends a `text: null` version. The line collapses to a **tombstone row** ("Line deleted · Undo") that stays until it is restored. Tombstones are skipped in numbering, the timeline, the word count and Copy script.

**Pending state** (line, or every line in a regenerating group): text fades to .35, the kind badge text becomes "Rewriting…", and a 2 px indeterminate bar runs along the left rail. Layout does not shift: keep the old text until the new text arrives, then crossfade. On failure the old text stays and a small inline error with Retry shows for 6 s. No version is added.

### 6.5 Keyboard and a11y summary

- Lines, reasons, tabs and toolbars are all reachable and operable by keyboard. Esc steps back one level: close menu, then cancel edit, then deselect.
- `⌘Z` and `⇧⌘Z` act on the selected line only while focus is inside the script card and not in a textarea (native undo is untouched while typing).
- One visually hidden `aria-live="polite"` region announces version changes, regeneration start and completion, and "Line deleted".
- Hatched stale areas are always accompanied by text (never color alone).

---

## 7. Cross-cutting pieces

**Toasts.** Add one `ToastHost` (bottom-center, max 3, `role="status"`). Undo toasts last 10-15 s; plain ones 4 s. Used for: fact removed, segment replaced, section regenerated, saved/unsaved, delete (as well as the tombstone). Undo toasts store a reducer snapshot or inverse action, never DOM state.

**Pending state vocabulary** is one set of classes: `.is-pending` on the thing being rewritten, `aria-busy="true"` on its container, and a label change.

**Responsive summary**

| Under 700 px | |
|---|---|
| Tab refresh | visible on the active tab only |
| Chevrons | become the `‹ 2/3 ›` stepper in the badge |
| Line toolbar | full-width in-flow row |
| Saved drawer | bottom sheet |
| Segment actions | icon-only below 420 px |

---

## 8. API surface the UI assumes (for the follow-up sprint)

Images are never re-sent; facts go as text. Every request carries product meta (name, category, market, language) and the current facts.

| Action | Request additions | Response |
|---|---|---|
| Regenerate section | current facts, and which slots to redo (edited segments are sent as given) | same SSE events as `/generate-stream` |
| Regenerate one segment | the segment to replace and the other segments' names | `Segment` (must differ from the others) |
| Rewrite script | segment (current, possibly edited), facts | `Script` |
| Rewrite reason lines | segment, facts, full current script (flat: kind and text per visible line), target line positions, the reason (title and why) | `lines: {kind, text}[]`, count may differ |
| Rephrase / regenerate one line | same context, the single target, `mode`, and tones already tried | `{ kind, text, tone? }` |

Constraints to add to the prompts and validators: reasons cite a contiguous range; a regenerated line or group keeps its position and kind; regenerated text uses only the supplied facts.

---

## 9. Decisions I made that you may want to flip

1. **Regenerate-all keeps hand-edited segments** and rewrites only their scripts. Flipping it means replacing them too (the undo toast already covers the loss).
2. **A replaced segment does not auto-write its script**, per your spec; the stale bar offers it. A script for a different persona is arguably wrong, so auto-starting generation for a replaced segment is a one-line behavior change if you prefer it.
3. **Pain point is not editable** (your list names title, who, tags only).
4. **Reasons must cite contiguous lines** (API contract in section 8). This is what makes group versions clean.
5. **Undo/redo and chevrons are the same cursor**, in creation order, rather than two separate histories.
6. **Saved scripts persist in `localStorage`** only. Syncing them to the API is a later step.
7. **"+ Add a fact" chip** is an addition beyond your list.
8. **The line toolbar docks at the bottom edge** with a 16 px reserved gap instead of floating over the line above, as in the mockup.

---

## 10. Suggested build order

1. `state/` types, hashing, selectors and reducer, with unit tests. Refactor `ResultsView` onto the reducer with **no visible change**. Switch tab keys to slot ids.
2. Facts chips, cause bar, effect rail, tab stale ring (feature 1), plus `ToastHost`.
3. Tab refresh, segment edit mode, Save, stale bar, Saved drawer (features 2 and 3).
4. Reason refresh, group versions, chevron rail and scope badge (feature 4, reason side).
5. Line selection, toolbar, in-place edit, rephrase, regenerate, delete and tombstones (feature 4, line side).

Steps 1 and 2 need no API changes beyond stubbed responses; use a `useRegenerate` hook that returns mock data until the endpoints exist.

---

## 11. Notes on the current code

- `ProductForm` builds the preview URL with `useMemo` and revokes it in an effect cleanup. Under React `StrictMode` in dev, the simulated unmount revokes the URL while the memoized value is reused, so the preview image breaks. Create the URL inside the effect and store it in state.
- `ResultsView` keys tabs by `${s.name}-${i}`. Editing or replacing a segment would remount or mis-key tabs; use slot ids.
- `.tab` and `.reason` are buttons; the new corner icons must be siblings (sections 4.1 and 6.1), not children.
- `li.line` currently sets `tabIndex={0}` and drives hover highlighting from focus. Keep that for preview, but add the `role="button"` inner target from section 6.3 for selection, so focus does not imply selection.