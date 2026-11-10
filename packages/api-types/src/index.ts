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

// Sprint 2 Granular Regeneration Types
export type SegmentRegenerateRequest = components['schemas']['SegmentRegenerateRequest'];
export type ScriptRewriteRequest = components['schemas']['ScriptRewriteRequest'];
export type ReasonLinesRewriteRequest = components['schemas']['ReasonLinesRewriteRequest'];
export type ReasonLinesRewriteResponse = components['schemas']['ReasonLinesRewriteResponse'];
export type RewrittenLine = components['schemas']['RewrittenLine'];
export type LineRephraseRequest = components['schemas']['LineRephraseRequest'];
export type LineRephraseResponse = components['schemas']['LineRephraseResponse'];
export type LineRegenerateRequest = components['schemas']['LineRegenerateRequest'];
export type LineRegenerateResponse = components['schemas']['LineRegenerateResponse'];
export type SectionRegenerateRequest = components['schemas']['SectionRegenerateRequest'];
export type SlotConfig = components['schemas']['SlotConfig'];

// Sprint 3 Security, Telemetry & Demo Product Types
export type VerifyAccessRequest = components['schemas']['VerifyAccessRequest'];
export type VerifyAccessResponse = components['schemas']['VerifyAccessResponse'];
export type AccessRequestCreate = components['schemas']['AccessRequestCreate'];
export type AccessRequestResponse = components['schemas']['AccessRequestResponse'];
export type DemoProduct = components['schemas']['DemoProduct'];
export type DemoProductsResponse = components['schemas']['DemoProductsResponse'];
export interface TokenUsage {
  prompt_tokens: number;
  candidates_tokens: number;
  total_tokens: number;
}

export interface ProgressiveGenerateResponse {
  facts: string[];
  segments: Segment[];
  scripts: (Script | null)[];
}

export type { components, paths };
