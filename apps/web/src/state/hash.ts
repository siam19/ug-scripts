import type { Segment } from 'api-types';
import type { FactItem, SegmentSlot, Workspace } from './types';

/**
 * Fast 32-bit djb2 string hash formatted in base-36.
 */
export function hash(s: string): string {
  let h = 5381;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  }
  return (h >>> 0).toString(36);
}

/**
 * Stable content hash of current facts list (sorted, whitespace trimmed).
 */
export function factsHash(facts: FactItem[]): string {
  return hash(facts.map((x) => x.text.trim()).sort().join('\n'));
}

/**
 * Stable content hash of a segment persona definition.
 */
export function segmentHash(s: Segment): string {
  return hash(
    JSON.stringify([
      s.name.trim(),
      s.who.trim(),
      s.pain_point.trim(),
      [...s.platforms].sort(),
    ]),
  );
}

export type StaleReason = 'facts' | 'segment';

/**
 * Derives whether a slot's current script revision was built from earlier facts or an earlier segment.
 */
export function scriptStaleReasons(ws: Workspace, slot: SegmentSlot): StaleReason[] {
  const rev = slot.script?.revisions[slot.script.cursor];
  if (!rev) return [];
  const out: StaleReason[] = [];
  if (rev.basis.facts !== factsHash(ws.facts)) out.push('facts');
  if (rev.basis.segment !== segmentHash(slot.segment)) out.push('segment');
  return out;
}

/**
 * Determines whether a slot requires regeneration:
 * - Its script is stale relative to current facts or segment, OR
 * - Its segment was not hand-edited and predates the current facts.
 */
export function slotNeedsRegen(ws: Workspace, s: SegmentSlot): boolean {
  return scriptStaleReasons(ws, s).length > 0 || (!s.edited && s.factsBasis !== factsHash(ws.facts));
}

export function scriptStaleMessage(reasons: StaleReason[], replaced: boolean): string {
  if (replaced) return 'This script was written for the previous segment.';
  const what =
    reasons.length === 2
      ? 'the facts and the segment'
      : reasons[0] === 'facts'
        ? 'the facts'
        : 'the segment';
  return `Written before you changed ${what}.`;
}
