// apps/web/src/components/ScriptCard.tsx
import { useEffect, useMemo, useRef, useState } from 'react';
import type { LineKind, Script } from 'api-types';
import { IconCopy, IconCheck } from '@tabler/icons-react';

const SECONDS_PER_WORD = 0.4; // roughly 2.5 spoken words per second
const HOOK_WINDOW_SECONDS = 3;

const KIND_LABEL: Record<LineKind, string> = {
  hook: 'Hook',
  concept: 'Concept',
  cta: 'Call to action',
};

function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function mmss(seconds: number): string {
  const total = Math.round(seconds);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

async function copyToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    document.execCommand('copy');
    document.body.removeChild(area);
  }
}

interface Props {
  script: Script;
  /** Line ids highlighted because a reason is hovered or pinned. */
  litLineIds: ReadonlySet<number>;
  hoveredLineId: number | null;
  /** True while a reason is active, so unrelated lines can fade back. */
  reasonFocused: boolean;
  onLineHover: (id: number | null) => void;
}

export function ScriptCard({
  script,
  litLineIds,
  hoveredLineId,
  reasonFocused,
  onLineHover,
}: Props) {
  const [copied, setCopied] = useState(false);
  const copyTimer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (copyTimer.current) window.clearTimeout(copyTimer.current);
    },
    [],
  );

  const timed = useMemo(() => {
    const lines = [...script.lines].sort((a, b) => a.id - b.id);
    let cursor = 0;
    let totalWords = 0;
    const rows: { line: typeof lines[number]; words: number; duration: number; start: number }[] = [];
    for (const line of lines) {
      const words = countWords(line.text);
      const duration = Math.max(words * SECONDS_PER_WORD, 0.8);
      rows.push({ line, words, duration, start: cursor });
      cursor += duration;
      totalWords += words;
    }
    return {
      rows,
      total: cursor,
      words: totalWords,
    };
  }, [script.lines]);

  async function handleCopy() {
    const text = timed.rows.map((r) => r.line.text).join('\n\n');
    await copyToClipboard(text);
    setCopied(true);
    if (copyTimer.current) window.clearTimeout(copyTimer.current);
    copyTimer.current = window.setTimeout(() => setCopied(false), 2000);
  }

  const tickPercent = Math.min(HOOK_WINDOW_SECONDS / (timed.total || 1), 1) * 100;

  return (
    <article className="panel script-card">
      <header className="script-head">
        <div>
          <h3>Script</h3>
          <p className="hint">
            About {Math.round(timed.total)} seconds spoken, {timed.words} words
          </p>
        </div>
        <button
          type="button"
          className={`btn btn-quiet${copied ? ' is-done' : ''}`}
          onClick={handleCopy}
        >
          {copied ? (
            <>
              <IconCheck size={16} aria-hidden="true" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <IconCopy size={16} aria-hidden="true" />
              <span>Copy script</span>
            </>
          )}
        </button>
      </header>

      <div className="timeline-wrap">
        <div className="timeline" aria-hidden="true">
          {timed.rows.map(({ line, duration }) => (
            <span
              key={line.id}
              className={`tl-seg${
                litLineIds.has(line.id) || hoveredLineId === line.id ? ' is-on' : ''
              }`}
              data-kind={line.kind}
              style={{ flexGrow: duration }}
            />
          ))}
        </div>
        <span className="tl-tick" style={{ left: `${tickPercent}%` }} aria-hidden="true">
          <span className="tl-tick-label">3s</span>
        </span>
      </div>

      <ol className="lines">
        {timed.rows.map(({ line, start }) => {
          const lit = litLineIds.has(line.id);
          const cls = [
            'line',
            lit ? 'is-lit' : '',
            reasonFocused && !lit ? 'is-dim' : '',
            hoveredLineId === line.id ? 'is-hover' : '',
          ]
            .filter(Boolean)
            .join(' ');

          return (
            <li
              key={line.id}
              className={cls}
              data-kind={line.kind}
              tabIndex={0}
              onMouseEnter={() => onLineHover(line.id)}
              onMouseLeave={() => onLineHover(null)}
              onFocus={() => onLineHover(line.id)}
              onBlur={() => onLineHover(null)}
            >
              <div className="ln-gutter">
                <span className="ln-id">{line.id}</span>
                <span className="ln-time">{mmss(start)}</span>
              </div>
              <div className="ln-body">
                <span className="kind">{KIND_LABEL[line.kind] ?? line.kind}</span>
                <p className="ln-text">{line.text}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </article>
  );
}
