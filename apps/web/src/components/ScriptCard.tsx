import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { LineKind } from 'api-types';
import { IconCheck, IconChevronLeft, IconChevronRight, IconCopy } from '@tabler/icons-react';
import {
  countWords,
  formatTime,
  getVisibleLineItems,
  SECONDS_PER_WORD,
} from '../state/script-tree';
import type { ResolvedLineItem } from '../state/script-tree';
import type { ScriptDoc, Uid } from '../state/types';
import { LineTombstone, ScriptLine } from './ScriptLine';
import type { LineView } from './ScriptLine';
import { VersionRail } from './VersionRail';
import type { ScopeVersion } from './VersionRail';

const HOOK_WINDOW_SECONDS = 3;

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

export interface PersonaCyclerInfo {
  current: number;
  total: number;
  name: string;
  onPrev: () => void;
  onNext: () => void;
}

interface Props {
  doc: ScriptDoc;
  scope: ScopeVersion | null;
  selectedLineUid: Uid | null;
  litLineUids: ReadonlySet<Uid>;
  hoveredLineUid: Uid | null;
  reasonFocused: boolean;
  recentlyChangedUids?: ReadonlySet<Uid>;
  personaInfo?: PersonaCyclerInfo;
  onLineHover: (uid: Uid | null) => void;
  onLineSelect: (uid: Uid | null) => void;
  onEditLine: (uid: Uid, text: string) => void;
  onRephraseLine: (uid: Uid) => void;
  onRegenerateLine: (uid: Uid) => void;
  onUndoLine: (uid: Uid) => void;
  onRedoLine: (uid: Uid) => void;
  onDeleteLine: (uid: Uid) => void;
  onStepScope: (delta: -1 | 1) => void;
}

