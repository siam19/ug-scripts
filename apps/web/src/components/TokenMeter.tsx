// apps/web/src/components/TokenMeter.tsx
import { useEffect, useId, useRef, useState } from 'react';
import type { TokenTracker } from '../hooks/useTokenTracker';

interface Props {
  tracker: TokenTracker;
}

function MeterGlyph() {
  return (
    <svg className="meter-glyph" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <rect x="1.5" y="9.5" width="3" height="5" rx="1" />
      <rect x="6.5" y="5.5" width="3" height="9" rx="1" />
      <rect x="11.5" y="1.5" width="3" height="13" rx="1" />
    </svg>
  );
}

/**
 * Masthead usage pill. Click or Enter opens a small "receipt" with session and all-time totals,
 * plus an input/output split when the API reports one.
 */
export function TokenMeter({ tracker }: Props) {
  const popId = useId();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false);
        btnRef.current?.focus();
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const { sessionTokens, lifetimeTokens, sessionInput, sessionOutput } = tracker;
  const split = sessionInput + sessionOutput;
  const inputPct = split > 0 ? Math.round((sessionInput / split) * 100) : 0;

  return (
    <div className="meter" ref={wrapRef}>
      <button
        ref={btnRef}
        type="button"
        className={`meter-btn${open ? ' is-open' : ''}`}
        aria-expanded={open}
        aria-controls={popId}
        aria-label={`Token usage: ${sessionTokens.toLocaleString()} this session`}
        onClick={() => setOpen((o) => !o)}
      >
        <MeterGlyph />
        <span className="meter-label">Tokens</span>
        {/* Keyed by the value so the tick animation replays whenever usage changes. */}
        <span
          key={sessionTokens}
          className={`meter-value${sessionTokens > 0 ? ' is-tick' : ''}`}
        >
          {tracker.formattedSession}
        </span>
      </button>

      {open && (
        <div className="meter-pop" id={popId} role="region" aria-label="Token usage">
          <p className="meter-pop-title">Usage</p>

          <dl className="meter-ledger">
            <div>
              <dt>This session</dt>
              <dd className="meter-leader" aria-hidden="true" />
              <dd>{sessionTokens.toLocaleString()}</dd>
            </div>
            <div>
              <dt>All time</dt>
              <dd className="meter-leader" aria-hidden="true" />
              <dd>{lifetimeTokens.toLocaleString()}</dd>
            </div>
          </dl>

          {split > 0 && (
            <div className="meter-split">
              <div className="meter-split-bar" role="img" aria-label={`Input ${inputPct}%, output ${100 - inputPct}%`}>
                <i style={{ width: `${inputPct}%` }} />
              </div>
              <div className="meter-split-legend">
                <span>
                  <b className="dot is-in" /> Input {sessionInput.toLocaleString()}
                </span>
                <span>
                  <b className="dot is-out" /> Output {sessionOutput.toLocaleString()}
                </span>
              </div>
            </div>
          )}

          <p className="meter-note">
            Counted from the usage the API reports after each request. The all-time total is stored
            in this browser.
          </p>
        </div>
      )}
    </div>
  );
}
