# Sprint 3 UI Handoff & Redesign Guide

> **Document**: `docs/sprints/3. Security & first deployment/sprint3-ui-handoff.md`  
> **Target Audience**: Frontend UI/UX Designer Agent  
> **Objective**: Comprehensive reference containing the architecture, component source code, state flow, API contracts, and integration points for all user interface components added in Sprint 3.

---

## 1. Context & Design Foundations

UG-Scripts is an editorial, utility-focused AI script generation tool for marketing teams and creators. The visual language is inspired by mid-century print publishing, newsrooms, and tactile editorial typography:
* **Display Font**: `var(--font-display)` (Newsreader / Serif)
* **Body Font**: `var(--font-body)` (Inter / Sans-serif)
* **Palette**:
  * Ink & Cards: `--ink: #14181a`, `--ink-2: #4a5459`, `--ink-3: #75838a`, `--card: #ffffff`, `--line: #e3e8e5`
  * Accents: Recording red dot `--rec: #e11d48`, Kind accents (`--hook: #ea580c`, `--concept: #0284c7`, `--cta: #16a34a`)
* **Styling**: Pure CSS with scoped BEM-like classes in [`apps/web/src/App.css`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.css).

---

## 2. Sprint 3 UI Components Overview

Sprint 3 introduced three key user-facing features:
1. **Access Gate Modal (`AccessGateModal.tsx`)**: An invite-only gate modal that pops up on first load or when encountering an unauthorized session (HTTP 401). Includes both an Access Code entry tab and a "Request Access" lead-capture form.
2. **Demo Product Picker (`DemoProductPicker.tsx`)**: A drawer/shelf allowing users to test the generator with 12 pre-loaded products (Bangladeshi and global) without needing to upload an image.
3. **Live Token Usage Meter (`useTokenTracker.ts` + Masthead Pill)**: Real-time session and lifetime token usage indicator mounted in the top navigation masthead.

---

## 3. Component Details & Source Code

