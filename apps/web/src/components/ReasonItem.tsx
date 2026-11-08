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

/**
 * Replaces the inner <li> markup in ReasonList. The refresh control is a sibling of the card button.
 */
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
        onClick={(e) => {
          e.stopPropagation();
          p.onRefresh();
        }}
      >
        <IconRefresh size={16} aria-hidden="true" />
      </button>
    </li>
  );
}
