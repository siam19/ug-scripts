/**
 * Re-exports strongly typed schemas generated from the FastAPI OpenAPI specification.
 */
import type { components, paths } from './schema.d.ts';

export type GenerateResponse = components['schemas']['GenerateResponse'];
export type Segment = components['schemas']['Segment'];
export type Script = components['schemas']['Script'];
export type Line = components['schemas']['Line'];
export type Reason = components['schemas']['Reason'];
export type LineKind = components['schemas']['Line']['kind'];

export interface ProgressiveGenerateResponse {
  facts: string[];
  segments: Segment[];
  scripts: (Script | null)[];
}

export type { components, paths };
