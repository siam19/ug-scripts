import type {
  GroupNode,
  LineNode,
  LineVersion,
  ScriptDoc,
  ScriptNode,
  Uid,
  Workspace,
} from './types';
import type { ScopeVersion } from '../components/VersionRail';

export const SECONDS_PER_WORD = 0.4; // ~2.5 spoken words per second

export function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export function formatTime(seconds: number): string {
  const total = Math.round(seconds);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

export interface ResolvedLineItem {
  node: LineNode;
  version: LineVersion;
  isDeleted: boolean;
}

/**
 * Traverses active revision and active group versions to collect all visible lines and tombstones.
 */
export function getVisibleLineItems(doc: ScriptDoc | null): ResolvedLineItem[] {
  if (!doc || doc.revisions.length === 0) return [];
  const currentRev = doc.revisions[doc.cursor];
  if (!currentRev) return [];

  const items: ResolvedLineItem[] = [];

  function walk(nodes: ScriptNode[]) {
    for (const node of nodes) {
      if (node.type === 'line') {
        const ver = node.versions[node.cursor];
        if (ver) {
          items.push({
            node,
            version: ver,
            isDeleted: ver.text === null,
          });
        }
      } else if (node.type === 'group') {
        const groupVer = node.versions[node.cursor];
        if (groupVer) {
          walk(groupVer.children);
        }
      }
    }
  }

  walk(currentRev.nodes);
  return items;
}

/**
 * Returns only visible non-deleted lines.
 */
export function getActiveLines(doc: ScriptDoc | null): { node: LineNode; text: string }[] {
  return getVisibleLineItems(doc)
    .filter((item) => !item.isDeleted && item.version.text !== null)
    .map((item) => ({ node: item.node, text: item.version.text! }));
}

/**
 * Finds a LineNode anywhere in the active revision of a script doc.
 */
export function findLineNode(doc: ScriptDoc | null, lineUid: Uid): LineNode | null {
  if (!doc) return null;
  const currentRev = doc.revisions[doc.cursor];
  if (!currentRev) return null;

  function walk(nodes: ScriptNode[]): LineNode | null {
    for (const node of nodes) {
      if (node.type === 'line') {
        if (node.uid === lineUid) return node;
      } else if (node.type === 'group') {
        const groupVer = node.versions[node.cursor];
        if (groupVer) {
          const found = walk(groupVer.children);
          if (found) return found;
        }
      }
    }
    return null;
  }

  return walk(currentRev.nodes);
}

/**
 * Returns the active children list at the top level of the current script revision.
 */
export function getActiveTopLevelNodes(doc: ScriptDoc | null): ScriptNode[] {
  if (!doc || doc.revisions.length === 0) return [];
  const rev = doc.revisions[doc.cursor];
  return rev ? rev.nodes : [];
}

/**
 * Finds all visible line UIDs inside a given ScriptNode (recursing active group versions).
 */
export function collectVisibleUids(node: ScriptNode): Uid[] {
  if (node.type === 'line') {
    const ver = node.versions[node.cursor];
    return ver && ver.text !== null ? [node.uid] : [];
  }
  const ver = node.versions[node.cursor];
  if (!ver) return [];
  return ver.children.flatMap(collectVisibleUids);
}

/**
 * Resolves which active top-level / ancestor nodes a reason covers.
 * Handles contiguous grouping and wrapping for reason regeneration.
 */
export function resolveVisibleCover(
  doc: ScriptDoc | null,
  citedUids: Uid[],
): {
  coverNodes: ScriptNode[];
  startIndex: number;
  endIndex: number;
  parentList: ScriptNode[];
} | null {
  if (!doc || citedUids.length === 0) return null;
  const rev = doc.revisions[doc.cursor];
  if (!rev) return null;

  const topNodes = rev.nodes;
  const citedSet = new Set(citedUids);

  // Check top-level nodes that contain any cited UIDs
  const matchingIndices: number[] = [];
  topNodes.forEach((node, idx) => {
    const uidsInNode = collectVisibleUids(node);
    if (uidsInNode.some((id) => citedSet.has(id))) {
      matchingIndices.push(idx);
    }
  });

  if (matchingIndices.length === 0) return null;

  const startIndex = Math.min(...matchingIndices);
  const endIndex = Math.max(...matchingIndices);
  const coverNodes = topNodes.slice(startIndex, endIndex + 1);

  return {
    coverNodes,
    startIndex,
    endIndex,
    parentList: topNodes,
  };
}

/**
 * Resolves the active version scope that chevrons and undo/redo should act on:
 * - Line selection -> that line's versions
 * - Reason selection -> that reason's group versions (if group exists and count > 1)
 * - None / Script selection -> whole script revisions (if count > 1)
 */
export function getActiveScope(ws: Workspace): ScopeVersion | null {
  const slot = ws.slots.find((s) => s.id === ws.activeSlotId);
  const doc = slot?.script;
  if (!doc) return null;

  if (ws.selection.kind === 'line') {
    const lineUid = ws.selection.uid;
    const line = findLineNode(doc, lineUid);
    if (!line) return null;
    const curVer = line.versions[line.cursor];
    return {
      type: 'line',
      index: line.cursor,
      count: line.versions.length,
      label: curVer ? `${curVer.label}${curVer.detail ? ` · ${curVer.detail}` : ''}` : 'Original',
      targetUid: line.uid,
    };
  }

  if (ws.selection.kind === 'reason') {
    const reasonUid = ws.selection.reasonUid;
    const rev = doc.revisions[doc.cursor];
    const reason = rev?.reasons.find((r) => r.uid === reasonUid);
    if (!reason) return null;

    const cover = resolveVisibleCover(doc, reason.cites);
    if (cover && cover.coverNodes.length === 1 && cover.coverNodes[0].type === 'group') {
      const group = cover.coverNodes[0] as GroupNode;
      const curVer = group.versions[group.cursor];
      return {
        type: 'group',
        index: group.cursor,
        count: group.versions.length,
        label: curVer?.label ?? 'Original',
        targetUid: group.uid,
      };
    }
  }

  // Nothing selected -> whole script revisions
  if (doc.revisions.length > 1) {
    const curRev = doc.revisions[doc.cursor];
    return {
      type: 'script',
      index: doc.cursor,
      count: doc.revisions.length,
      label: curRev ? `Version ${doc.cursor + 1} of ${doc.revisions.length}: ${curRev.label}` : '',
    };
  }

  return null;
}
