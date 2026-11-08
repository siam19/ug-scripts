import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { LineKind } from 'api-types';
import { IconArrowBackUp, IconCheck, IconX } from '@tabler/icons-react';
import { LineToolbar } from './LineToolbar';
import type { LinePending } from './LineToolbar';
import { MOD } from '../state/keyboard';
import { ScopeBadge } from './VersionRail';
import type { ScopeVersion } from './VersionRail';

const KIND_LABEL: Record<LineKind, string> = {
  hook: 'Hook',
  concept: 'Concept',
  cta: 'Call to action',
};

/**
 * View model derived by ScriptCard from the workspace state tree.
 */
export interface LineView {
  uid: string;
  kind: LineKind;
  text: string;
  no: number; // 1-based display number derived from position
  time: string; // e.g. "0:12"
  version: ScopeVersion;
  canUndo: boolean;
  canRedo: boolean;
  undoHint?: string;
  pending?: LinePending;
}

interface Props {
  line: LineView;
  selected: boolean;
  lit: boolean; // lit by hovered/pinned reason
  dim: boolean; // a reason is focused and this line is not part of it
  hovered: boolean;
  flash: boolean; // recently updated/replaced
  canDelete: boolean;
  onSelect: (uid: string) => void;
  onHover: (uid: string | null) => void;
  onDraft?: (uid: string, text: string | null) => void; // live timeline while typing
  onEdit: (uid: string, text: string) => void;
  onRephrase: (uid: string) => void;
  onRegenerate: (uid: string) => void;
  onUndo: (uid: string) => void;
  onRedo: (uid: string) => void;
  onDelete: (uid: string) => void;
  onStep: (uid: string, delta: -1 | 1) => void;
}

export function ScriptLine(p: Props) {
  const { line, selected } = p;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(line.text);
  const area = useRef<HTMLTextAreaElement>(null);

  // Ensure editing cancels when line is deselected externally (e.g. ESC or other selection)
  useEffect(() => {
    if (!selected && editing) {
      // oxlint-disable-next-line react/set-state-in-effect
      setEditing(false);
      p.onDraft?.(line.uid, null);
    }
  }, [selected, editing, line.uid, p]);

  // Robust cursor placement inside ln-body text when edit mode starts
  useLayoutEffect(() => {
    if (!editing) return;
    const el = area.current;
    if (!el) return;
    el.focus();
    const len = el.value.length;
    el.setSelectionRange(len, len);

    const raf = requestAnimationFrame(() => {
      if (area.current) {
        area.current.focus();
        const l = area.current.value.length;
        area.current.setSelectionRange(l, l);
      }
    });
    return () => cancelAnimationFrame(raf);
  }, [editing]);

  // Auto-grow textarea to occupy the exact paragraph height
  useLayoutEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [draft, editing]);

  function startEdit() {
    setDraft(line.text);
    setEditing(true);
  }

  function finishEdit(save: boolean) {
    const next = draft.trim();
    if (save && next && next !== line.text) {
      p.onEdit(line.uid, next);
    }
    setEditing(false);
    p.onDraft?.(line.uid, null);
  }

  function handleDraft(value: string) {
    setDraft(value);
    p.onDraft?.(line.uid, value);
  }

  function handleAreaKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.nativeEvent.isComposing) return; // Bangla / IME composition
    if (e.key === 'Escape') {
      e.preventDefault();
      finishEdit(false);
    } else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      finishEdit(true);
    }
  }

  function handleHitClick() {
    if (window.getSelection()?.toString()) return; // User is selecting text to copy
    p.onSelect(line.uid);
  }

  function handleHitKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      p.onSelect(line.uid);
    }
  }

  // ⌘Z / ⇧⌘Z while focus is inside this line
  function handleLineKey(e: KeyboardEvent<HTMLLIElement>) {
    if (!selected || editing) return;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') {
      e.preventDefault();
      if (e.shiftKey) {
        if (line.canRedo) p.onRedo(line.uid);
      } else if (line.canUndo) {
        p.onUndo(line.uid);
      }
    }
  }

  const cls = [
    'line',
    selected && 'is-selected',
    p.lit && 'is-lit',
    p.dim && 'is-dim',
    p.hovered && 'is-hover',
    p.flash && 'is-flash',
    line.pending && 'is-pending',
  ]
    .filter(Boolean)
    .join(' ');

  // While editing, the hit area must not be a button (preventing button-in-button nesting)
  const hitProps = editing
    ? {}
    : {
        role: 'button' as const,
        tabIndex: 0,
        'aria-pressed': selected,
        onClick: handleHitClick,
        onKeyDown: handleHitKey,
      };

  return (
    <li
      className={cls}
      data-kind={line.kind}
      data-line-uid={line.uid}
      onMouseEnter={() => !editing && p.onHover(line.uid)}
      onMouseLeave={() => p.onHover(null)}
      onKeyDown={handleLineKey}
    >
      <div className="line-hit" {...hitProps}>
        <div className="ln-gutter">
          <span className="ln-id">{line.no}</span>
          <span className="ln-time">{line.time}</span>
        </div>
        <div className="ln-body">
          <span className="kind">
            {line.pending ? 'Rewriting…' : KIND_LABEL[line.kind] ?? line.kind}
          </span>
          {editing ? (
            <textarea
              ref={area}
              className="ln-edit"
              rows={1}
              value={draft}
              autoFocus
              aria-label={`Edit line ${line.no}`}
              onChange={(e) => handleDraft(e.target.value)}
              onKeyDown={handleAreaKey}
            />
          ) : (
            <p className="ln-text">{line.text}</p>
          )}
        </div>
      </div>

      {line.pending && <span className="ln-progress" aria-hidden="true" />}

      {selected && !editing && (
        <>
          <ScopeBadge
            scope={line.version}
            disabled={Boolean(line.pending)}
            onStep={(d) => p.onStep(line.uid, d)}
          />
          <LineToolbar
            pending={line.pending}
            canUndo={line.canUndo}
            canRedo={line.canRedo}
            canDelete={p.canDelete}
            undoHint={line.undoHint}
            onEdit={startEdit}
            onRephrase={() => p.onRephrase(line.uid)}
            onRegenerate={() => p.onRegenerate(line.uid)}
            onUndo={() => p.onUndo(line.uid)}
            onRedo={() => p.onRedo(line.uid)}
            onDelete={() => p.onDelete(line.uid)}
          />
        </>
      )}

      {editing && (
        <div className="line-toolbar line-editbar" role="group" aria-label="Editing line">
          <span className="tb-hint">{MOD}↵ save · Esc cancel</span>
          <button type="button" className="tb-btn" onClick={() => finishEdit(false)}>
            <IconX size={16} aria-hidden="true" />
            <span>Cancel</span>
          </button>
          <button
            type="button"
            className="tb-btn is-primary"
            onClick={() => finishEdit(true)}
          >
            <IconCheck size={16} aria-hidden="true" />
            <span>Save</span>
          </button>
        </div>
      )}
    </li>
  );
}

/**
 * Tombstone for deleted line: stays until restored via Undo.
 */
export function LineTombstone({ onUndo }: { onUndo: () => void }) {
  return (
    <li className="line-tombstone">
      <span>Line deleted</span>
      <button type="button" className="link-btn" onClick={onUndo}>
        <IconArrowBackUp size={14} aria-hidden="true" />
        Undo
      </button>
    </li>
  );
}
