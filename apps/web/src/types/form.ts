// apps/web/src/types/form.ts
import type { ScriptFormat } from 'api-types';

export type Language = 'en' | 'bn';
export type { ScriptFormat };

export interface FormValues {
  name: string;
  description: string;
  category: string;
  market: string;
  language: Language;
  script_format: ScriptFormat;
  image: File | null;
  demoProductId?: string;
  demoImageUrl?: string;
}

export const INITIAL_VALUES: FormValues = {
  name: '',
  description: '',
  category: 'Skincare',
  market: 'Bangladesh',
  language: 'en',
  script_format: 'ugc',
  image: null,
};

export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export const ACCEPTED_IMAGE_TYPES: string[] = ['image/jpeg', 'image/png', 'image/webp'];
export const MAX_MARKET_LENGTH = 60;
