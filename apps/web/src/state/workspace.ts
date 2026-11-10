import type { LineKind, Script, Segment } from 'api-types';
import { factsHash, hash, segmentHash } from './hash';
import {
  collectVisibleUids,
  findLineNode,
  resolveVisibleCover,
} from './script-tree';
import type {
  FactItem,
  GroupNode,
  GroupVersion,
  LineNode,
  LineVersion,
  ReasonItem,
  ScriptDoc,
  ScriptNode,
  ScriptRevision,
  SegmentSlot,
  Uid,
  Workspace,
  WorkspaceMeta,
} from './types';
import { generateUid } from './uid';

export type WorkspaceAction =
  | {
      type: 'SEED_WORKSPACE';
      facts: string[];
      segments: Segment[];
      meta: WorkspaceMeta;
    }
  | { type: 'SCRIPT_READY'; index: number; script: Script }
  | { type: 'SCRIPT_ERROR'; index: number }
  | { type: 'SET_ACTIVE_SLOT'; slotId: Uid }
  | { type: 'SELECT_LINE'; uid: Uid }
  | { type: 'SELECT_REASON'; reasonUid: Uid }
  | { type: 'SELECT_NONE' }
  // Facts
  | { type: 'EDIT_FACT'; id: Uid; text: string }
  | { type: 'REMOVE_FACT'; id: Uid }
  | { type: 'ADD_FACT'; text: string }
  | { type: 'RESET_FACTS' }
  // Segments
  | { type: 'REPLACE_SEGMENT_START'; slotId: Uid }
  | { type: 'REPLACE_SEGMENT_SUCCESS'; slotId: Uid; segment: Segment }
  | { type: 'REPLACE_SEGMENT_UNDO'; slotId: Uid }
  | { type: 'REPLACE_SEGMENT_FAIL'; slotId: Uid }
  | { type: 'EDIT_SEGMENT'; slotId: Uid; segment: Segment }
  // Whole Script
  | { type: 'REWRITE_SCRIPT_START'; slotId: Uid }
  | { type: 'REWRITE_SCRIPT_SUCCESS'; slotId: Uid; script: Script }
  | { type: 'REWRITE_SCRIPT_FAIL'; slotId: Uid }
  | { type: 'KEEP_SCRIPT_AS_IS'; slotId: Uid }
  // Line Actions
  | { type: 'EDIT_LINE'; lineUid: Uid; text: string }
  | { type: 'REPHRASE_LINE_START'; lineUid: Uid }
  | { type: 'REPHRASE_LINE_SUCCESS'; lineUid: Uid; text: string; tone?: string }
  | { type: 'REGENERATE_LINE_START'; lineUid: Uid }
  | { type: 'REGENERATE_LINE_SUCCESS'; lineUid: Uid; text: string }
  | { type: 'LINE_ACTION_FAIL'; lineUid: Uid }
  | { type: 'DELETE_LINE'; lineUid: Uid }
  | { type: 'UNDO_LINE'; lineUid: Uid }
  | { type: 'REDO_LINE'; lineUid: Uid }
  | { type: 'STEP_SCOPE'; delta: -1 | 1 }
  // Reason Actions
  | { type: 'REWRITE_REASON_START'; reasonUid: Uid }
  | {
      type: 'REWRITE_REASON_SUCCESS';
      reasonUid: Uid;
      newLines: { kind: LineKind; text: string }[];
    }
  | { type: 'REWRITE_REASON_FAIL'; reasonUid: Uid };

export const INITIAL_WORKSPACE: Workspace = {
  meta: { name: '', market: '', language: 'en' },
  facts: [],
  slots: [],
  activeSlotId: '',
  selection: { kind: 'none' },
};

/**
 * Transforms an incoming API Script into our version-tracked ScriptDoc.
 */
