// apps/web/src/components/ResultsView.tsx
import { useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { GenerateResponse } from 'api-types';
import { SegmentCard } from './SegmentCard';
import { ScriptCard } from './ScriptCard';
import { ReasonList } from './ReasonList';

interface Props {
  data: GenerateResponse;
}

export function ResultsView({ data }: Props) {
  const uid = useId();
  const [active, setActive] = useState(0);
  const [pinnedReason, setPinnedReason] = useState<number | null>(null);
  const [hoverReason, setHoverReason] = useState<number | null>(null);
  const [hoverLine, setHoverLine] = useState<number | null>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const segment = data.segments[active];
  const script = data.scripts[active];

  function selectSegment(index: number) {
    setActive(index);
    setPinnedReason(null);
    setHoverReason(null);
    setHoverLine(null);
  }

  function handleTabKey(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    const count = data.segments.length;
    let next = index;
    if (e.key === 'ArrowRight') next = (index + 1) % count;
    else if (e.key === 'ArrowLeft') next = (index - 1 + count) % count;
    else return;
    e.preventDefault();
    selectSegment(next);
    tabRefs.current[next]?.focus();
  }

  // Bi-directional highlighting.
  // Reason -> lines: the hovered reason wins over the pinned one.
  const focusedReason = hoverReason ?? pinnedReason;
  const litLineIds = new Set<number>(
    focusedReason !== null ? (script?.reasons[focusedReason]?.line_ids ?? []) : [],
  );

  // Line -> reasons: hovering a line lights every reason that cites it.
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
      {data.facts.length > 0 && (
        <section className="results-section">
          <div className="section-head">
            <h2>Facts the scripts rely on</h2>
            <p>Pulled from your description and photo. The scripts only use these.</p>
          </div>
          <ul className="chip-list">
            {data.facts.map((fact, i) => (
              <li key={i} className="chip">
                {fact}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="results-section">
        <div className="section-head">
          <h2>Customer segments</h2>
          <p>Each segment has its own script. Switch between them without waiting.</p>
        </div>

        <div className="tabs" role="tablist" aria-label="Customer segments">
          {data.segments.map((s, i) => (
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
              className={`tab${active === i ? ' is-active' : ''}`}
              onClick={() => selectSegment(i)}
              onKeyDown={(e) => handleTabKey(e, i)}
            >
              {s.name}
            </button>
          ))}
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
          ) : (
            <p className="hint">No script came back for this segment. Try generating again.</p>
          )}
        </div>
      </section>
    </div>
  );
}
