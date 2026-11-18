// apps/web/src/state/pricing.ts

/**
 * Centralized Gemini Flash token pricing estimates & USD->BDT conversion.
 * These are approximate client-side estimates for display in the masthead meter;
 * actual Google Cloud / Vertex AI billing depends on SKU, caching, and FX rates.
 */
export const GEMINI_FLASH_INPUT_USD_PER_1M = 0.15;
export const GEMINI_FLASH_OUTPUT_USD_PER_1M = 0.6;
/** Fallback blended rate (~70% input / 30% output) when only total tokens are available. */
export const GEMINI_FLASH_BLENDED_USD_PER_1M = 0.285;
/** Approximate BDT per 1 USD exchange rate for rough cost visibility. */
export const USD_TO_BDT = 122;

function safeTokens(value: number | undefined): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 0;
}

/**
 * Estimates USD cost from input/output token counts, with a safe fallback to
 * total tokens (or any unattributed remainder) using the blended Flash rate.
 */
export function estimateCostUsd(input: number, output: number, total?: number): number {
  const safeIn = safeTokens(input);
  const safeOut = safeTokens(output);
  const safeTotal = safeTokens(total);

  if (safeIn > 0 || safeOut > 0) {
    const splitCost =
      (safeIn / 1_000_000) * GEMINI_FLASH_INPUT_USD_PER_1M +
      (safeOut / 1_000_000) * GEMINI_FLASH_OUTPUT_USD_PER_1M;
    const unattributed = Math.max(0, safeTotal - (safeIn + safeOut));
    const remainderCost = (unattributed / 1_000_000) * GEMINI_FLASH_BLENDED_USD_PER_1M;
    return splitCost + remainderCost;
  }

  if (safeTotal > 0) {
    return (safeTotal / 1_000_000) * GEMINI_FLASH_BLENDED_USD_PER_1M;
  }

  return 0;
}

export function usdToBdt(usd: number): number {
  if (!Number.isFinite(usd) || usd <= 0) return 0;
  return usd * USD_TO_BDT;
}

export function estimateCostBdt(input: number, output: number, total?: number): number {
  return usdToBdt(estimateCostUsd(input, output, total));
}

export function formatBdt(bdt: number): string {
  if (!Number.isFinite(bdt) || bdt <= 0) return '৳0.00';
  if (bdt < 0.01) return '<৳0.01';
  if (bdt < 100) return `৳${bdt.toFixed(2)}`;
  if (bdt < 1000) return `৳${bdt.toFixed(1)}`;
  return `৳${Math.round(bdt).toLocaleString('en-US')}`;
}

export function formatUsd(usd: number): string {
  if (!Number.isFinite(usd) || usd <= 0) return '$0.00';
  if (usd < 0.0001) return '<$0.0001';
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  if (usd < 1) return `$${usd.toFixed(3)}`;
  return `$${usd.toFixed(2)}`;
}
