// apps/web/src/components/ResultsView.tsx
import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { ProgressiveGenerateResponse } from 'api-types';
import { SegmentCard } from './SegmentCard';
import { ScriptCard } from './ScriptCard';
import { ReasonList } from './ReasonList';

interface Props {
  data: ProgressiveGenerateResponse;
  isStreaming?: boolean;
}

export function ResultsView({ data, isStreaming = false }: Props) {
  const uid = useId();
  const [active, setActive] = useState(0);
  const [pinnedReason, setPinnedReason] = useState<number | null>(null);
  const [hoverReason, setHoverReason] = useState<number | null>(null);
  const [hoverLine, setHoverLine] = useState<number | null>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const totalFacts = data.facts.length;
  const totalSegments = data.segments.length;

  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Staggered population: populate facts chips first, then customer segments
  const [visibleFactsCount, setVisibleFactsCount] = useState(() =>
    prefersReducedMotion ? totalFacts : 0,
  );
  const [visibleSegmentsCount, setVisibleSegmentsCount] = useState(() =>
    prefersReducedMotion ? totalSegments : 0,
  );

  useEffect(() => {
    if (prefersReducedMotion) return;

    let timer: number | null = null;

    if (visibleFactsCount < totalFacts) {
      timer = window.setTimeout(
        () => {
          setVisibleFactsCount((c) => Math.min(c + 1, totalFacts));
        },
        visibleFactsCount === 0 ? 60 : 130,
      );
    } else if (visibleSegmentsCount < totalSegments) {
      timer = window.setTimeout(
        () => {
          setVisibleSegmentsCount((c) => Math.min(c + 1, totalSegments));
        },
        visibleSegmentsCount === 0 ? 180 : 220,
      );
    }

    return () => {
      if (timer) window.clearTimeout(timer);
    };
  }, [
    visibleFactsCount,
    visibleSegmentsCount,
    totalFacts,
    totalSegments,
    prefersReducedMotion,
  ]);

  const segment = data.segments[active];
  const script = data.scripts[active];

  function selectSegment(index: number) {
    setActive(index);
    setPinnedReason(null);
    setHoverReason(null);
    setHoverLine(null);
  }

  function handleTabKey(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    const count = Math.max(visibleSegmentsCount, 1);
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
      {totalFacts > 0 && (
        <section className="results-section">
          <div className="section-head">
            <h2>Facts the scripts rely on</h2>
            <p>Pulled from your description and photo. The scripts only use these.</p>
          </div>
          <ul className="chip-list">
            {data.facts.slice(0, visibleFactsCount).map((fact, i) => (
              <li key={i} className="chip chip-animated">
                {fact}
              </li>
            ))}
          </ul>
        </section>
      )}

      {visibleSegmentsCount > 0 && (
        <section className="results-section segment-section-animated">
          <div className="section-head">
            <h2>Customer segments</h2>
            <p>
              Auto-generated target demographics based on your product details and packaging.
              Each segment has its own tailored script—switch between them without waiting.
            </p>
          </div>

          <div className="tabs" role="tablist" aria-label="Customer segments">
            {data.segments.slice(0, visibleSegmentsCount).map((s, i) => {
              const isReady = Boolean(data.scripts[i]);
              return (
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
                  className={`tab tab-animated${active === i ? ' is-active' : ''}`}
                  onClick={() => selectSegment(i)}
                  onKeyDown={(e) => handleTabKey(e, i)}
                >
                  <span>
                    {i + 1}. {s.name}
                  </span>
                  {isStreaming && !isReady && (
                    <span
                      className="tab-status-dot"
                      title="Generating script…"
                      aria-label="Generating script"
                    />
                  )}
                </button>
              );
            })}
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
            ) : isStreaming ? (
              <div className="panel script-skeleton-card">
                <div className="script-skeleton-head">
                  <span className="rec-dot" aria-hidden="true" />
                  <h3>Writing script for {segment?.name ?? 'segment'}…</h3>
                </div>
                <p className="hint">Crafting hook, timestamped lines, and psychological reasoning…</p>
                <div className="skeleton" aria-hidden="true">
                  <span style={{ height: '20px', width: '92%' }} />
                  <span style={{ height: '20px', width: '78%' }} />
                  <span style={{ height: '20px', width: '85%' }} />
                  <span style={{ height: '20px', width: '60%' }} />
                </div>
              </div>
            ) : (
              <p className="hint">No script came back for this segment. Try generating again.</p>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
