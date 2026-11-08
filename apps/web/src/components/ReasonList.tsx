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