export function buildScriptDoc(
  script: Script,
  factsBasis: string,
  segmentBasis: string,
): ScriptDoc {
  // Convert API lines into LineNodes with stable UIDs
  const lineIdToUid = new Map<number, Uid>();

  const nodes: LineNode[] = script.lines.map((l) => {
    const uid = generateUid();
    lineIdToUid.set(l.id, uid);
    return {
      type: 'line',
      uid,
      kind: l.kind,
      cursor: 0,
      versions: [
        {
          id: generateUid(),
          label: 'Original',
          text: l.text,
        },
      ],
    };
  });

  const reasons: ReasonItem[] = script.reasons.map((r) => ({
    uid: generateUid(),
    title: r.title,
    why: r.why,
    cites: r.line_ids.map((id) => lineIdToUid.get(id) || '').filter(Boolean),
  }));

  const initialRev: ScriptRevision = {
    id: generateUid(),
    label: 'Original',
    basis: { facts: factsBasis, segment: segmentBasis },
    nodes,
    reasons,
  };

  return {
    revisions: [initialRev],
    cursor: 0,
  };
}

export function workspaceReducer(state: Workspace, action: WorkspaceAction): Workspace {
  switch (action.type) {
    case 'SEED_WORKSPACE': {
      const currentFactsHash = hash(action.facts.map((f) => f.trim()).sort().join('\n'));
      const factItems: FactItem[] = action.facts.map((text) => ({
        id: generateUid(),
        text,
        original: text,
      }));

      const slots: SegmentSlot[] = action.segments.map((seg) => ({
        id: generateUid(),
        segment: seg,
        edited: false,
        factsBasis: currentFactsHash,
        script: null,
        scriptStatus: 'streaming',
      }));

      return {
        meta: action.meta,
        facts: factItems,
        slots,
        activeSlotId: slots[0]?.id ?? '',
        selection: { kind: 'none' },
      };
    }

    case 'SCRIPT_READY': {
      const slot = state.slots[action.index];
      if (!slot) return state;

      const fHash = factsHash(state.facts);
      const sHash = segmentHash(slot.segment);
      const scriptDoc = buildScriptDoc(action.script, fHash, sHash);

      const nextSlots = [...state.slots];
      nextSlots[action.index] = {
        ...slot,
        script: scriptDoc,
        scriptStatus: 'ready',
      };

      return { ...state, slots: nextSlots };
    }

    case 'SCRIPT_ERROR': {
      const slot = state.slots[action.index];
      if (!slot) return state;
      const nextSlots = [...state.slots];
      nextSlots[action.index] = { ...slot, scriptStatus: 'error' };
      return { ...state, slots: nextSlots };
    }

    case 'SET_ACTIVE_SLOT': {
      if (state.activeSlotId === action.slotId) return state;
      return {
        ...state,
        activeSlotId: action.slotId,
        selection: { kind: 'none' },
      };
    }

    case 'SELECT_LINE': {
      return {
        ...state,
        selection: { kind: 'line', uid: action.uid },
      };
    }

    case 'SELECT_REASON': {
      return {
        ...state,
        selection: { kind: 'reason', reasonUid: action.reasonUid },
      };
    }

    case 'SELECT_NONE': {
      if (state.selection.kind === 'none') return state;
      return { ...state, selection: { kind: 'none' } };
    }

    // --- Facts Actions ---
    case 'EDIT_FACT': {
      const nextFacts = state.facts.map((f) =>
        f.id === action.id ? { ...f, text: action.text.trim() } : f,
      );
      return { ...state, facts: nextFacts };
    }

    case 'REMOVE_FACT': {
      return {
        ...state,
        facts: state.facts.filter((f) => f.id !== action.id),
      };
    }

    case 'ADD_FACT': {
      const trimmed = action.text.trim();
      if (!trimmed) return state;
      return {
        ...state,
        facts: [
          ...state.facts,
          { id: generateUid(), text: trimmed, original: null },
        ],
      };
    }

    case 'RESET_FACTS': {
      const restored = state.facts
        .filter((f) => f.original !== null)
        .map((f) => ({ ...f, text: f.original! }));
      return { ...state, facts: restored };
    }

    // --- Segment Actions ---
    case 'REPLACE_SEGMENT_START': {
      return {
        ...state,
        slots: state.slots.map((s) =>
          s.id === action.slotId ? { ...s, pending: true } : s,
        ),
      };
    }

    case 'REPLACE_SEGMENT_SUCCESS': {
      const curFactsHash = factsHash(state.facts);
      return {
        ...state,
        slots: state.slots.map((s) => {
          if (s.id !== action.slotId) return s;
          return {
            ...s,
            segment: action.segment,
            edited: false,
            factsBasis: curFactsHash,
            previous: s.segment,
            pending: false,
          };
        }),
      };
    }

    case 'REPLACE_SEGMENT_UNDO': {
      return {
        ...state,
        slots: state.slots.map((s) => {
          if (s.id !== action.slotId || !s.previous) return s;
          return {
            ...s,
            segment: s.previous,
            previous: undefined,
          };
        }),
      };
    }

    case 'REPLACE_SEGMENT_FAIL': {
      return {
        ...state,
        slots: state.slots.map((s) =>
          s.id === action.slotId ? { ...s, pending: false } : s,
        ),
      };
    }

    case 'EDIT_SEGMENT': {
      return {
        ...state,
        slots: state.slots.map((s) => {
          if (s.id !== action.slotId) return s;
          return {
            ...s,
            segment: action.segment,
            edited: true,
          };
        }),
      };
    }

    // --- Whole Script Actions ---
    case 'REWRITE_SCRIPT_START': {
      return {
        ...state,
        slots: state.slots.map((s) => {
          if (s.id !== action.slotId || !s.script) return s;
          return { ...s, script: { ...s.script, pending: true } };
        }),
      };
    }

    case 'REWRITE_SCRIPT_SUCCESS': {
      const slot = state.slots.find((s) => s.id === action.slotId);
      if (!slot || !slot.script) return state;

      const fHash = factsHash(state.facts);
      const sHash = segmentHash(slot.segment);
      const newDoc = buildScriptDoc(action.script, fHash, sHash);
      const newRev = newDoc.revisions[0];
      newRev.label = 'Rewritten';

      return {
        ...state,
        slots: state.slots.map((s) => {
          if (s.id !== action.slotId || !s.script) return s;
          const nextRevs = [...s.script.revisions, newRev];
          return {
            ...s,
            script: {
              revisions: nextRevs,
              cursor: nextRevs.length - 1,
              pending: false,
            },
          };
        }),
        selection: { kind: 'none' },
      };
    }

    case 'REWRITE_SCRIPT_FAIL': {
      return {
        ...state,
        slots: state.slots.map((s) => {
          if (s.id !== action.slotId || !s.script) return s;
          return { ...s, script: { ...s.script, pending: false } };
        }),
      };
    }

    case 'KEEP_SCRIPT_AS_IS': {
      const slot = state.slots.find((s) => s.id === action.slotId);
      if (!slot || !slot.script) return state;

      const fHash = factsHash(state.facts);
      const sHash = segmentHash(slot.segment);
      const curRev = slot.script.revisions[slot.script.cursor];
      if (!curRev) return state;

      const updatedRev: ScriptRevision = {
        ...curRev,
        basis: { facts: fHash, segment: sHash },
      };

      const nextRevs = [...slot.script.revisions];
      nextRevs[slot.script.cursor] = updatedRev;

      return {
        ...state,
        slots: state.slots.map((s) =>
          s.id === action.slotId && s.script
            ? {
                ...s,
                factsBasis: fHash,
                script: { ...s.script, revisions: nextRevs },
              }
            : s,
        ),
      };
    }

    // --- Line Actions ---
    case 'EDIT_LINE': {
      return mutateLineNode(state, action.lineUid, (line) => {
        const curVer = line.versions[line.cursor];
        if (curVer && curVer.text === action.text) return line;

        const newVersion: LineVersion = {
          id: generateUid(),
          label: 'Edited',
          text: action.text,
        };
        const nextVersions = [...line.versions, newVersion];
        return {
          ...line,
          versions: nextVersions,
          cursor: nextVersions.length - 1,
        };
      });
    }

    case 'REPHRASE_LINE_START': {
      return mutateLineNode(state, action.lineUid, (line) => ({
        ...line,
        pending: 'rephrase',
      }));
    }

    case 'REPHRASE_LINE_SUCCESS': {
      return mutateLineNode(state, action.lineUid, (line) => {
        const newVersion: LineVersion = {
          id: generateUid(),
          label: 'Rephrased',
          detail: action.tone,
          text: action.text,
        };
        const nextVersions = [...line.versions, newVersion];
        return {
          ...line,
          versions: nextVersions,
          cursor: nextVersions.length - 1,
          pending: undefined,
        };
      });
    }

    case 'REGENERATE_LINE_START': {
      return mutateLineNode(state, action.lineUid, (line) => ({
        ...line,
        pending: 'regenerate',
      }));
    }

    case 'REGENERATE_LINE_SUCCESS': {
      return mutateLineNode(state, action.lineUid, (line) => {
        const newVersion: LineVersion = {
          id: generateUid(),
          label: 'Regenerated',
          text: action.text,
        };
        const nextVersions = [...line.versions, newVersion];
        return {
          ...line,
          versions: nextVersions,
          cursor: nextVersions.length - 1,
          pending: undefined,
        };
      });
    }

    case 'LINE_ACTION_FAIL': {
      return mutateLineNode(state, action.lineUid, (line) => ({
        ...line,
        pending: undefined,
      }));
    }

    case 'DELETE_LINE': {
      return mutateLineNode(state, action.lineUid, (line) => {
        const newVersion: LineVersion = {
          id: generateUid(),
          label: 'Deleted',
          text: null,
        };
        const nextVersions = [...line.versions, newVersion];
        return {
          ...line,
          versions: nextVersions,
          cursor: nextVersions.length - 1,
        };
      });
    }

    case 'UNDO_LINE': {
      return mutateLineNode(state, action.lineUid, (line) => {
        if (line.cursor <= 0) return line;
        return { ...line, cursor: line.cursor - 1 };
      });
    }

    case 'REDO_LINE': {
      return mutateLineNode(state, action.lineUid, (line) => {
        if (line.cursor >= line.versions.length - 1) return line;
        return { ...line, cursor: line.cursor + 1 };
      });
    }

    case 'STEP_SCOPE': {
      const slot = state.slots.find((s) => s.id === state.activeSlotId);
      const doc = slot?.script;
      if (!doc) return state;

      // Line scope
      if (state.selection.kind === 'line') {
        const line = findLineNode(doc, state.selection.uid);
        if (!line) return state;
        const nextCursor = line.cursor + action.delta;
        if (nextCursor < 0 || nextCursor >= line.versions.length) return state;
        return mutateLineNode(state, line.uid, (l) => ({ ...l, cursor: nextCursor }));
      }

      // Reason group scope
      if (state.selection.kind === 'reason') {
        const reasonUid = state.selection.reasonUid;
        const rev = doc.revisions[doc.cursor];
        const reason = rev?.reasons.find((r) => r.uid === reasonUid);
        if (!reason) return state;
        const cover = resolveVisibleCover(doc, reason.cites);
        if (cover && cover.coverNodes.length === 1 && cover.coverNodes[0].type === 'group') {
          const group = cover.coverNodes[0] as GroupNode;
          const nextCursor = group.cursor + action.delta;
          if (nextCursor < 0 || nextCursor >= group.versions.length) return state;
          return mutateGroupNode(state, group.uid, (g) => ({ ...g, cursor: nextCursor }));
        }
      }

      // Script scope
      const nextCursor = doc.cursor + action.delta;
      if (nextCursor < 0 || nextCursor >= doc.revisions.length) return state;
      return {
        ...state,
        slots: state.slots.map((s) =>
          s.id === state.activeSlotId && s.script
            ? { ...s, script: { ...s.script, cursor: nextCursor } }
            : s,
        ),
      };
    }

    // --- Reason Group Actions ---
    case 'REWRITE_REASON_START': {
      const slot = state.slots.find((s) => s.id === state.activeSlotId);
      const doc = slot?.script;
      if (!doc) return state;

      const rev = doc.revisions[doc.cursor];
      const reason = rev?.reasons.find((r) => r.uid === action.reasonUid);
      if (!reason) return state;

      const updatedReasons = rev.reasons.map((r) =>
        r.uid === action.reasonUid ? { ...r, pending: true } : r,
      );
      const nextRev: ScriptRevision = { ...rev, reasons: updatedReasons };
      const nextRevs = [...doc.revisions];
      nextRevs[doc.cursor] = nextRev;

      let nextState: Workspace = {
        ...state,
        slots: state.slots.map((s) =>
          s.id === state.activeSlotId && s.script
            ? { ...s, script: { ...s.script, revisions: nextRevs } }
            : s,
        ),
      };

      const cover = resolveVisibleCover(doc, reason.cites);
      if (cover && cover.coverNodes.length === 1 && cover.coverNodes[0].type === 'group') {
        nextState = mutateGroupNode(nextState, cover.coverNodes[0].uid, (g) => ({ ...g, pending: true }));
      }
      return nextState;
    }

    case 'REWRITE_REASON_SUCCESS': {
      const slot = state.slots.find((s) => s.id === state.activeSlotId);
      const doc = slot?.script;
      if (!doc) return state;

      const rev = doc.revisions[doc.cursor];
      const reason = rev?.reasons.find((r) => r.uid === action.reasonUid);
      if (!reason) return state;

      const cover = resolveVisibleCover(doc, reason.cites);
      if (!cover) return state;

      // Build new LineNodes for the rewritten lines
      const newNodes: LineNode[] = action.newLines.map((nl) => ({
        type: 'line',
        uid: generateUid(),
        kind: nl.kind,
        cursor: 0,
        versions: [{ id: generateUid(), label: 'Original', text: nl.text }],
      }));

      const visibleUids = cover.coverNodes.flatMap(collectVisibleUids);
      const newUids = newNodes.map((n) => n.uid);
      const updatedReasons = rev.reasons.map((r) => {
        const touchesCover =
          r.uid === action.reasonUid || r.cites.some((id) => visibleUids.includes(id));
        return touchesCover
          ? {
              ...r,
              cites: Array.from(new Set([...r.cites, ...newUids])),
              pending: r.uid === action.reasonUid ? false : r.pending,
            }
          : r;
      });

      // If the cover is already a GroupNode, append a new GroupVersion
      if (cover.coverNodes.length === 1 && cover.coverNodes[0].type === 'group') {
        const group = cover.coverNodes[0] as GroupNode;
        const newGroupVer: GroupVersion = {
          id: generateUid(),
          label: 'Rewritten',
          children: newNodes,
        };
        const nextGroupVers = [...group.versions, newGroupVer];
        const nextState = mutateGroupNode(state, group.uid, (g) => ({
          ...g,
          versions: nextGroupVers,
          cursor: nextGroupVers.length - 1,
          pending: false,
        }));
        return {
          ...nextState,
          slots: nextState.slots.map((s) => {
            if (s.id !== nextState.activeSlotId || !s.script) return s;
            const curRev = s.script.revisions[s.script.cursor];
            if (!curRev) return s;
            const updatedRevs = [...s.script.revisions];
            updatedRevs[s.script.cursor] = { ...curRev, reasons: updatedReasons };
            return { ...s, script: { ...s.script, revisions: updatedRevs } };
          }),
        };
      }

      // Otherwise, WRAP the contiguous coverNodes into a new GroupNode
      const originalVersion: GroupVersion = {
        id: generateUid(),
        label: 'Original',
        children: cover.coverNodes,
      };
      const rewrittenVersion: GroupVersion = {
        id: generateUid(),
        label: 'Rewritten',
        children: newNodes,
      };

      const newGroup: GroupNode = {
        type: 'group',
        uid: generateUid(),
        cursor: 1, // point to rewritten version
        versions: [originalVersion, rewrittenVersion],
        pending: false,
      };

      // Splice new group into the current revision's top-level nodes
      const nextNodes = [...cover.parentList];
      nextNodes.splice(cover.startIndex, cover.coverNodes.length, newGroup);

      const nextRev: ScriptRevision = {
        ...rev,
        nodes: nextNodes,
        reasons: updatedReasons,
      };
      const nextRevs = [...doc.revisions];
      nextRevs[doc.cursor] = nextRev;

      return {
        ...state,
        slots: state.slots.map((s) =>
          s.id === state.activeSlotId && s.script
            ? { ...s, script: { ...s.script, revisions: nextRevs } }
            : s,
        ),
      };
    }

    case 'REWRITE_REASON_FAIL': {
      const slot = state.slots.find((s) => s.id === state.activeSlotId);
      const doc = slot?.script;
      if (!doc) return state;

      const rev = doc.revisions[doc.cursor];
      const reason = rev?.reasons.find((r) => r.uid === action.reasonUid);
      if (!reason) return state;

      const updatedReasons = rev.reasons.map((r) =>
        r.uid === action.reasonUid ? { ...r, pending: false } : r,
      );
      const nextRev: ScriptRevision = { ...rev, reasons: updatedReasons };
      const nextRevs = [...doc.revisions];
      nextRevs[doc.cursor] = nextRev;

      let nextState: Workspace = {
        ...state,
        slots: state.slots.map((s) =>
          s.id === state.activeSlotId && s.script
            ? { ...s, script: { ...s.script, revisions: nextRevs } }
            : s,
        ),
      };

      const cover = resolveVisibleCover(doc, reason.cites);
      if (cover && cover.coverNodes.length === 1 && cover.coverNodes[0].type === 'group') {
        nextState = mutateGroupNode(nextState, cover.coverNodes[0].uid, (g) => ({ ...g, pending: false }));
      }
      return nextState;
    }

    default:
      return state;
  }
}