### Component 1: `AccessGateModal.tsx`
* **File Location**: [`apps/web/src/components/AccessGateModal.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/AccessGateModal.tsx)
* **Where It Is Mounted**: Mounted at the root of the app in [`apps/web/src/App.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.tsx#L140-L148).
* **Triggers**:
  - Automatically opens if `localStorage.getItem('ug_access_code')` is empty.
  - Automatically opens if an API call returns `401 Unauthorized` (via custom event `ug:unauthorized`).
  - Opens on-demand if the user clicks the "Access" button in the masthead.
* **Backend Contracts**:
  - `POST /auth/verify`: Body `{ code: string }`. Returns `VerifyAccessResponse`.
  - `POST /auth/request-access`: Body `{ name: string, phone: string, company: string }`. Returns `AccessRequestResponse`.

#### Full Source Code:
```tsx
// apps/web/src/components/AccessGateModal.tsx
import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { IconKey, IconMailForward, IconLock, IconCheck, IconX } from '@tabler/icons-react';
import type { VerifyAccessResponse } from 'api-types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

interface Props {
  open: boolean;
  onUnlocked: (data: VerifyAccessResponse, code: string) => void;
  onClose?: () => void;
}

export function AccessGateModal({ open, onUnlocked, onClose }: Props) {
  const [mode, setMode] = useState<'enter_code' | 'request_access'>('enter_code');
  const [code, setCode] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Request Access form fields
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [company, setCompany] = useState('');
  const [submittingLead, setSubmittingLead] = useState(false);
  const [requestSubmitted, setRequestSubmitted] = useState(false);

  useEffect(() => {
    if (open) {
      // oxlint-disable-next-line react/set-state-in-effect
      setErrorMsg(null);
      setRequestSubmitted(false);
    }
  }, [open]);

  if (!open) return null;

  async function handleVerify(e: FormEvent) {
    e.preventDefault();
    const clean = code.trim();
    if (!clean) return;

    setVerifying(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`${API_URL}/auth/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: clean }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || 'Invalid or expired access code. Please request access.');
        setVerifying(false);
        return;
      }

      const data: VerifyAccessResponse = await res.json();
      localStorage.setItem('ug_access_code', clean);
      onUnlocked(data, clean);
    } catch {
      setErrorMsg(`Cannot connect to authentication server at ${API_URL}.`);
    } finally {
      setVerifying(false);
    }
  }

  async function handleRequestAccess(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !phone.trim() || !company.trim()) return;

    setSubmittingLead(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`${API_URL}/auth/request-access`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          phone: phone.trim(),
          company: company.trim(),
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || 'Failed to submit access request. Please try again.');
        setSubmittingLead(false);
        return;
      }

      setRequestSubmitted(true);
    } catch {
      setErrorMsg(`Cannot connect to server at ${API_URL}.`);
    } finally {
      setSubmittingLead(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        {onClose && (
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <IconX size={18} aria-hidden="true" />
          </button>
        )}
        <div className="modal-header">
          <div className="modal-icon-wrap">
            <IconLock size={24} aria-hidden="true" />
          </div>
          <h2>{mode === 'enter_code' ? 'Private Demo Access' : 'Request Access Code'}</h2>
          <p className="modal-sub">
            {mode === 'enter_code'
              ? 'This preview is invite-only. Enter your demo access code to unlock the script generator.'
              : 'Fill in your details below. We will review and send you a demo access code.'}
          </p>
        </div>

        {errorMsg && (
          <div className="modal-alert" role="alert">
            <IconX size={16} aria-hidden="true" />
            <span>{errorMsg}</span>
          </div>
        )}

        {mode === 'enter_code' ? (
          <form onSubmit={handleVerify} className="modal-form">
            <div className="field">
              <label htmlFor="access-code-input">Access Code</label>
              <div className="input-with-icon">
                <IconKey size={18} className="field-icon" aria-hidden="true" />
                <input
                  id="access-code-input"
                  type="text"
                  placeholder="e.g. BETA-DHAKA-01"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  autoFocus
                  required
                />
              </div>
            </div>

            <button type="submit" className="btn-primary" disabled={verifying || !code.trim()}>
              {verifying ? 'Verifying…' : 'Unlock App'}
            </button>

            <div className="modal-footer-action">
              <span>Don't have an access code?</span>
              <button
                type="button"
                className="btn-link"
                onClick={() => {
                  setMode('request_access');
                  setErrorMsg(null);
                }}
              >
                Request Access
              </button>
            </div>
          </form>
        ) : requestSubmitted ? (
          <div className="modal-success-view">
            <div className="success-icon-wrap">
              <IconCheck size={28} aria-hidden="true" />
            </div>
            <h3>Request Received!</h3>
            <p>
              Thank you, <strong>{name}</strong>. We received your request for{' '}
              <strong>{company}</strong> and will contact you via phone or WhatsApp with your code.
            </p>
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                setMode('enter_code');
                setRequestSubmitted(false);
              }}
            >
              Back to Code Entry
            </button>
          </div>
        ) : (
          <form onSubmit={handleRequestAccess} className="modal-form">
            <div className="field">
              <label htmlFor="lead-name">Your Full Name</label>
              <input
                id="lead-name"
                type="text"
                placeholder="e.g. Rahim Uddin"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="lead-phone">Phone / WhatsApp Number</label>
              <input
                id="lead-phone"
                type="tel"
                placeholder="e.g. +880 1712-345678"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="lead-company">Company or Brand Name</label>
              <input
                id="lead-company"
                type="text"
                placeholder="e.g. Chaldal / D2C Brand"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                required
              />
            </div>

            <button
              type="submit"
              className="btn-primary"
              disabled={submittingLead || !name.trim() || !phone.trim() || !company.trim()}
            >
              <IconMailForward size={16} aria-hidden="true" />
              <span>{submittingLead ? 'Submitting…' : 'Submit Access Request'}</span>
            </button>

            <div className="modal-footer-action">
              <button
                type="button"
                className="btn-link"
                onClick={() => {
                  setMode('enter_code');
                  setErrorMsg(null);
                }}
              >
                ← Back to Enter Code
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
```

---

### Component 2: `DemoProductPicker.tsx`
* **File Location**: [`apps/web/src/components/DemoProductPicker.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/DemoProductPicker.tsx)
* **Where It Is Mounted**: Mounted inside [`apps/web/src/components/ProductForm.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/ProductForm.tsx#L174) before the form grid.
* **Purpose**: Fetches the 12 curated demo products (or 3 offline fallbacks) from `GET /demo-products`. Selecting a demo autofills the entire product form and sets `demoProductId` and `demoImageUrl`.
* **State & Props**:
  - `onSelect: (product: DemoProduct) => void`
  - `selectedId?: string`

#### Full Source Code:
```tsx
// apps/web/src/components/DemoProductPicker.tsx
import { useEffect, useState } from 'react';
import { IconSparkles, IconChevronDown, IconChevronUp, IconCheck } from '@tabler/icons-react';
import type { DemoProduct } from 'api-types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

interface Props {
  onSelect: (product: DemoProduct) => void;
  selectedId?: string;
}

export function DemoProductPicker({ onSelect, selectedId }: Props) {
  const [open, setOpen] = useState(false);
  const [products, setProducts] = useState<DemoProduct[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || products.length > 0) return;

    let active = true;
    // oxlint-disable-next-line react/set-state-in-effect
    setLoading(true);
    setError(null);

    fetch(`${API_URL}/demo-products`)
      .then((res) => {
        if (!res.ok) throw new Error(`Status ${res.status}`);
        return res.json();
      })
      .then((data: { products?: DemoProduct[] }) => {
        if (!active) return;
        if (data.products && Array.isArray(data.products)) {
          setProducts(data.products);
        }
      })
      .catch(() => {
        if (!active) return;
        setError('Could not load demo products. You can still upload your own photo below.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [open, products.length]);

  const categories = ['All', ...Array.from(new Set(products.map((p) => p.category)))];
  const filteredProducts =
    selectedCategory === 'All'
      ? products
      : products.filter((p) => p.category === selectedCategory);

  const selectedProduct = products.find((p) => p.id === selectedId);

  return (
    <div className="demo-picker-wrap">
      <div className="demo-picker-header">
        <div className="demo-picker-title">
          <IconSparkles size={16} aria-hidden="true" />
          <span>Quick Demo Products</span>
        </div>

        <button
          type="button"
          className="demo-toggle-btn"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
        >
          <span>{open ? 'Hide demo items' : 'Try a sample product'}</span>
          {open ? <IconChevronUp size={16} aria-hidden="true" /> : <IconChevronDown size={16} aria-hidden="true" />}
        </button>
      </div>

      {selectedProduct && !open && (
        <div className="demo-selected-badge">
          <span className="demo-pill">Loaded: {selectedProduct.name}</span>
          <button
            type="button"
            className="btn-link"
            onClick={() => setOpen(true)}
          >
            Change
          </button>
        </div>
      )}

      {open && (
        <div className="demo-drawer">
          <div className="demo-drawer-header">
            <span className="hint">Choose any product below to instantly generate scripts without uploading an image:</span>
            {categories.length > 2 && (
              <div className="demo-category-pills">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    className={`category-pill${selectedCategory === cat ? ' is-active' : ''}`}
                    onClick={() => setSelectedCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            )}
          </div>

          {loading && <p className="hint">Loading curated products…</p>}
          {error && <p className="demo-picker-error">{error}</p>}

          <div className="demo-grid">
            {filteredProducts.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`demo-card${selectedId === p.id ? ' is-selected' : ''}`}
                onClick={() => {
                  onSelect(p);
                  setOpen(false);
                }}
              >
                <img src={p.image_url} alt={p.name} className="demo-card-img" loading="lazy" />
                <div className="demo-card-body">
                  <div className="demo-card-header">
                    <strong>{p.name}</strong>
                    {selectedId === p.id && <IconCheck size={16} color="#059669" />}
                  </div>
                  <p className="demo-card-desc">{p.description}</p>
                  <div className="demo-card-meta">
                    <span>{p.category}</span>
                    <span className="demo-lang-tag">{p.language === 'bn' ? 'বাংলা' : 'EN'}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

### Component 3: `useTokenTracker.ts`
* **File Location**: [`apps/web/src/hooks/useTokenTracker.ts`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/hooks/useTokenTracker.ts)
* **Where It Is Mounted**: Imported in [`apps/web/src/App.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/App.tsx#L23).
* **How It Works**: Listens for the `ug:token-usage` event dispatched by API callers. Returns formatted numbers for the masthead.

#### Full Source Code:
```ts
// apps/web/src/hooks/useTokenTracker.ts
import { useEffect, useState } from 'react';
import type { TokenUsage } from 'api-types';

const LIFETIME_TOKENS_KEY = 'ug_lifetime_tokens';

export function useTokenTracker() {
  const [sessionTokens, setSessionTokens] = useState(0);
  const [lifetimeTokens, setLifetimeTokens] = useState<number>(() => {
    try {
      const saved = localStorage.getItem(LIFETIME_TOKENS_KEY);
      return saved ? parseInt(saved, 10) : 0;
    } catch {
      return 0;
    }
  });

  useEffect(() => {
    function handleTokenUsage(e: Event) {
      const customEvent = e as CustomEvent<TokenUsage | { total_tokens?: number }>;
      const usage = customEvent.detail;
      const count = usage?.total_tokens ?? 0;
      if (count > 0) {
        setSessionTokens((prev) => prev + count);
        setLifetimeTokens((prev) => {
          const next = prev + count;
          try {
            localStorage.setItem(LIFETIME_TOKENS_KEY, next.toString());
          } catch {
            // Storage quota or privacy mode ignore
          }
          return next;
        });
      }
    }

    window.addEventListener('ug:token-usage', handleTokenUsage);
    return () => window.removeEventListener('ug:token-usage', handleTokenUsage);
  }, []);

  function formatCount(tokens: number): string {
    if (tokens < 1000) return tokens.toString();
    if (tokens < 10_000) return `${(tokens / 1000).toFixed(1)}k`;
    return `${Math.round(tokens / 1000)}k`;
  }

  return {
    sessionTokens,
    lifetimeTokens,
    formattedSession: formatCount(sessionTokens),
    formattedLifetime: formatCount(lifetimeTokens),
  };
}
```

---

## 4. Integration Points in Modified Files

### 1. `apps/web/src/App.tsx`
In `App.tsx`, the masthead renders the token usage pill and an access key button, and mounts `AccessGateModal`:

```tsx
// Inside <header className="masthead">
<div className="masthead-actions">
  <div
    className="token-usage-pill"
    title={`Session: ${sessionTokens.toLocaleString()} tokens | Lifetime: ${lifetimeTokens.toLocaleString()} tokens`}
  >
    <span className="rec-dot token-dot" aria-hidden="true" />
    <span>Tokens: {formattedSession} session · {formattedLifetime} total</span>
  </div>

  <button
    type="button"
    className="access-btn"
    onClick={() => setAccessModalOpen(true)}
    title="Manage demo access key"
  >
    <IconKey size={15} aria-hidden="true" />
    <span>Access</span>
  </button>

  <button
    type="button"
    className="saved-btn"
    onClick={() => setDrawerOpen(true)}
  >
    <IconBookmark size={16} aria-hidden="true" />
    <span>Saved scripts</span>
    {savedScripts.length > 0 && (
      <span className="saved-count-pill">{savedScripts.length}</span>
    )}
  </button>
</div>

// At bottom of return JSX:
<AccessGateModal
  open={accessModalOpen}
  onUnlocked={() => setAccessModalOpen(false)}
  onClose={localStorage.getItem('ug_access_code') ? () => setAccessModalOpen(false) : undefined}
/>
```

### 2. `apps/web/src/components/ProductForm.tsx`
In `ProductForm.tsx`, `DemoProductPicker` is placed right above the `.form-grid`, and the image preview section handles both uploaded files and demo product images:

```tsx
// At top of <form className="panel product-form" ...>
<DemoProductPicker onSelect={handleSelectDemo} selectedId={values.demoProductId} />

// In the photo-field section:
{values.image && previewUrl ? (
  <div className="photo-preview">
    <img src={previewUrl} alt="Product preview" />
    <div className="photo-meta">
      <span className="photo-name" title={values.image.name}>{values.image.name}</span>
      <span className="hint">{formatBytes(values.image.size)}</span>
      <button type="button" className="btn btn-quiet" onClick={removeImage}>Remove</button>
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
  <label htmlFor={id('image')} className={`dropzone${dragging ? ' is-dragging' : ''}`} ...>
    <strong>Drop the product photo here</strong>
    <span>choose a file, or paste with Ctrl+V</span>
    <span className="hint">JPEG, PNG or WebP, up to 5 MB</span>
  </label>
)}
```

---

## 5. Existing CSS Styles (`apps/web/src/App.css`)

Here are the current styles appended to the end of `App.css` (lines 1850-2050):

```css
/* ---------- Token Pill & Access Button in Masthead ---------- */
.token-usage-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--tint);
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--ink-2);
  user-select: none;
}
.token-usage-pill .token-dot {
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
}

.access-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--ink);
  cursor: pointer;
  transition: border-color 0.12s, background-color 0.12s;
}
.access-btn:hover {
  border-color: var(--ink);
  background: var(--tint);
}

/* ---------- Access Gate Modal ---------- */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(20, 24, 26, 0.65);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: fadeIn 0.2s ease-out;
}

.modal-card {
  position: relative;
  background: #fff;
  border-radius: 16px;
  width: 100%;
  max-width: 440px;
  padding: 32px 28px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.18), 0 1px 3px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--line);
  animation: modalScale 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalScale {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-close-btn {
  position: absolute;
  top: 18px;
  right: 18px;
  background: transparent;
  border: none;
  color: var(--ink-3);
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.12s, background-color 0.12s;
}
.modal-close-btn:hover {
  color: var(--ink);
  background: var(--tint);
}

.modal-header {
  text-align: center;
  margin-bottom: 24px;
}
.modal-icon-wrap {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  border-radius: 12px;
  background: var(--tint);
  border: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink);
}
.modal-header h2 {
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.015em;
  margin-bottom: 6px;
}
.modal-sub {
  font-size: 0.875rem;
  color: var(--ink-2);
  line-height: 1.45;
}

.modal-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  margin-bottom: 18px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #991b1b;
  font-size: 0.8125rem;
  font-weight: 500;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.modal-form .field {
  gap: 6px;
}
.modal-form .btn-primary {
  width: 100%;
  height: 44px;
  margin-top: 4px;
  font-size: 0.9375rem;
}

.input-with-icon {
  position: relative;
  display: flex;
  align-items: center;
}
.input-with-icon .field-icon {
  position: absolute;
  left: 14px;
  color: var(--ink-3);
  pointer-events: none;
}
.input-with-icon input {
  padding-left: 42px !important;
  font-family: monospace;
  font-size: 1rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.modal-footer-action {
  margin-top: 14px;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--ink-2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.btn-link {
  background: transparent;
  border: none;
  color: #0066cc;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.btn-link:hover {
  opacity: 0.8;
}

.modal-success-view {
  text-align: center;
  padding: 12px 0;
}
.success-icon-wrap {
  width: 52px;
  height: 52px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #059669;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-success-view h3 {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 8px;
}
.modal-success-view p {
  font-size: 0.875rem;
  color: var(--ink-2);
  line-height: 1.5;
  margin-bottom: 24px;
}

/* ---------- Demo Product Picker ---------- */
.demo-picker-wrap {
  margin-bottom: 24px;
  border-bottom: 1px dashed var(--line);
  padding-bottom: 20px;
}

.demo-picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.demo-picker-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--ink);
}

.demo-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: var(--tint);
  border: 1px solid var(--line);
  border-radius: 8px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--ink);
  cursor: pointer;
  transition: all 0.15s;
}
.demo-toggle-btn:hover {
  background: #e2e8e4;
  border-color: var(--ink-3);
}

.demo-selected-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  font-size: 0.8125rem;
  color: #166534;
}
.demo-selected-badge .demo-pill {
  padding: 2px 8px;
  background: #dcfce7;
  border-radius: 4px;
  font-weight: 600;
}

.demo-drawer {
  margin-top: 16px;
  padding: 16px;
  background: #fafbfa;
  border: 1px solid var(--line);
  border-radius: 12px;
  animation: fadeIn 0.2s ease-out;
}

.demo-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.demo-category-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.category-pill {
  padding: 4px 10px;
  font-size: 0.75rem;
  font-weight: 600;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--ink-2);
  cursor: pointer;
  transition: all 0.12s;
}
.category-pill:hover {
  border-color: var(--ink);
}
.category-pill.is-active {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}

