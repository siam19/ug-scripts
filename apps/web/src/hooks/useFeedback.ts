import { useCallback } from 'react';
import type { Script } from 'api-types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY ?? '';

export const FEEDBACK_TAGS = [
  'bland',
  'sounds_like_an_ad',
  'wrong_tone',
  'too_long',
  'weak_hook',
  'unrealistic',
  'wrong_language',
  'great_hook',
] as const;

export type FeedbackTag = (typeof FEEDBACK_TAGS)[number];

export const FEEDBACK_TAG_LABELS: Record<FeedbackTag, string> = {
  bland: 'Bland',
  sounds_like_an_ad: 'Sounds like an ad',
  wrong_tone: 'Wrong tone',
  too_long: 'Too long',
  weak_hook: 'Weak hook',
  unrealistic: 'Unrealistic',
  wrong_language: 'Wrong language',
  great_hook: 'Great hook',
};

export type FeedbackRating = -1 | 1;
export type FeedbackSignal = 'copy' | 'save' | 'regenerate';

export interface ScriptFeedbackPayload {
  log_id: string;
  script_index: number;
  rating: FeedbackRating;
  tags?: FeedbackTag[];
  comment?: string | null;
  script_snapshot: Script;
  script_format: string;
  language: string;
  segment_name: string;
}

export interface ScriptFeedbackResponse {
  success: boolean;
  feedback_id?: string;
  stored?: boolean;
  [key: string]: unknown;
}

export interface FeedbackSubmitResult {
  ok: boolean;
  data?: ScriptFeedbackResponse;
  error?: string;
}

export interface ScriptSignalPayload {
  log_id: string;
  script_index: number;
  signal: FeedbackSignal;
}

const VALID_TAG_SET = new Set<string>(FEEDBACK_TAGS);

function buildAuthHeaders(): Record<string, string> {
  const accessCode = localStorage.getItem('ug_access_code') || '';
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  if (accessCode) {
    headers['X-Access-Code'] = accessCode;
  }
  return headers;
}

function sanitizeTags(tags?: readonly FeedbackTag[]): FeedbackTag[] {
  if (!tags || tags.length === 0) return [];
  const seen = new Set<FeedbackTag>();
  for (const tag of tags) {
    if (VALID_TAG_SET.has(tag)) {
      seen.add(tag);
    }
  }
  return Array.from(seen);
}

function sanitizeComment(comment?: string | null): string | null {
  if (!comment) return null;
  const trimmed = comment.trim();
  if (!trimmed) return null;
  return trimmed.slice(0, 500);
}

/**
 * Non-blocking feedback submission helper for POST /feedback.
 * Never throws; returns a structured { ok, data, error } outcome so UI remains responsive.
 */
export async function submitFeedback(
  payload: ScriptFeedbackPayload,
): Promise<FeedbackSubmitResult> {
  if (!payload.log_id) {
    return { ok: false, error: 'Missing log_id' };
  }

  const body = {
    log_id: payload.log_id,
    script_index: payload.script_index,
    rating: payload.rating,
    tags: sanitizeTags(payload.tags),
    comment: sanitizeComment(payload.comment),
    script_snapshot: payload.script_snapshot,
    script_format: payload.script_format || 'ugc',
    language: payload.language || 'en',
    segment_name: payload.segment_name || payload.script_snapshot.segment || 'Segment',
  };

  try {
    const res = await fetch(`${API_URL}/feedback`, {
      method: 'POST',
      headers: buildAuthHeaders(),
      body: JSON.stringify(body),
      keepalive: true,
    });

    if (!res.ok) {
      if (res.status === 401) {
        window.dispatchEvent(new CustomEvent('ug:unauthorized'));
      }
      let detail = `HTTP ${res.status}`;
      try {
        const errJson = (await res.json()) as { detail?: unknown; message?: unknown };
        if (typeof errJson.detail === 'string') detail = errJson.detail;
        else if (typeof errJson.message === 'string') detail = errJson.message;
      } catch {
        // Ignore parse failure
      }
      return { ok: false, error: detail };
    }

    const data = (await res.json().catch(() => ({ success: true }))) as ScriptFeedbackResponse;
    return { ok: true, data };
  } catch {
    return { ok: false, error: 'Network error while sending feedback' };
  }
}

/**
 * Fire-and-forget implicit quality signal helper for POST /feedback/signal.
 * Never throws or blocks user interactions (copy, save, regenerate).
 */
export async function sendFeedbackSignal(payload: ScriptSignalPayload): Promise<void> {
  if (!payload.log_id) return;

  try {
    const res = await fetch(`${API_URL}/feedback/signal`, {
      method: 'POST',
      headers: buildAuthHeaders(),
      body: JSON.stringify({
        log_id: payload.log_id,
        script_index: payload.script_index,
        signal: payload.signal,
      }),
      keepalive: true,
    });

    if (res.status === 401) {
      window.dispatchEvent(new CustomEvent('ug:unauthorized'));
    }
  } catch {
    // Implicit signals are strictly non-blocking
  }
}

/**
 * Convenience React hook returning stable feedback submission and signal helpers.
 */
export function useFeedback() {
  const submit = useCallback(
    (payload: ScriptFeedbackPayload) => submitFeedback(payload),
    [],
  );
  const sendSignal = useCallback(
    (payload: ScriptSignalPayload) => sendFeedbackSignal(payload),
    [],
  );

  return {
    submitFeedback: submit,
    sendFeedbackSignal: sendSignal,
  };
}