/**
 * Helper to immutably update a LineNode across active tree nodes.
 */
function mutateLineNode(
  state: Workspace,
  lineUid: Uid,
  transform: (line: LineNode) => LineNode,
): Workspace {
  const slot = state.slots.find((s) => s.id === state.activeSlotId);
  if (!slot || !slot.script) return state;

  const doc = slot.script;
  const rev = doc.revisions[doc.cursor];
  if (!rev) return state;

  function walk(nodes: ScriptNode[]): ScriptNode[] {
    return nodes.map((node) => {
      if (node.type === 'line') {
        return node.uid === lineUid ? transform(node) : node;
      }
      if (node.type === 'group') {
        const curVer = node.versions[node.cursor];
        if (!curVer) return node;
        const nextChildren = walk(curVer.children);
        const nextVers = [...node.versions];
        nextVers[node.cursor] = { ...curVer, children: nextChildren };
        return { ...node, versions: nextVers };
      }
      return node;
    });
  }

  const nextNodes = walk(rev.nodes);
  const nextRev = { ...rev, nodes: nextNodes };
  const nextRevs = [...doc.revisions];
  nextRevs[doc.cursor] = nextRev;

  return {
    ...state,
    slots: state.slots.map((s) =>
      s.id === state.activeSlotId && s.script
        ? { ...s, script: { ...s.script, revisions: nextRevs } }
        : s,
    ),
  };
}

