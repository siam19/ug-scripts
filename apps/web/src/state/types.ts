import type { Angle, LineKind, Segment } from 'api-types';

export type Uid = string;

// --- Script Tree: lines and groups both carry versions ---
export type LineVersionLabel = 'Original' | 'Edited' | 'Rephrased' | 'Regenerated' | 'Deleted';

export interface LineVersion {
  id: Uid;
  label: LineVersionLabel;
  detail?: string; // e.g. the tone used for a rephrase ("punchier", "casual")
  text: string | null; // null = deleted (tombstone)
  speaker?: string | null;
  visual?: string | null;
}

export interface LineNode {
  type: 'line';
  uid: Uid;
  kind: LineKind;
  speaker?: string | null;
  visual?: string | null;
  versions: LineVersion[];
  cursor: number;
  pending?: 'rephrase' | 'regenerate';
}

export type GroupVersionLabel = 'Original' | 'Rewritten';

export interface GroupVersion {
  id: Uid;
  label: GroupVersionLabel;
  children: ScriptNode[];
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
  cites: Uid[]; // LineNode uids cited by this reason
  pending?: boolean;
}

export interface Basis {
  facts: string; // content hash of facts
  segment: string; // content hash of segment
}

export interface ScriptRevision {
  id: Uid;
  label: 'Original' | 'Rewritten';
  basis: Basis;
  nodes: ScriptNode[];
  reasons: ReasonItem[];
}

export interface ScriptDoc {
  revisions: ScriptRevision[];
  cursor: number;
  pending?: boolean;
}

// --- Workspace State ---
export interface FactItem {
  id: Uid;
  factId?: number;
  text: string;
  value?: 'core' | 'visual' | 'trivia';
  original: string | null; // original null = user-added
}

export interface SegmentSlot {
  id: Uid;
  segment: Segment;
  edited: boolean;
  factsBasis: string; // facts hash when segment was generated
  previous?: Segment; // for undo replacement
  pending?: boolean;
  script: ScriptDoc | null;
  scriptStatus: 'streaming' | 'ready' | 'error';
}

export type Selection =
  | { kind: 'none' }
  | { kind: 'reason'; reasonUid: Uid }
  | { kind: 'line'; uid: Uid };

export interface WorkspaceMeta {
  name: string;
  market: string;
  language: 'en' | 'bn';
  script_format?: 'ugc' | 'commercial_30s';
}

export interface Workspace {
  meta: WorkspaceMeta;
  facts: FactItem[];
  angles: Angle[];
  slots: SegmentSlot[];
  activeSlotId: Uid;
  selection: Selection;
}
