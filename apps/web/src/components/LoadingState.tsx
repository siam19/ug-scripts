// apps/web/src/components/LoadingState.tsx
import { useEffect, useState } from 'react';

const STAGES = [
  {
    title: 'Analyzing packaging and verifying facts',
    note: 'Reading the photo and your description for claims the scripts can safely use.',
  },
  {
    title: 'Writing 3 creator scripts',
    note: 'One script per customer segment, each with its own hook style.',
  },
];

// Stage 1 (image + facts) usually finishes first; the API reports no progress,
// so this switch is a time-based estimate.
const STAGE_ONE_SECONDS = 7;

export function LoadingState() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const timer = window.setInterval(() => {
      setElapsed((Date.now() - start) / 1000);
    }, 250);
    return () => window.clearInterval(timer);
  }, []);

  const stage = elapsed < STAGE_ONE_SECONDS ? 0 : 1;
  const percent = Math.round(92 * (1 - Math.exp(-elapsed / 12)));

  return (
    <div className="panel loading" role="status" aria-live="polite">
      <div className="loading-head">
        <h2>Writing your scripts</h2>
        <span className="hint">{Math.floor(elapsed)}s elapsed. Usually 10 to 20 seconds.</span>
      </div>

      <div className="progress" aria-hidden="true">
        <span style={{ width: `${percent}%` }} />
      </div>

      <ol className="stages">
        {STAGES.map((s, i) => {
          const state = i < stage ? 'done' : i === stage ? 'active' : 'pending';
          return (
            <li key={s.title} className={`stage is-${state}`}>
              <span className="stage-mark" aria-hidden="true" />
              <div>
                <strong>{s.title}</strong>
                <p>{s.note}</p>
              </div>
            </li>
          );
        })}
      </ol>

      {elapsed > 25 && (
        <p className="hint">
          This is taking longer than usual. The request is still running.
        </p>
      )}

      <div className="skeleton" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
