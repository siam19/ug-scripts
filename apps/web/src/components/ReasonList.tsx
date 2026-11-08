import { ReasonItem } from './ReasonItem';
import type { ReasonRef } from './ReasonItem';

export interface ReasonDisplayItem {
  uid: string;
  title: string;
  why: string;
  refs: ReasonRef[];
  orphan: boolean;
  pending?: boolean;
}

interface Props {
  items: ReasonDisplayItem[];
  litIndexes: ReadonlySet<number>;
  pinnedIndex: number | null;
  onHover: (index: number | null) => void;
  onPin: (index: number) => void;
  onRefresh: (reasonUid: string) => void;
}

export function ReasonList({
  items,
  litIndexes,
  pinnedIndex,
  onHover,
  onPin,
  onRefresh,
}: Props) {
  return (
    <aside className="panel reasons">
      <h3>Why this script should work</h3>
      <p className="hint">
        Hover or select a reason to light up the lines it points to. Click the refresh
        icon on a technique to rewrite its associated lines.
      </p>

      <ul className="reason-list">
        {items.map((item, i) => (
          <ReasonItem
            key={item.uid}
            title={item.title}
            why={item.why}
            refs={item.refs}
            orphan={item.orphan}
            lit={litIndexes.has(i)}
            pinned={pinnedIndex === i}
            pending={Boolean(item.pending)}
            onHover={(hovering) => onHover(hovering ? i : null)}
            onPin={() => onPin(i)}
            onRefresh={() => onRefresh(item.uid)}
          />
        ))}
      </ul>
    </aside>
  );
}