.demo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  max-height: 380px;
  overflow-y: auto;
  padding: 2px;
}

.demo-card {
  text-align: left;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.12s;
  padding: 0;
}
.demo-card:hover {
  border-color: var(--ink);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}
.demo-card.is-selected {
  border-color: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.3);
}

.demo-card-img {
  width: 100%;
  height: 120px;
  object-fit: cover;
  background: var(--tint);
  border-bottom: 1px solid var(--line);
}

.demo-card-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.demo-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 4px;
}
.demo-card-header strong {
  font-size: 0.8125rem;
  line-height: 1.3;
  color: var(--ink);
}
.demo-lang-tag {
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 5px;
  background: var(--tint);
  border-radius: 4px;
  color: var(--ink-2);
}

.demo-card-desc {
  font-size: 0.75rem;
  color: var(--ink-2);
  line-height: 1.35;
  margin: 4px 0 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.demo-card-meta {
  margin-top: auto;
  display: flex;
  justify-content: space-between;
  font-size: 0.6875rem;
  color: var(--ink-3);
  font-weight: 500;
}
```

---

## 6. Recommendations & Areas for Visual Elevation

1. **Access Gate Modal**:
   - Currently feels generic. Consider incorporating warm editorial touches (e.g. newspaper masthead stamp, embossed border, subtler monochromatic badge, styled monospace code inputs with spaced dashes).
   - Smooth transition between "Enter Code" and "Request Access" views.
2. **Demo Product Picker**:
   - Instead of a vertical accordion that pushes the form down, consider a horizontal carousel or side-docked pill strip, or a sleek drawer with crisp card elevation and rounded image aspect ratios.
   - Improve contrast and language indicator tag styling (`বাংলা` vs `EN`).
3. **Token Usage Meter in Masthead**:
   - Give the pill a refined layout matching `.saved-btn` (subtle border, crisp typography, clean tooltip or dropdown popover with input/output breakdown).
