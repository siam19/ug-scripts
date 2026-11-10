import { useCallback } from 'react';
import type {
  LineKind,
  LineRegenerateResponse,
  LineRephraseResponse,
  ReasonLinesRewriteResponse,
  Script,
  Segment,
} from 'api-types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY ?? '';

async function postJson<T>(endpoint: string, body: unknown): Promise<T> {
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
  let res: Response;
  try {
    res = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(`Cannot connect to API server at ${API_URL}. Please ensure the server is running.`);
  }

  // Intercept X-Token-Usage header to update masthead usage meter
  const tokenHeader = res.headers.get('X-Token-Usage');
  if (tokenHeader) {
    try {
      const usage = JSON.parse(tokenHeader);
      window.dispatchEvent(new CustomEvent('ug:token-usage', { detail: usage }));
    } catch {
      // Ignore parse failure
    }
  }

  if (!res.ok) {
    if (res.status === 401) {
      window.dispatchEvent(new CustomEvent('ug:unauthorized'));
    }
    let detail = '';
    try {
      const errJson = await res.json();
      detail = errJson.detail || errJson.message || '';
    } catch {
      // Ignore JSON parse failure
    }
    if (res.status === 429) {
      throw new Error(
        detail || 'Slow down. Too many requests in 1 minute. Try again later.',
      );
    }
    throw new Error(detail || `API request failed with status ${res.status}: ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export interface RegenerateMeta {
  name?: string;
  category?: string;
  market?: string;
  language?: 'en' | 'bn';
}

export interface RewriteReasonLinesOptions {
  segment?: Segment;
  facts?: string[];
  fullScript?: { id: number; kind: LineKind; text: string }[];
  targetLineIds?: number[];
}

export interface RephraseLineOptions {
  segment?: Segment;
  facts?: string[];
  scriptContext?: { id: number; kind: LineKind; text: string }[];
  lineId?: number;
  avoidTones?: string[];
}

export interface RegenerateLineOptions {
  segment?: Segment;
  facts?: string[];
  scriptContext?: { id: number; kind: LineKind; text: string }[];
  lineId?: number;
}

export interface RewriteScriptOptions {
  hookStyle?: string | null;
}

/**
 * Regenerator hook that connects to apps/api endpoints directly,
 * throwing descriptive errors on network or HTTP failures.
 */
export function useRegenerate(metaOrLang: RegenerateMeta | ('en' | 'bn') = 'en') {
  const meta: RegenerateMeta =
    typeof metaOrLang === 'string' ? { language: metaOrLang } : metaOrLang;
  const language = meta.language ?? 'en';

  const regenerateSegment = useCallback(
    async (current: Segment, others: Segment[], facts: string[]): Promise<Segment> => {
      return postJson<Segment>('/regenerate/segment', {
        name: meta.name || 'Product',
        category: meta.category || 'General',
        market: meta.market || 'Bangladesh',
        language,
        facts: facts.length > 0 ? facts : ['Verified product facts'],
        current_segment: current,
        existing_segment_names: others.map((o) => o.name),
      });
    },
    [language, meta.category, meta.market, meta.name],
  );

  const rewriteReasonLines = useCallback(
    async (
      title: string,
      why: string,
      currentLines: { kind: LineKind; text: string }[],
      options?: RewriteReasonLinesOptions,
    ): Promise<{ kind: LineKind; text: string }[]> => {
      const fullScript =
        options?.fullScript ??
        currentLines.map((l, idx) => ({
          id: idx + 1,
          kind: l.kind,
          text: l.text,
        }));
      const targetLineIds =
        options?.targetLineIds ?? currentLines.map((_, idx) => idx + 1);
      const facts =
        options?.facts && options.facts.length > 0
          ? options.facts
          : ['Verified product facts'];
      const segment = options?.segment ?? {
        name: 'Active Target Segment',
        who: 'Target audience',
        pain_point: 'Current pain point',
        platforms: ['TikTok', 'Reels'],
      };

      const res = await postJson<ReasonLinesRewriteResponse>('/regenerate/reason-lines', {
        name: meta.name || 'Product',
        market: meta.market || 'Bangladesh',
        language,
        facts,
        segment,
        full_script: fullScript,
        target_line_ids: targetLineIds,
        reason: { title, why },
      });

      return res.lines.map((l) => ({ kind: l.kind, text: l.text }));
    },
    [language, meta.market, meta.name],
  );

  const rephraseLine = useCallback(
    async (
      currentText: string,
      kind: LineKind,
      options?: RephraseLineOptions,
    ): Promise<{ text: string; tone: string }> => {
      const scriptContext =
        options?.scriptContext ?? [{ id: 1, kind, text: currentText }];
      const lineId = options?.lineId ?? 1;
      const facts =
        options?.facts && options.facts.length > 0
          ? options.facts
          : ['Verified product facts'];
      const segment = options?.segment ?? {
        name: 'Target Segment',
        who: 'Target audience',
        pain_point: 'Pain point',
        platforms: ['TikTok'],
      };
      const avoidTones = options?.avoidTones ?? [];

      return postJson<LineRephraseResponse>('/regenerate/line/rephrase', {
        name: meta.name || 'Product',
        market: meta.market || 'Bangladesh',
        language,
        facts,
        segment,
        script_context: scriptContext,
        line_id: lineId,
        current_text: currentText,
        kind,
        avoid_tones: avoidTones,
      });
    },
    [language, meta.market, meta.name],
  );

  const regenerateLine = useCallback(
    async (
      currentText: string,
      kind: LineKind,
      options?: RegenerateLineOptions,
    ): Promise<string> => {
      const scriptContext =
        options?.scriptContext ?? [{ id: 1, kind, text: currentText }];
      const lineId = options?.lineId ?? 1;
      const facts =
        options?.facts && options.facts.length > 0
          ? options.facts
          : ['Verified product facts'];
      const segment = options?.segment ?? {
        name: 'Target Segment',
        who: 'Target audience',
        pain_point: 'Pain point',
        platforms: ['TikTok'],
      };

      const res = await postJson<LineRegenerateResponse>('/regenerate/line/regenerate', {
        name: meta.name || 'Product',
        market: meta.market || 'Bangladesh',
        language,
        facts,
        segment,
        script_context: scriptContext,
        line_id: lineId,
        current_text: currentText,
        kind,
      });
      return res.text;
    },
    [language, meta.market, meta.name],
  );

  const rewriteScript = useCallback(
    async (
      segment: Segment,
      facts: string[],
      options?: RewriteScriptOptions,
    ): Promise<Script> => {
      return postJson<Script>('/regenerate/script', {
        name: meta.name || 'Product',
        category: meta.category || 'General',
        market: meta.market || 'Bangladesh',
        language,
        facts: facts.length > 0 ? facts : ['Verified product facts'],
        segment,
        hook_style: options?.hookStyle ?? null,
      });
    },
    [language, meta.category, meta.market, meta.name],
  );

  return {
    regenerateSegment,
    rewriteReasonLines,
    rephraseLine,
    regenerateLine,
    rewriteScript,
  };
}