/**
 * Helper to immutably update a GroupNode across active tree nodes.
 */
function mutateGroupNode(
  state: Workspace,
  groupUid: Uid,
  transform: (group: GroupNode) => GroupNode,
): Workspace {
  const slot = state.slots.find((s) => s.id === state.activeSlotId);
  if (!slot || !slot.script) return state;

  const doc = slot.script;
  const rev = doc.revisions[doc.cursor];
  if (!rev) return state;

  function walk(nodes: ScriptNode[]): ScriptNode[] {
    return nodes.map((node) => {
      if (node.type === 'group') {
        if (node.uid === groupUid) return transform(node);
        const curVer = node.versions[node.cursor];
        if (!curVer) return node;
        const nextChildren = walk(curVer.children);
        const nextVers = [...node.versions];
        nextVers[node.cursor] = { ...curVer, children: nextChildren };
        return { ...node, versions: nextVers };
      }
      return node;
    });
  }

  const nextNodes = walk(rev.nodes);
  const nextRev = { ...rev, nodes: nextNodes };
  const nextRevs = [...doc.revisions];
  nextRevs[doc.cursor] = nextRev;

  return {
    ...state,
    slots: state.slots.map((s) =>
      s.id === state.activeSlotId && s.script
        ? { ...s, script: { ...s.script, revisions: nextRevs } }
        : s,
    ),
  };
}
