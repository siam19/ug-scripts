// apps/web/src/components/ProductForm.tsx
import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, FormEvent } from 'react';
import {
  ACCEPTED_IMAGE_TYPES,
  MAX_IMAGE_BYTES,
  MAX_MARKET_LENGTH,
} from '../types/form';
import type { FormValues, Language } from '../types/form';

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
  const fileInput = useRef<HTMLInputElement>(null);

  // Thumbnail preview derived from values.image; object URLs revoked on change or unmount.
  const previewUrl = useMemo(() => {
    if (!values.image) return null;
    return URL.createObjectURL(values.image);
  }, [values.image]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function acceptFile(file: File | undefined) {
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
    onChange({ image: file });
  }

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
    onChange({ image: null });
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
  if (!values.image) missing.push('photo');
  const canSubmit = missing.length === 0 && !submitting;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (canSubmit) onSubmit();
  }

  return (
    <form className="panel product-form" onSubmit={handleSubmit} noValidate>
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
              <span>or choose a file</span>
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
