// apps/web/src/components/ProductForm.tsx
import { useCallback, useEffect, useId, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, FormEvent } from 'react';
import type { DemoProduct } from 'api-types';
import { DemoProductPicker } from './DemoProductPicker';
import {
  ACCEPTED_IMAGE_TYPES,
  MAX_IMAGE_BYTES,
  MAX_MARKET_LENGTH,
} from '../types/form';
import type { FormValues, Language, ScriptFormat } from '../types/form';

const CATEGORIES = [
  'Skincare',
  'Tech / Gadgets',
  'Fashion',
  'Food & Beverage',
  'Home & Living',
];
const OTHER = '__other__';

const LANGUAGES: { value: Language; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'bn', label: 'Bangla' },
];

const SCRIPT_FORMATS: { value: ScriptFormat; label: string }[] = [
  { value: 'ugc', label: 'UGC Video' },
  { value: 'commercial_30s', label: '30s Commercial' },
];

interface Props {
  values: FormValues;
  onChange: (patch: Partial<FormValues>) => void;
  onSubmit: () => void;
  submitting: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function ProductForm({ values, onChange, onSubmit, submitting }: Props) {
  const uid = useId();
  const id = (key: string) => `${uid}-${key}`;

  const [customCategory, setCustomCategory] = useState(
    !CATEGORIES.includes(values.category),
  );
  const [dragging, setDragging] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  // Thumbnail preview derived from values.image; created and revoked in effect
  useEffect(() => {
    if (!values.image) return;
    const url = URL.createObjectURL(values.image);
    // oxlint-disable-next-line react/set-state-in-effect
    setPreviewUrl(url);
    return () => {
      URL.revokeObjectURL(url);
      setPreviewUrl(null);
    };
  }, [values.image]);

  const acceptFile = useCallback(
    (file: File | undefined) => {
      if (!file) return;
      if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
        setImageError('Use a JPEG, PNG or WebP image.');
        return;
      }
      if (file.size > MAX_IMAGE_BYTES) {
        setImageError(`That image is ${formatBytes(file.size)}. The limit is 5 MB.`);
        return;
      }
      setImageError(null);
      onChange({ image: file, demoProductId: undefined, demoImageUrl: undefined });
    },
    [onChange],
  );

  // Listen for Ctrl+V / Cmd+V paste events containing image data
  useEffect(() => {
    function handlePaste(e: ClipboardEvent) {
      const items = e.clipboardData?.items;
      if (items) {
        for (let i = 0; i < items.length; i++) {
          const item = items[i];
          if (item.type.startsWith('image/')) {
            const file = item.getAsFile();
            if (file) {
              e.preventDefault();
              acceptFile(file);
              return;
            }
          }
        }
      }

      const files = e.clipboardData?.files;
      if (files && files.length > 0) {
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          if (file.type.startsWith('image/')) {
            e.preventDefault();
            acceptFile(file);
            return;
          }
        }
      }
    }

    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [acceptFile]);

  function handleFileInput(e: ChangeEvent<HTMLInputElement>) {
    acceptFile(e.target.files?.[0]);
    e.target.value = ''; // allow choosing the same file again
  }

