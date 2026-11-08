import type { Uid } from './types';

/**
 * Generates a unique identifier.
 * Uses crypto.randomUUID() when available, with a fallback for non-secure contexts (e.g. LAN IP testing).
 */
export function generateUid(): Uid {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'uid-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
}