export function ScriptCard({
  doc,
  scope,
  selectedLineUid,
  litLineUids,
  hoveredLineUid,
  reasonFocused,
  recentlyChangedUids = new Set(),
  personaInfo,
  onLineHover,
  onLineSelect,
  onEditLine,
  onRephraseLine,
  onRegenerateLine,
  onUndoLine,
  onRedoLine,
  onDeleteLine,
  onStepScope,
}: Props) {
  const [copied, setCopied] = useState(false);
  const copyTimer = useRef<number | null>(null);
  const cardRef = useRef<HTMLElement>(null);
  const [railTopY, setRailTopY] = useState<number | null>(null);

  // Live draft map from typing in textareas
  const [drafts, setDrafts] = useState<Record<Uid, string>>({});

  useEffect(
    () => () => {
      if (copyTimer.current) window.clearTimeout(copyTimer.current);
    },
    [],
  );

  function handleDraft(uid: Uid, text: string | null) {
    setDrafts((prev) => {
      if (text === null) {
        const next = { ...prev };
        delete next[uid];
        return next;
      }
      return { ...prev, [uid]: text };
    });
  }

  // Derive visible lines & timing
  const { lineViews, totalWords, totalSeconds, timelineRows } = useMemo(() => {
    const rawItems: ResolvedLineItem[] = getVisibleLineItems(doc);
    let cursorTime = 0;
    let wordSum = 0;
    let displayNo = 1;

    const views: LineView[] = [];
    const tlRows: { id: Uid; kind: LineKind; duration: number }[] = [];

    for (const item of rawItems) {
      if (item.isDeleted) {
        continue;
      }

      const activeText = drafts[item.node.uid] ?? item.version.text ?? '';
      const words = countWords(activeText);
      const duration = Math.max(words * SECONDS_PER_WORD, 0.8);
      const startTime = cursorTime;

      cursorTime += duration;
      wordSum += words;

      views.push({
        uid: item.node.uid,
        kind: item.node.kind,
        speaker: item.version.speaker ?? item.node.speaker,
        visual: item.version.visual ?? item.node.visual,
        text: activeText,
        no: displayNo++,
        time: formatTime(startTime),
        version: {
          index: item.node.cursor,
          count: item.node.versions.length,
          label: `${item.version.label}${item.version.detail ? ` · ${item.version.detail}` : ''}`,
        },
        canUndo: item.node.cursor > 0,
        canRedo: item.node.cursor < item.node.versions.length - 1,
        undoHint:
          item.node.cursor > 0
            ? item.node.versions[item.node.cursor - 1]?.label
            : undefined,
        pending: item.node.pending,
      });

      tlRows.push({
        id: item.node.uid,
        kind: item.node.kind,
        duration,
      });
    }

    return {
      lineViews: views,
      totalWords: wordSum,
      totalSeconds: cursorTime,
      timelineRows: tlRows,
    };
  }, [doc, drafts]);

  const canDelete = lineViews.length > 1;

  // Dynamic vertical centering for VersionRail chevrons aligned with active selection
  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!card) return;

    function updateRailPosition() {
      if (!card) return;
      const cardRect = card.getBoundingClientRect();
      if (cardRect.height === 0) return;

      let targetCenterY: number | null = null;

      if (selectedLineUid) {
        const selectedEl = card.querySelector<HTMLElement>(`[data-line-uid="${selectedLineUid}"]`);
        if (selectedEl) {
          const elRect = selectedEl.getBoundingClientRect();
          targetCenterY = elRect.top + elRect.height / 2 - cardRect.top;
        }
      } else if (litLineUids.size > 0) {
        const litEls = Array.from(card.querySelectorAll<HTMLElement>('.line.is-lit'));
        if (litEls.length > 0) {
          const first = litEls[0].getBoundingClientRect();
          let minTop = first.top;
          let maxBottom = first.bottom;
          for (let i = 1; i < litEls.length; i++) {
            const rect = litEls[i].getBoundingClientRect();
            if (rect.top < minTop) minTop = rect.top;
            if (rect.bottom > maxBottom) maxBottom = rect.bottom;
          }
          targetCenterY = minTop + (maxBottom - minTop) / 2 - cardRect.top;
        }
      }

      if (targetCenterY !== null) {
        const clamped = Math.max(28, Math.min(targetCenterY, cardRect.height - 28));
        setRailTopY(clamped);
      } else {
        setRailTopY(cardRect.height / 2);
      }
    }

    updateRailPosition();

    const resizeObserver = new ResizeObserver(() => {
      updateRailPosition();
    });
    resizeObserver.observe(card);

    window.addEventListener('resize', updateRailPosition);
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateRailPosition);
    };
  }, [selectedLineUid, litLineUids, lineViews]);

  // Deselect line when clicking outside script-card
  useEffect(() => {
    if (!selectedLineUid) return;

    function handlePointerDown(e: PointerEvent) {
      const card = cardRef.current;
      if (!card) return;
      if (e.target instanceof Node && card.contains(e.target)) {
        return;
      }
      onLineSelect(null);
    }

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [selectedLineUid, onLineSelect]);

  async function handleCopy() {
    const text = lineViews.map((r) => r.text).join('\n\n');
    await copyToClipboard(text);
    setCopied(true);
    if (copyTimer.current) window.clearTimeout(copyTimer.current);
    copyTimer.current = window.setTimeout(() => setCopied(false), 2000);
  }

  const tickPercent = Math.min(HOOK_WINDOW_SECONDS / (totalSeconds || 1), 1) * 100;

  return (
    <article className="panel script-card" ref={cardRef}>
      <VersionRail
        scope={scope}
        disabled={doc.pending}
        topOffset={railTopY}
        onStep={onStepScope}
      />

      {personaInfo && personaInfo.total > 1 && (
        <div
          className="workbench-persona-bar"
          role="navigation"
          aria-label="Buyer persona / customer segment switcher"
        >
          <button
            type="button"
            className="persona-nav-btn"
            onClick={personaInfo.onPrev}
            aria-label="Previous buyer persona"
          >
            <IconChevronLeft size={18} aria-hidden="true" />
          </button>

          <div className="persona-nav-content">
            <span className="persona-nav-kicker">
              Buyer Persona {personaInfo.current} of {personaInfo.total}
            </span>
            <span className="persona-nav-title">{personaInfo.name}</span>
          </div>

          <button
            type="button"
            className="persona-nav-btn"
            onClick={personaInfo.onNext}
            aria-label="Next buyer persona"
          >
            <IconChevronRight size={18} aria-hidden="true" />
          </button>
        </div>
      )}

      <header className="script-head">
        <div>
          <h3>
            <span>Script</span>
            {scope?.type === 'script' && (
              <span className="hint" style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                ({scope.label})
              </span>
            )}
          </h3>
          <p className="hint">
            About {Math.round(totalSeconds)} seconds spoken, {totalWords} words
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
          {timelineRows.map(({ id, kind, duration }) => (
            <span
              key={id}
              className={`tl-seg${
                litLineUids.has(id) || hoveredLineUid === id || selectedLineUid === id
                  ? ' is-on'
                  : ''
              }`}
              data-kind={kind}
              style={{ flexGrow: duration }}
            />
          ))}
        </div>
        <span className="tl-tick" style={{ left: `${tickPercent}%` }} aria-hidden="true">
          <span className="tl-tick-label">3s</span>
        </span>
      </div>

      <ol className="lines">
        {getVisibleLineItems(doc).map((item) => {
          if (item.isDeleted) {
            return (
              <LineTombstone
                key={item.node.uid}
                onUndo={() => onUndoLine(item.node.uid)}
              />
            );
          }

          const view = lineViews.find((v) => v.uid === item.node.uid);
          if (!view) return null;

          const lit = litLineUids.has(view.uid);
          const isSelected = selectedLineUid === view.uid;

          return (
            <ScriptLine
              key={view.uid}
              line={view}
              selected={isSelected}
              lit={lit}
              dim={reasonFocused && !lit && !isSelected}
              hovered={hoveredLineUid === view.uid}
              flash={recentlyChangedUids.has(view.uid)}
              canDelete={canDelete}
              onSelect={(uid) => onLineSelect(selectedLineUid === uid ? null : uid)}
              onHover={onLineHover}
              onDraft={handleDraft}
              onEdit={(uid, text) => {
                handleDraft(uid, null);
                onEditLine(uid, text);
              }}
              onRephrase={onRephraseLine}
              onRegenerate={onRegenerateLine}
              onUndo={onUndoLine}
              onRedo={onRedoLine}
              onDelete={onDeleteLine}
              onStep={(_uid, delta) => onStepScope(delta)}
            />
          );
        })}
      </ol>
    </article>
  );
}
