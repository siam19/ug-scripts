// API types generated or derived from FastAPI OpenAPI schema

export type LineKind = 'hook' | 'concept' | 'cta';

export interface Line {
  id: number;
  kind: LineKind;
  text: string;
}

export interface Reason {
  title: string;
  why: string;
  line_ids: number[];
}

export interface Script {
  segment: string;
  lines: Line[];
  reasons: Reason[];
}

export interface Segment {
  name: string;
  who: string;
  pain_point: string;
  platforms: string[];
}

export interface GenerateResponse {
  facts: string[];
  segments: Segment[];
  scripts: Script[];
}
