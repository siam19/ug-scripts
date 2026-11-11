// apps/web/src/components/LoadingState.tsx
import { useEffect, useState } from 'react';

const STAGES = [
  {
    title: 'Analyzing packaging and verifying facts',
    note: 'Reading the photo and your description for claims the scripts can safely use.',
    activities: [
      'Analyzing Image(s) & packaging',
      'Detecting product features & visual cues',
      'Extracting core claims & ingredients',
      'Formulating creative psychological angles',
      'Grounding visual anchors from pack shot',
    ],
  },
  {
    title: 'Writing 3 creator scripts',
    note: 'One script per customer segment, each with its own hook style.',
    activities: [
      'Envisioning Market Segments & buyer personas',
      'Crafting 3-second scroll-stopping hooks',
      'Drafting dialogue lines with psychological pacing',
      'Polishing natural speech rhythm & cadence',
      'Synthesizing conversion marketing rationales',
    ],
  },
];

const STAGE_ONE_SECONDS = 7;

export function LoadingState() {
  const [elapsed, setElapsed] = useState(0);
  const [activityIndex, setActivityIndex] = useState(0);
  const [dotCount, setDotCount] = useState(1);

  useEffect(() => {
    const start = Date.now();
    const timer = window.setInterval(() => {
      setElapsed((Date.now() - start) / 1000);
    }, 250);
    return () => window.clearInterval(timer);
  }, []);

  // Cycle text activity every ~2.6 seconds
  useEffect(() => {
    const timer = window.setInterval(() => {
      setActivityIndex((idx) => idx + 1);
    }, 2600);
    return () => window.clearInterval(timer);
  }, []);

  // Moving ellipsis animation: . -> .. -> ... every 420ms
  useEffect(() => {
    const timer = window.setInterval(() => {
      setDotCount((d) => (d % 3) + 1);
    }, 420);
    return () => window.clearInterval(timer);
  }, []);

  const stage = elapsed < STAGE_ONE_SECONDS ? 0 : 1;
  const percent = Math.round(92 * (1 - Math.exp(-elapsed / 12)));

  const dots = '.'.repeat(dotCount);

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
          const currentActivity = s.activities[activityIndex % s.activities.length];
          const cleanActivity = currentActivity.replace(/[.…]+$/, '');
          return (
            <li key={s.title} className={`stage is-${state}`}>
              <span className="stage-mark" aria-hidden="true" />
              <div>
                <strong>{s.title}</strong>
                {state === 'active' && (
                  <div className="stage-ticker-wrap">
                    <span className="stage-ticker-text">
                      {cleanActivity}
                      <span className="stage-ticker-dots" aria-hidden="true">{dots}</span>
                    </span>
                  </div>
                )}
                {/* <p>{s.note}</p> */}
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