  function handleDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragging(false);
    acceptFile(e.dataTransfer.files?.[0]);
  }

  function removeImage() {
    setImageError(null);
    onChange({ image: null, demoProductId: undefined, demoImageUrl: undefined });
    if (fileInput.current) fileInput.current.value = '';
  }

  function handleSelectDemo(product: DemoProduct) {
    setImageError(null);
    setCustomCategory(!CATEGORIES.includes(product.category));
    onChange({
      name: product.name,
      category: product.category,
      description: product.description,
      market: product.market,
      language: product.language as Language,
      demoProductId: product.id,
      demoImageUrl: product.image_url,
      image: null,
    });
    if (fileInput.current) fileInput.current.value = '';
  }

  function handleCategory(e: ChangeEvent<HTMLSelectElement>) {
    const v = e.target.value;
    if (v === OTHER) {
      setCustomCategory(true);
      onChange({ category: '' });
    } else {
      setCustomCategory(false);
      onChange({ category: v });
    }
  }

  const missing: string[] = [];
  if (!values.name.trim()) missing.push('product name');
  if (!values.category.trim()) missing.push('category');
  if (!values.market.trim()) missing.push('market');
  if (!values.description.trim()) missing.push('description');
  if (!values.image && !values.demoProductId) missing.push('photo');
  const canSubmit = missing.length === 0 && !submitting;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (canSubmit) onSubmit();
  }

  return (
    <form className="panel product-form" onSubmit={handleSubmit} noValidate>
      <DemoProductPicker onSelect={handleSelectDemo} selectedId={values.demoProductId} />

      <div className="form-grid">
        <div className="form-fields">
          <div className="field-row">
            <div className="field">
              <label htmlFor={id('name')}>Product name</label>
              <input
                id={id('name')}
                type="text"
                required
                value={values.name}
                placeholder="GlowHydrate Serum"
                onChange={(e) => onChange({ name: e.target.value })}
              />
            </div>

            <div className="field">
              <label htmlFor={id('category')}>Category</label>
              <select
                id={id('category')}
                value={customCategory ? OTHER : values.category}
                onChange={handleCategory}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
                <option value={OTHER}>Other</option>
              </select>
              {customCategory && (
                <input
                  type="text"
                  aria-label="Custom category"
                  value={values.category}
                  placeholder="Type a category"
                  onChange={(e) => onChange({ category: e.target.value })}
                />
              )}
            </div>
          </div>

          <div className="field-row">
            <div className="field">
              <label htmlFor={id('market')}>Market</label>
              <input
                id={id('market')}
                type="text"
                required
                maxLength={MAX_MARKET_LENGTH}
                value={values.market}
                onChange={(e) => onChange({ market: e.target.value })}
              />
              <span className="hint">
                {values.market.length}/{MAX_MARKET_LENGTH} characters
              </span>
            </div>

            <div className="field">
              <span className="label" id={id('lang')}>
                Script language
              </span>
              <div className="segmented" role="radiogroup" aria-labelledby={id('lang')}>
                {LANGUAGES.map((l) => (
                  <label key={l.value}>
                    <input
                      type="radio"
                      name={id('language')}
                      value={l.value}
                      checked={values.language === l.value}
                      onChange={() => onChange({ language: l.value })}
                    />
                    <span>{l.label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="field-row">
            <div className="field">
              <span className="label" id={id('format')}>
                Script format
              </span>
              <div className="segmented" role="radiogroup" aria-labelledby={id('format')}>
                {SCRIPT_FORMATS.map((f) => (
                  <label key={f.value}>
                    <input
                      type="radio"
                      name={id('script_format')}
                      value={f.value}
                      checked={(values.script_format ?? 'ugc') === f.value}
                      onChange={() => onChange({ script_format: f.value })}
                    />
                    <span>{f.label}</span>
                  </label>
                ))}
              </div>
              <span className="hint">
                {(values.script_format ?? 'ugc') === 'ugc'
                  ? 'Creator style, fast scroll-stopping hook, 60–90 words'
                  : 'Broadcast / digital TV commercial, voiceover & scene visual cues, 65–80 words'}
              </span>
            </div>
          </div>

          <div className="field">
            <label htmlFor={id('description')}>Product description</label>
            <textarea
              id={id('description')}
              rows={5}
              required
              value={values.description}
              placeholder="What it is, who it's for, key ingredients or specs, size, price. The more specific, the better the scripts."
              onChange={(e) => onChange({ description: e.target.value })}
            />
          </div>
        </div>

        <div className="field photo-field">
          <span className="label">Product photo</span>

          <input
            ref={fileInput}
            id={id('image')}
            className="sr-only file-input"
            type="file"
            accept={ACCEPTED_IMAGE_TYPES.join(',')}
            onChange={handleFileInput}
          />

          {values.image && previewUrl ? (
            <div className="photo-preview">
              <img src={previewUrl} alt="Product preview" />
              <div className="photo-meta">
                <span className="photo-name" title={values.image.name}>
                  {values.image.name}
                </span>
                <span className="hint">{formatBytes(values.image.size)}</span>
                <button type="button" className="btn btn-quiet" onClick={removeImage}>
                  Remove
                </button>
              </div>
            </div>
          ) : values.demoImageUrl ? (
            <div className="photo-preview">
              <img src={values.demoImageUrl} alt="Demo product preview" />
              <div className="photo-meta">
                <span className="photo-name">Preset product photo</span>
                <span className="hint">Included with demo</span>
                <button
                  type="button"
                  className="btn btn-quiet"
                  onClick={() => onChange({ demoProductId: undefined, demoImageUrl: undefined })}
                >
                  Upload custom
                </button>
              </div>
            </div>
          ) : (
            <label
              htmlFor={id('image')}
              className={`dropzone${dragging ? ' is-dragging' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              <strong>Drop the product photo here</strong>
              <span>choose a file, or paste with Ctrl+V</span>
              <span className="hint">JPEG, PNG or WebP, up to 5 MB</span>
            </label>
          )}

          {imageError && (
            <p className="field-error" role="alert">
              {imageError}
            </p>
          )}
        </div>
      </div>

      <div className="form-actions">
        <p className="hint">
          {missing.length > 0
            ? `Still needed: ${missing.join(', ')}`
            : 'Takes 10 to 20 seconds'}
        </p>
        <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
          <span className="rec-dot" aria-hidden="true" />
          {submitting ? 'Generating…' : 'Generate UGC scripts'}
        </button>
      </div>
    </form>
  );
}
