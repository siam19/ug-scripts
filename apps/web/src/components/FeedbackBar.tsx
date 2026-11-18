// apps/web/src/components/FeedbackBar.tsx
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { IconCheck, IconThumbDown, IconThumbUp, IconX } from '@tabler/icons-react';
import type { Script, ScriptFormat } from 'api-types';
import {
  FEEDBACK_TAG_LABELS,
  submitFeedback,
} from '../hooks/useFeedback';
import type {
  FeedbackRating,
  FeedbackTag,
  ScriptFeedbackPayload,
} from '../hooks/useFeedback';
import './FeedbackBar.css';

const NEGATIVE_TAGS: readonly FeedbackTag[] = [
  'weak_hook',
  'bland',
  'sounds_like_an_ad',
  'wrong_tone',
  'too_long',
  'unrealistic',
  'wrong_language',
];

const POSITIVE_TAGS: readonly FeedbackTag[] = [
  'great_hook',
  'wrong_tone',
  'too_long',
];

interface EntryState {
  rating: FeedbackRating | null;
  tags: FeedbackTag[];
  comment: string;
  expanded: boolean;
  saved: boolean;
  error: string | null;
}

const EMPTY_ENTRY: EntryState = {
  rating: null,
  tags: [],
  comment: '',
  expanded: false,
  saved: false,
  error: null,
};

export interface FeedbackBarProps {
  logId: string | null | undefined;
  scriptIndex: number;
  scriptSnapshot: Script;
  scriptFormat?: ScriptFormat | string;
  language?: 'en' | 'bn' | string;
  segmentName?: string;
  onFeedbackSubmitted?: (details: {
    rating: FeedbackRating;
    tags: FeedbackTag[];
    comment: string | null;
  }) => void;
  onSubmit?: (payload: ScriptFeedbackPayload) => Promise<unknown> | void;
  className?: string;
}

