import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  Angle,
  Fact,
  LineKind,
  LineRegenerateResponse,
  LineRephraseResponse,
  ReasonLinesRewriteResponse,
  Script,
  ScriptFormat,
  Segment,
  SlotConfig,
  TokenUsage,
} from 'api-types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY ?? '';

function buildAuthHeaders(accept?: string): Record<string, string> {
  const accessCode = localStorage.getItem('ug_access_code') || '';
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (accept) {
    headers['Accept'] = accept;
  }
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  if (accessCode) {
    headers['X-Access-Code'] = accessCode;
  }
  return headers;
}

function dispatchTokenUsageFromHeader(res: Response): void {
  const tokenHeader = res.headers.get('X-Token-Usage');
  if (!tokenHeader) return;
  try {
    const usage = JSON.parse(tokenHeader) as TokenUsage;
    window.dispatchEvent(new CustomEvent('ug:token-usage', { detail: usage }));
  } catch {
    // Ignore parse failure
  }
}

async function buildHttpError(res: Response): Promise<Error> {
  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent('ug:unauthorized'));
  }
  let detail = '';
  try {
    const errJson = (await res.json()) as { detail?: unknown; message?: unknown };
    if (typeof errJson.detail === 'string') {
      detail = errJson.detail;
    } else if (typeof errJson.message === 'string') {
      detail = errJson.message;
    }
  } catch {
    // Ignore JSON parse failure
  }
  if (res.status === 429) {
    return new Error(
      detail || 'Slow down. Too many requests in 1 minute. Try again later.',
    );
  }
  return new Error(detail || `API request failed with status ${res.status}: ${res.statusText}`);
}

async function postJson<T>(
  endpoint: string,
  body: unknown,
  onLogId?: (logId: string) => void,
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: buildAuthHeaders(),
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(`Cannot connect to API server at ${API_URL}. Please ensure the server is running.`);
  }

  // Intercept X-Token-Usage and X-Log-Id headers
  dispatchTokenUsageFromHeader(res);
  const logIdHeader = res.headers.get('X-Log-Id');
  if (logIdHeader) {
    onLogId?.(logIdHeader);
  }

  if (!res.ok) {
    throw await buildHttpError(res);
  }
  return (await res.json()) as T;
}

export interface RegenerateMeta {
  name?: string;
  category?: string;
  market?: string;
  language?: 'en' | 'bn';
  script_format?: ScriptFormat;
  onLogId?: (logId: string) => void;
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
  angles?: Angle[];
  scriptFormat?: ScriptFormat;
}

export interface SectionSegmentsEventPayload {
  facts: (Fact | string)[];
  angles?: Angle[];
  segments: Segment[];
}

export interface RegenerateSectionStreamParams {
  facts: (Fact | string)[];
  angles?: Angle[];
  slots?: SlotConfig[];
  script_format?: ScriptFormat;
  signal?: AbortSignal;
}

export interface RegenerateSectionStreamCallbacks {
  onSegments?: (payload: SectionSegmentsEventPayload) => void;
  onScript?: (index: number, script: Script) => void;
  onDone?: (payload: { usage?: TokenUsage; logId?: string }) => void;
  onLogId?: (logId: string) => void;
  onError?: (error: Error) => void;
}

export interface RegenerateSectionStreamResult {
  segments: Segment[];
  scripts: (Script | null)[];
  usage?: TokenUsage;
  logId: string | null;
}

interface SectionSegmentsSseEvent {
  event: 'segments';
  facts: (Fact | string)[];
  angles?: Angle[];
  segments: Segment[];
}

interface SectionScriptSseEvent {
  event: 'script';
  index: number;
  script: Script;
}

interface SectionDoneSseEvent {
  event: 'done';
  usage?: TokenUsage;
  log_id?: string;
}

interface SectionErrorSseEvent {
  event: 'error';
  detail?: string;
}

type SectionSseEvent =
  | SectionSegmentsSseEvent
  | SectionScriptSseEvent
  | SectionDoneSseEvent
  | SectionErrorSseEvent;

/**
 * Regenerator hook that connects to apps/api endpoints directly,
 * throwing descriptive errors on network or HTTP failures.
 */
