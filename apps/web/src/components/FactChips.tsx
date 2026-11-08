import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent, MouseEvent } from 'react';
import { IconCheck, IconPencil, IconPlus, IconX } from '@tabler/icons-react';
import type { FactItem } from '../state/types';

const MAX_FACT = 200;

// Prevent textarea blur when clicking ✓ or ✕ buttons so the button handler fires cleanly
const keepFocus = (e: MouseEvent) => e.preventDefault();

interface EditorProps {
  initial: string;
  onSave: (text: string) => void;
  onCancel: () => void;
}

function ChipEditor({ initial, onSave, onCancel }: EditorProps) {
  const [draft, setDraft] = useState(initial);
  const ref = useRef<HTMLTextAreaElement>(null);
  const done = useRef(false);

  useEffect(() => {
    const el = ref.current;
    el?.focus();
    el?.setSelectionRange(el.value.length, el.value.length);
  }, []);

  const save = () => {
    if (done.current) return;
    done.current = true;
    onSave(draft.trim().slice(0, MAX_FACT));
  };

  const cancel = () => {
    if (done.current) return;
    done.current = true;
    onCancel();
  };

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.nativeEvent.isComposing) return; // IME composition check
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      save();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancel();
    }
  }

  return (
    <>
      <textarea
        ref={ref}
        className="chip-input"
        rows={1}
        maxLength={MAX_FACT}
        value={draft}
        aria-label="Edit fact"
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKey}
        onBlur={save}
      />
      <span className="chip-actions is-visible">
        <button type="button" aria-label="Save fact" onMouseDown={keepFocus} onClick={save}>
          <IconCheck size={14} aria-hidden="true" />
        </button>
        <button
          type="button"
          aria-label="Cancel editing"
          onMouseDown={keepFocus}
          onClick={cancel}
        >
          <IconX size={14} aria-hidden="true" />
        </button>
      </span>
    </>
  );
}

interface Props {
  facts: FactItem[];
  onEdit: (id: string, text: string) => void;
  onRemove: (id: string) => void;
  onAdd: (text: string) => void;
}

export function FactChips({ facts, onEdit, onRemove, onAdd }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  return (
    <ul className="chip-list">
      {facts.map((fact) => {
        if (editingId === fact.id) {
          return (
            <li key={fact.id} className="chip chip-fact is-editing">
              <ChipEditor
                initial={fact.text}
                onCancel={() => setEditingId(null)}
                onSave={(text) => {
                  setEditingId(null);
                  if (!text) onRemove(fact.id);
                  else if (text !== fact.text) onEdit(fact.id, text);
                }}
              />
            </li>
          );
        }

        const edited = fact.original === null || fact.text !== fact.original;
        return (
          <li
            key={fact.id}
            className={`chip chip-fact chip-animated${edited ? ' is-edited' : ''}`}
          >
            {edited && (
              <span
                className="chip-dot"
                role="img"
                aria-label="Edited by you"
                title="Edited by you"
              />
            )}
            <span
              className="chip-text"
              onDoubleClick={() => setEditingId(fact.id)}
            >
              {fact.text}
            </span>
            <span className="chip-actions">
              <button
                type="button"
                aria-label={`Edit fact: ${fact.text}`}
                onClick={() => setEditingId(fact.id)}
              >
                <IconPencil size={14} aria-hidden="true" />
              </button>
              <button
                type="button"
                aria-label={`Remove fact: ${fact.text}`}
                onClick={() => onRemove(fact.id)}
              >
                <IconX size={14} aria-hidden="true" />
              </button>
            </span>
          </li>
        );
      })}

      {adding ? (
        <li className="chip chip-fact is-editing">
          <ChipEditor
            initial=""
            onCancel={() => setAdding(false)}
            onSave={(text) => {
              setAdding(false);
              if (text) onAdd(text);
            }}
          />
        </li>
      ) : (
        <li>
          <button
            type="button"
            className="chip chip-add"
            onClick={() => setAdding(true)}
          >
            <IconPlus size={14} aria-hidden="true" />
            Add a fact
          </button>
        </li>
      )}
    </ul>
  );
}