export function FeedbackBar({
  logId,
  scriptIndex,
  scriptSnapshot,
  scriptFormat = 'ugc',
  language = 'en',
  segmentName,
  onFeedbackSubmitted,
  onSubmit,
  className,
}: FeedbackBarProps) {
  const drawerId = useId();
  const commentId = useId();
  const [entries, setEntries] = useState<Record<string, EntryState>>({});
  const flushedPendingRef = useRef<Set<string>>(new Set());

  const pendingKey = `pending:${scriptIndex}`;
  const concreteKey = logId ? `${logId}:${scriptIndex}` : null;
  const entryKey = concreteKey ?? pendingKey;
  const entry = (concreteKey ? entries[concreteKey] : undefined) ?? entries[pendingKey] ?? EMPTY_ENTRY;

  function buildPayload(
    targetLogId: string,
    rating: FeedbackRating,
    tags: FeedbackTag[],
    commentText: string,
  ): { payload: ScriptFeedbackPayload; comment: string | null } {
    const trimmed = commentText.trim();
    const comment = trimmed ? trimmed.slice(0, 500) : null;
    return {
      comment,
      payload: {
        log_id: targetLogId,
        script_index: scriptIndex,
        rating,
        tags,
        comment,
        script_snapshot: scriptSnapshot,
        script_format: scriptFormat || 'ugc',
        language: language || 'en',
        segment_name: segmentName || scriptSnapshot.segment || 'Segment',
      },
    };
  }

  function dispatchSubmit(
    targetLogId: string,
    rating: FeedbackRating,
    tags: FeedbackTag[],
    commentText: string,
    targetKey: string,
  ) {
    const { payload, comment } = buildPayload(targetLogId, rating, tags, commentText);
    onFeedbackSubmitted?.({ rating, tags, comment });

    if (onSubmit) {
      Promise.resolve(onSubmit(payload)).catch(() => {
        setEntries((prev) => ({
          ...prev,
          [targetKey]: {
            ...(prev[targetKey] ?? EMPTY_ENTRY),
            error: 'Could not save right now',
          },
        }));
      });
      return;
    }

    void submitFeedback(payload).then((result) => {
      if (!result.ok) {
        setEntries((prev) => ({
          ...prev,
          [targetKey]: {
            ...(prev[targetKey] ?? EMPTY_ENTRY),
            error: result.error || 'Could not save feedback',
          },
        }));
      }
    });
  }

  // Keep latest dispatch callback in a ref synced via effect for pending-logId flush
  const flushSubmitRef = useRef(dispatchSubmit);
  useEffect(() => {
    flushSubmitRef.current = dispatchSubmit;
  });

  // If user rated while logId was still streaming in, flush once logId arrives
  useEffect(() => {
    if (!logId || !concreteKey) return;
    const pendingEntry = entries[pendingKey];
    if (!pendingEntry || pendingEntry.rating === null) return;
    const flushId = `${concreteKey}:${pendingEntry.rating}:${pendingEntry.tags.join(',')}:${pendingEntry.comment}`;
    if (flushedPendingRef.current.has(flushId)) return;
    flushedPendingRef.current.add(flushId);

    flushSubmitRef.current(
      logId,
      pendingEntry.rating,
      pendingEntry.tags,
      pendingEntry.comment,
      concreteKey,
    );
  }, [logId, concreteKey, pendingKey, entries]);

  function updateEntry(updater: (prev: EntryState) => EntryState) {
    setEntries((prev) => {
      const base = (concreteKey ? prev[concreteKey] : undefined) ?? prev[pendingKey] ?? EMPTY_ENTRY;
      const next = { ...prev, [entryKey]: updater(base) };
      if (concreteKey && next[pendingKey]) {
        delete next[pendingKey];
      }
      return next;
    });
  }

  function handleRate(rating: FeedbackRating) {
    const switching = entry.rating !== rating;
    const nextTags = switching
      ? entry.tags.filter((t) =>
          rating === 1 ? POSITIVE_TAGS.includes(t) : NEGATIVE_TAGS.includes(t),
        )
      : entry.tags;
    const shouldExpand = rating === -1 ? true : switching ? false : !entry.expanded;

    // Optimistic state update
    updateEntry((prev) => ({
      ...prev,
      rating,
      tags: nextTags,
      expanded: shouldExpand,
      saved: true,
      error: null,
    }));

    if (logId) {
      dispatchSubmit(logId, rating, nextTags, entry.comment, entryKey);
    }
  }

  function toggleTag(tag: FeedbackTag) {
    const exists = entry.tags.includes(tag);
    const nextTags = exists
      ? entry.tags.filter((t) => t !== tag)
      : [...entry.tags, tag];

    updateEntry((prev) => ({
      ...prev,
      tags: nextTags,
      error: null,
    }));
  }

  function handleDetailsSubmit(e: FormEvent) {
    e.preventDefault();
    if (entry.rating === null) return;

    // Optimistically collapse drawer and mark saved
    updateEntry((prev) => ({
      ...prev,
      expanded: false,
      saved: true,
      error: null,
    }));

    if (logId) {
      dispatchSubmit(logId, entry.rating, entry.tags, entry.comment, entryKey);
    }
  }

  const availableTags = entry.rating === 1 ? POSITIVE_TAGS : NEGATIVE_TAGS;

  return (
    <div
      className={`feedback-bar${className ? ` ${className}` : ''}`}
      role="region"
      aria-label="Script quality feedback"
    >
      <div className="feedback-row">
        <div className="feedback-meta">
          <span className="feedback-prompt">
            {entry.rating === null ? 'How is this script?' : 'Thanks for rating'}
          </span>

          {entry.saved && !entry.error && (
            <span className="feedback-status">
              <IconCheck size={12} aria-hidden="true" />
              <span>Saved</span>
            </span>
          )}

          {entry.error && (
            <span className="feedback-status is-error">{entry.error}</span>
          )}

          {entry.rating !== null && !entry.expanded && (
            <button
              type="button"
              className="feedback-edit-link"
              onClick={() => updateEntry((prev) => ({ ...prev, expanded: true }))}
              aria-expanded={entry.expanded}
              aria-controls={drawerId}
            >
              {entry.tags.length > 0 || entry.comment.trim()
                ? 'Edit details'
                : 'Add note'}
            </button>
          )}
        </div>

        <div className="feedback-actions">
          <button
            type="button"
            className={`feedback-thumb-btn${entry.rating === 1 ? ' is-active-up' : ''}`}
            aria-label="Thumbs up — good script"
            aria-pressed={entry.rating === 1}
            onClick={() => handleRate(1)}
          >
            <IconThumbUp size={15} aria-hidden="true" />
            <span>Good</span>
          </button>

          <button
            type="button"
            className={`feedback-thumb-btn${entry.rating === -1 ? ' is-active-down' : ''}`}
            aria-label="Thumbs down — needs work"
            aria-pressed={entry.rating === -1}
            onClick={() => handleRate(-1)}
          >
            <IconThumbDown size={15} aria-hidden="true" />
            <span>Needs work</span>
          </button>
        </div>
      </div>

      {entry.expanded && entry.rating !== null && (
        <form
          id={drawerId}
          className="feedback-drawer"
          onSubmit={handleDetailsSubmit}
        >
          <div className="feedback-drawer-head">
            <span className="feedback-drawer-title">
              {entry.rating === -1
                ? 'What felt off? (optional)'
                : 'What worked well? (optional)'}
            </span>
            <button
              type="button"
              className="feedback-close-btn"
              aria-label="Close feedback details"
              onClick={() => updateEntry((prev) => ({ ...prev, expanded: false }))}
            >
              <IconX size={15} aria-hidden="true" />
            </button>
          </div>

          <div className="feedback-tags" role="group" aria-label="Feedback tags">
            {availableTags.map((tag) => {
              const selected = entry.tags.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  className={`feedback-tag${selected ? ' is-selected' : ''}`}
                  aria-pressed={selected}
                  onClick={() => toggleTag(tag)}
                >
                  {FEEDBACK_TAG_LABELS[tag]}
                </button>
              );
            })}
          </div>

          <div className="feedback-comment-row">
            <label htmlFor={commentId} className="sr-only">
              Optional feedback note
            </label>
            <input
              id={commentId}
              type="text"
              className="feedback-comment-input"
              maxLength={500}
              value={entry.comment}
              onChange={(e) =>
                updateEntry((prev) => ({ ...prev, comment: e.target.value, error: null }))
              }
              placeholder="Optional note (up to 500 chars)..."
            />
            <button type="submit" className="feedback-submit-btn">
              Send feedback
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