export function useRegenerate(metaOrLang: RegenerateMeta | ('en' | 'bn') = 'en') {
  const meta: RegenerateMeta =
    typeof metaOrLang === 'string' ? { language: metaOrLang } : metaOrLang;
  const language = meta.language ?? 'en';
  const [logId, setLogId] = useState<string | null>(null);
  const onLogIdRef = useRef(meta.onLogId);
  useEffect(() => {
    onLogIdRef.current = meta.onLogId;
  }, [meta.onLogId]);

  const handleLogId = useCallback((nextLogId: string) => {
    setLogId(nextLogId);
    onLogIdRef.current?.(nextLogId);
  }, []);

  const regenerateSegment = useCallback(
    async (current: Segment, others: Segment[], facts: string[]): Promise<Segment> => {
      return postJson<Segment>(
        '/regenerate/segment',
        {
          name: meta.name || 'Product',
          category: meta.category || 'General',
          market: meta.market || 'Bangladesh',
          language,
          facts: facts.length > 0 ? facts : ['Verified product facts'],
          current_segment: current,
          existing_segment_names: others.map((o) => o.name),
        },
        handleLogId,
      );
    },
    [handleLogId, language, meta.category, meta.market, meta.name],
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

      const res = await postJson<ReasonLinesRewriteResponse>(
        '/regenerate/reason-lines',
        {
          name: meta.name || 'Product',
          market: meta.market || 'Bangladesh',
          language,
          facts,
          segment,
          full_script: fullScript,
          target_line_ids: targetLineIds,
          reason: { title, why },
        },
        handleLogId,
      );

      return res.lines.map((l) => ({ kind: l.kind, text: l.text }));
    },
    [handleLogId, language, meta.market, meta.name],
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

      return postJson<LineRephraseResponse>(
        '/regenerate/line/rephrase',
        {
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
        },
        handleLogId,
      );
    },
    [handleLogId, language, meta.market, meta.name],
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

      const res = await postJson<LineRegenerateResponse>(
        '/regenerate/line/regenerate',
        {
          name: meta.name || 'Product',
          market: meta.market || 'Bangladesh',
          language,
          facts,
          segment,
          script_context: scriptContext,
          line_id: lineId,
          current_text: currentText,
          kind,
        },
        handleLogId,
      );
      return res.text;
    },
    [handleLogId, language, meta.market, meta.name],
  );

  const rewriteScript = useCallback(
    async (
      segment: Segment,
      facts: string[],
      options?: RewriteScriptOptions,
    ): Promise<Script> => {
      return postJson<Script>(
        '/regenerate/script',
        {
          name: meta.name || 'Product',
          category: meta.category || 'General',
          market: meta.market || 'Bangladesh',
          language,
          facts: facts.length > 0 ? facts : ['Verified product facts'],
          angles: options?.angles ?? [],
          segment,
          hook_style: options?.hookStyle ?? null,
          script_format: options?.scriptFormat ?? meta.script_format ?? 'ugc',
        },
        handleLogId,
      );
    },
    [handleLogId, language, meta.category, meta.market, meta.name, meta.script_format],
  );

  const regenerateSectionStream = useCallback(
    async (
      params: RegenerateSectionStreamParams,
      callbacks?: RegenerateSectionStreamCallbacks,
    ): Promise<RegenerateSectionStreamResult> => {
      const requestBody = {
        name: meta.name || 'Product',
        category: meta.category || 'General',
        market: meta.market || 'Bangladesh',
        language,
        facts: params.facts.length > 0 ? params.facts : ['Verified product facts'],
        angles: params.angles ?? [],
        script_format: params.script_format ?? meta.script_format ?? 'ugc',
        slots: params.slots ?? [],
      };

      let res: Response;
      try {
        res = await fetch(`${API_URL}/regenerate/section`, {
          method: 'POST',
          headers: buildAuthHeaders('text/event-stream'),
          body: JSON.stringify(requestBody),
          signal: params.signal,
        });
      } catch (err) {
        const netErr =
          err instanceof DOMException && err.name === 'AbortError'
            ? err
            : new Error(`Cannot connect to API server at ${API_URL}. Please ensure the server is running.`);
        if (netErr instanceof Error) callbacks?.onError?.(netErr);
        throw netErr;
      }

      dispatchTokenUsageFromHeader(res);
      let resolvedLogId: string | null = res.headers.get('X-Log-Id');
      if (resolvedLogId) {
        handleLogId(resolvedLogId);
        callbacks?.onLogId?.(resolvedLogId);
      }

      if (!res.ok) {
        const httpErr = await buildHttpError(res);
        callbacks?.onError?.(httpErr);
        throw httpErr;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        const err = new Error('Section regeneration stream was empty.');
        callbacks?.onError?.(err);
        throw err;
      }

      let segments: Segment[] = [];
      let scripts: (Script | null)[] = [];
      let usage: TokenUsage | undefined;
      let gotDone = false;

      const decoder = new TextDecoder();
      let buffer = '';

      const processPart = (part: string) => {
        const lines = part.split(/\r?\n/);
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;
          const payload = JSON.parse(jsonStr) as SectionSseEvent;

          if (payload.event === 'segments') {
            segments = payload.segments;
            scripts = new Array<Script | null>(payload.segments.length).fill(null);
            callbacks?.onSegments?.({
              facts: payload.facts,
              angles: payload.angles,
              segments: payload.segments,
            });
          } else if (payload.event === 'script') {
            scripts[payload.index] = payload.script;
            callbacks?.onScript?.(payload.index, payload.script);
          } else if (payload.event === 'done') {
            gotDone = true;
            usage = payload.usage;
            if (payload.usage) {
              window.dispatchEvent(
                new CustomEvent('ug:token-usage', { detail: payload.usage }),
              );
            }
            if (payload.log_id) {
              resolvedLogId = payload.log_id;
              handleLogId(payload.log_id);
              callbacks?.onLogId?.(payload.log_id);
            }
            callbacks?.onDone?.({
              usage: payload.usage,
              logId: resolvedLogId ?? undefined,
            });
          } else if (payload.event === 'error') {
            throw new Error(payload.detail || 'Section regeneration failed.');
          }
        }
      };

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split(/\r?\n\r?\n/);
          buffer = parts.pop() ?? '';

          for (const part of parts) {
            processPart(part);
          }
        }

        const tail = buffer + decoder.decode();
        if (tail.trim()) {
          processPart(tail);
        }

        if (!gotDone) {
          throw new Error('Section regeneration stream ended before completion.');
        }

        return { segments, scripts, usage, logId: resolvedLogId };
      } catch (err) {
        const errorObj = err instanceof Error ? err : new Error('Section regeneration failed.');
        callbacks?.onError?.(errorObj);
        throw errorObj;
      }
    },
    [handleLogId, language, meta.category, meta.market, meta.name, meta.script_format],
  );

  return {
    logId,
    regenerateSegment,
    rewriteReasonLines,
    rephraseLine,
    regenerateLine,
    rewriteScript,
    regenerateSectionStream,
  };
}
