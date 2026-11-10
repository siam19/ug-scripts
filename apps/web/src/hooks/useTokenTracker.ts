// apps/web/src/hooks/useTokenTracker.ts
import { useEffect, useState } from 'react';
import type { TokenUsage } from 'api-types';

const LIFETIME_TOKENS_KEY = 'ug_lifetime_tokens';

// The API reports usage under different names depending on the provider wrapper.
const INPUT_KEYS = ['input_tokens', 'prompt_tokens', 'prompt_token_count'];
const OUTPUT_KEYS = ['output_tokens', 'candidates_tokens', 'completion_tokens', 'candidates_token_count'];

function pick(usage: unknown, keys: string[]): number {
  const record = (usage ?? {}) as Record<string, unknown>;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'number' && Number.isFinite(value)) return value;
  }
  return 0;
}

export function formatCount(tokens: number): string {
  if (tokens < 1000) return tokens.toString();
  if (tokens < 10_000) return `${(tokens / 1000).toFixed(1)}k`;
  return `${Math.round(tokens / 1000)}k`;
}

export function useTokenTracker() {
  const [sessionTokens, setSessionTokens] = useState(0);
  const [sessionInput, setSessionInput] = useState(0);
  const [sessionOutput, setSessionOutput] = useState(0);
  const [lifetimeTokens, setLifetimeTokens] = useState<number>(() => {
    try {
      const saved = localStorage.getItem(LIFETIME_TOKENS_KEY);
      return saved ? parseInt(saved, 10) : 0;
    } catch {
      return 0;
    }
  });

  useEffect(() => {
    function handleTokenUsage(e: Event) {
      const usage = (e as CustomEvent<TokenUsage | { total_tokens?: number }>).detail;
      const input = pick(usage, INPUT_KEYS);
      const output = pick(usage, OUTPUT_KEYS);
      const count = usage?.total_tokens ?? input + output;
      if (count > 0) {
        setSessionTokens((prev) => prev + count);
        setSessionInput((prev) => prev + input);
        setSessionOutput((prev) => prev + output);
        setLifetimeTokens((prev) => {
          const next = prev + count;
          try {
            localStorage.setItem(LIFETIME_TOKENS_KEY, next.toString());
          } catch {
            // Storage quota or privacy mode: ignore
          }
          return next;
        });
      }
    }

    window.addEventListener('ug:token-usage', handleTokenUsage);
    return () => window.removeEventListener('ug:token-usage', handleTokenUsage);
  }, []);

  return {
    sessionTokens,
    lifetimeTokens,
    sessionInput,
    sessionOutput,
    formattedSession: formatCount(sessionTokens),
    formattedLifetime: formatCount(lifetimeTokens),
  };
}

export type TokenTracker = ReturnType<typeof useTokenTracker>;
