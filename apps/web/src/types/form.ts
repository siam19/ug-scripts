// apps/web/src/types/form.ts

export type Language = 'en' | 'bn';

export interface FormValues {
  name: string;
  description: string;
  category: string;
  market: string;
  language: Language;
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
  image: null,
};

export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
export const ACCEPTED_IMAGE_TYPES: string[] = ['image/jpeg', 'image/png', 'image/webp'];
export const MAX_MARKET_LENGTH = 60;
