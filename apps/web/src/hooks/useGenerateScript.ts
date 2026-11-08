// apps/web/src/hooks/useGenerateScript.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import type { GenerateResponse } from 'api-types';
import type { FormValues } from '../types/form';

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_KEY: string = import.meta.env.VITE_API_KEY ?? '';
const TIMEOUT_MS = 90_000;

export type Status = 'idle' | 'loading' | 'success' | 'error';

export interface FriendlyError {
  title: string;
  message: string;
}

const TIMEOUT_ERROR: FriendlyError = {
  title: 'This took too long',
  message:
    'The server did not answer within 90 seconds. Try again; if it keeps happening, the AI service may be busy.',
};

const NETWORK_ERROR: FriendlyError = {
  title: "Can't reach the server",
  message:
    'Check your connection and that the API is running, then try again.',
};

const BAD_RESPONSE_ERROR: FriendlyError = {
  title: 'Unexpected response',
  message: 'The server replied, but the result was incomplete. Try again.',
};

function errorForStatus(status: number, detail?: string): FriendlyError {
  switch (status) {
    case 401:
      return {
        title: 'API key rejected',
        message:
          'The server did not accept the API key. Check VITE_API_KEY in apps/web/.env.local and restart the dev server.',
      };
    case 413:
      return {
        title: 'Image is too large',
        message: 'The photo must be 5 MB or smaller. Choose a smaller image or compress it.',
      };
    case 415:
      return {
        title: 'Unsupported image type',
        message: 'Use a JPEG, PNG or WebP photo.',
      };
    case 422:
      return {
        title: 'Some details need fixing',
        message:
          'Check that the name, category, description and market are filled in, and that the market is 60 characters or fewer.' +
          (detail ? ` Server says: ${detail}` : ''),
      };
    case 502:
    case 503:
    case 504:
      return {
        title: 'The AI service did not respond',
        message: 'The script generator timed out or is temporarily unavailable. Try again in a moment.',
      };
    default:
      return {
        title: 'Something went wrong',
        message: detail ?? `The server responded with status ${status}. Try again.`,
      };
  }
}

function isGenerateResponse(value: unknown): value is GenerateResponse {
  const v = value as Partial<GenerateResponse> | null;
  return (
    !!v &&
    Array.isArray(v.facts) &&
    Array.isArray(v.segments) &&
    Array.isArray(v.scripts) &&
    v.segments.length > 0 &&
    v.scripts.length > 0
  );
}

export function useGenerateScript() {
  const [status, setStatus] = useState<Status>('idle');
  const [data, setData] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<FriendlyError | null>(null);
  const [runId, setRunId] = useState(0);

  const lastValues = useRef<FormValues | null>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  const generate = useCallback(async (values: FormValues) => {
    if (!values.image) return;

    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;

    let timedOut = false;
    const timer = window.setTimeout(() => {
      timedOut = true;
      ctrl.abort();
    }, TIMEOUT_MS);

    lastValues.current = values;
    setStatus('loading');
    setError(null);
    setData(null);

    // Let the browser set the multipart boundary: do not set Content-Type.
    const body = new FormData();
    body.append('name', values.name.trim());
    body.append('description', values.description.trim());
    body.append('category', values.category.trim());
    body.append('market', values.market.trim());
    body.append('language', values.language);
    body.append('image', values.image);

    try {
      const res = await fetch(`${API_URL}/generate`, {
        method: 'POST',
        headers: { 'X-API-Key': API_KEY },
        body,
        signal: ctrl.signal,
      });

      if (!res.ok) {
        const detail = await res
          .json()
          .then((j: { detail?: unknown }) => (typeof j.detail === 'string' ? j.detail : undefined))
          .catch(() => undefined);
        setError(errorForStatus(res.status, detail));
        setStatus('error');
        return;
      }

      const json: unknown = await res.json();
      if (!isGenerateResponse(json)) {
        setError(BAD_RESPONSE_ERROR);
        setStatus('error');
        return;
      }

      setData(json);
      setRunId((n) => n + 1);
      setStatus('success');
    } catch {
      // Aborted because a newer request replaced this one (or on unmount): stay quiet.
      if (ctrl.signal.aborted && !timedOut) return;
      setError(timedOut ? TIMEOUT_ERROR : NETWORK_ERROR);
      setStatus('error');
    } finally {
      window.clearTimeout(timer);
    }
  }, []);

  const retry = useCallback(() => {
    if (lastValues.current) void generate(lastValues.current);
  }, [generate]);

  const clearError = useCallback(() => {
    setError(null);
    setStatus((s) => (s === 'error' ? 'idle' : s));
  }, []);

  return { status, data, error, runId, generate, retry, clearError };
}
