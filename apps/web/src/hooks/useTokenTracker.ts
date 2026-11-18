// apps/web/src/hooks/useTokenTracker.ts
import { useEffect, useState } from 'react';
import type { TokenUsage } from 'api-types';
import { estimateCostUsd, formatBdt, formatUsd, usdToBdt } from '../state/pricing';

const LIFETIME_TOKENS_KEY = 'ug_lifetime_tokens';
const LIFETIME_INPUT_KEY = 'ug_lifetime_input_tokens';
const LIFETIME_OUTPUT_KEY = 'ug_lifetime_output_tokens';

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

function readStoredCount(key: string): number {
  try {
    const saved = localStorage.getItem(key);
    const parsed = saved ? parseInt(saved, 10) : 0;
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  } catch {
    return 0;
  }
}

function writeStoredCount(key: string, value: number) {
  try {
    localStorage.setItem(key, value.toString());
  } catch {
    // Storage quota or privacy mode: ignore
  }
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
  const [lifetimeTokens, setLifetimeTokens] = useState<number>(() => readStoredCount(LIFETIME_TOKENS_KEY));
  const [lifetimeInput, setLifetimeInput] = useState<number>(() => readStoredCount(LIFETIME_INPUT_KEY));
  const [lifetimeOutput, setLifetimeOutput] = useState<number>(() => readStoredCount(LIFETIME_OUTPUT_KEY));

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
          writeStoredCount(LIFETIME_TOKENS_KEY, next);
          return next;
        });
        if (input > 0) {
          setLifetimeInput((prev) => {
            const next = prev + input;
            writeStoredCount(LIFETIME_INPUT_KEY, next);
            return next;
          });
        }
        if (output > 0) {
          setLifetimeOutput((prev) => {
            const next = prev + output;
            writeStoredCount(LIFETIME_OUTPUT_KEY, next);
            return next;
          });
        }
      }
    }

    window.addEventListener('ug:token-usage', handleTokenUsage);
    return () => window.removeEventListener('ug:token-usage', handleTokenUsage);
  }, []);

  const sessionCostUsd = estimateCostUsd(sessionInput, sessionOutput, sessionTokens);
  const sessionCostBdt = usdToBdt(sessionCostUsd);
  const lifetimeCostUsd = estimateCostUsd(lifetimeInput, lifetimeOutput, lifetimeTokens);
  const lifetimeCostBdt = usdToBdt(lifetimeCostUsd);

  return {
    sessionTokens,
    lifetimeTokens,
    sessionInput,
    sessionOutput,
    lifetimeInput,
    lifetimeOutput,
    sessionCostUsd,
    sessionCostBdt,
    lifetimeCostUsd,
    lifetimeCostBdt,
    formattedSession: formatCount(sessionTokens),
    formattedLifetime: formatCount(lifetimeTokens),
    formattedSessionBdt: formatBdt(sessionCostBdt),
    formattedSessionUsd: formatUsd(sessionCostUsd),
    formattedLifetimeBdt: formatBdt(lifetimeCostBdt),
    formattedLifetimeUsd: formatUsd(lifetimeCostUsd),
  };
}

export type TokenTracker = ReturnType<typeof useTokenTracker>;
