# Sprint 3 UI Redesign: Access Gate, Sample Shelf, Token Meter

One file with everything the local agent needs: instructions, the redesigned components, the updated hook, the CSS, and the `App.tsx` changes.

**How it was checked.** The three components were bundled with esbuild and rendered in headless Chromium at desktop and mobile widths, covering the code view, error, request form, success, shelf closed/open/selected, and the token popover. They were not type-checked against your repo (no `api-types` or Tabler install in my sandbox), so expect small type fixes on first build. The sandbox has no Newsreader font, so serif metrics in my renders were approximate; headings will be narrower with the real font.

---

## 1. What changed and why

| Component | Before | After |
|---|---|---|
| **Access gate** | Centered white card, lock icon in a square, generic input | Two-part "title card": an ink **cover** (film-slate stripe, wordmark, headline, demo-video poster) beside a paper **panel**. The code field is an **admit-one ticket** with notched, perforated edges. Tabs switch between "I have a code" and "Request access" with a sliding underline. Success shows a rotated **rubber stamp**. |
| **Demo picker** | Accordion that pushed the form down, dense text cards | **Sample shelf**: a slim bar with a fan of print thumbnails. Opening it shows a floating sheet with category tabs and a horizontal rail of 4:5 poster cards. The form never moves. |
| **Token pill** | Plain pill with a green dot and a long sentence | **Token meter**: same height and border as the other masthead buttons, with a bar glyph, "Tokens" and a figure that ticks when usage changes. Click opens a small receipt with dotted-leader totals and an input/output split. |

Design language: print and newsroom, using only your existing tokens (`--ink`, `--ink-2`, `--ink-3`, `--card`, `--line`, `--tint`, `--rec`, kind colors, `--font-display`, `--font-body`). Color is kept for meaning: red for the recording dot and errors, the three kind colors only in the demo-video progress strip. No gradients, glows or icon-in-a-square.

The **View demo video** button appears twice: as a poster on the cover (desktop) and as a text pill in the panel footer (below 860px, where the cover shrinks). Both use the same `DEMO_VIDEO_URL` constant, currently empty, so the click does nothing until you add a URL (section 3.1).

---

## 2. Install steps for the agent

1. **Replace** `apps/web/src/components/AccessGateModal.tsx` and `DemoProductPicker.tsx` with the versions in section 3. Props are unchanged, so `App.tsx` and `ProductForm.tsx` need no prop changes.
2. **Add** `apps/web/src/components/TokenMeter.tsx` (new).
3. **Replace** `apps/web/src/hooks/useTokenTracker.ts`. It still returns every field it did before and adds `sessionInput` and `sessionOutput`.
4. **Add the CSS** from section 4 (append to `App.css` or import as `sprint3.css`). Then **delete the old CSS** for these blocks in `App.css`:
   - "Token Pill & Access Button in Masthead": delete `.token-usage-pill` and `.token-usage-pill .token-dot`. **Keep** `.access-btn`; the new CSS restyles it and `.saved-btn` to match.
   - "Access Gate Modal": delete `.modal-backdrop`, `.modal-card`, `@keyframes modalScale`, `.modal-close-btn`, `.modal-header`, `.modal-icon-wrap`, `.modal-sub`, `.modal-alert`, `.modal-form`, `.input-with-icon`, `.modal-footer-action`, `.modal-success-view`, `.success-icon-wrap`.
   - "Demo Product Picker": delete every `.demo-*` rule and `.category-pill`.
   - `.btn-link`: search the codebase first. It was only used by the old modal and picker; delete it if nothing else uses it.
5. **Update the masthead in `App.tsx`** (section 5).
6. **Check two assumptions in your CSS**:
   - `--tint` and `--font-display` / `--font-body` exist (the old CSS already used `--tint`).
   - No ancestor of `.shelf` (the `.panel.product-form`) has `overflow: hidden`, or the floating sheet will be clipped.
7. **Fonts**: Newsreader and Inter are already your display and body fonts. Bengali text (the `বাংলা` chip) needs a Bengali-capable fallback; if the app already loads Hind Siliguri, nothing to do, otherwise add it to your Google Fonts import.
8. **Set `DEMO_VIDEO_URL`** when the video exists (section 3.1).

### Behavior notes

- **Access gate** keeps every contract from the handoff: the same props, the same two endpoints and error messages, the `ug_access_code` localStorage write, and a close button only when `onClose` is passed. New: a focus trap, Esc closes (only when `onClose` exists), page scroll is locked while open, focus returns to the previously focused element, `aria-labelledby` points at the heading, and the tabs support Left/Right arrows. The first field is focused by an effect instead of `autoFocus`.
- **Demo picker** now fetches `/demo-products` **on mount** instead of on first open, so the collapsed bar can show real thumbnails. If that endpoint requires the access code, move the `useEffect` that calls `fetchProducts` to run after unlock. A failed load shows a "Try again" link inside the sheet.
- **Token meter**: the input/output split only appears if the API reports it. `useTokenTracker` reads several possible field names (`input_tokens`, `prompt_tokens`, `prompt_token_count`, and the output equivalents). Open `TokenUsage` in `api-types` and trim the `INPUT_KEYS` / `OUTPUT_KEYS` arrays to the real names. If the API only reports a total, the popover simply omits the split.
- **Reduced motion**: your global reduced-motion rule neutralizes every animation here. The spinner then stops, but the button text still changes to "Verifying…" so the state stays readable.
- **Browser support**: the ticket notches use CSS `mask` (prefixed too). Where unsupported, the ticket degrades to a plain bordered rectangle.

---

## 3. Components

### 3.1 `apps/web/src/components/AccessGateModal.tsx`

Set the demo video link on the `DEMO_VIDEO_URL` line at the top. It accepts any URL; it opens in a new tab.

```tsx
// apps/web/src/components/AccessGateModal.tsx
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent, RefObject } from 'react';
import {
  IconAlertCircle,
  IconArrowRight,
  IconArrowUpRight,
  IconKey,
  IconLoader2,
  IconPlayerPlayFilled,
  IconSend,
  IconX,
} from '@tabler/icons-react';
import type { VerifyAccessResponse } from 'api-types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

/**
 * TODO: paste the demo video URL here (YouTube, Loom, Vimeo, a hosted .mp4, anything).
 * While this is empty the "View demo video" button renders but does nothing.
 */
export const DEMO_VIDEO_URL = '';

interface Props {
  open: boolean;
  onUnlocked: (data: VerifyAccessResponse, code: string) => void;
  onClose?: () => void;
}

type Mode = 'enter_code' | 'request_access';

/** Focus trap, Esc-to-close (only when closable), scroll lock, and focus restore. */
function useDialogA11y(open: boolean, ref: RefObject<HTMLElement | null>, onClose?: () => void) {
  // Keep the latest onClose without re-running the effect (App passes a new arrow every render).
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  });

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    function onKeyDown(e: globalThis.KeyboardEvent) {
      if (e.key === 'Escape' && closeRef.current) {
        e.preventDefault();
        closeRef.current();
        return;
      }
      if (e.key !== 'Tab' || !ref.current) return;
      const focusable = ref.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (!ref.current.contains(active)) {
        e.preventDefault();
        first.focus();
      } else if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [open, ref]);
}

function DemoVideoLink({ variant }: { variant: 'poster' | 'inline' }) {
  const hasUrl = DEMO_VIDEO_URL.length > 0;
  return (
    <a
      className={`gate-video is-${variant}`}
      href={hasUrl ? DEMO_VIDEO_URL : '#'}
      target={hasUrl ? '_blank' : undefined}
      rel="noopener noreferrer"
      onClick={(e) => {
        if (!hasUrl) e.preventDefault();
      }}
    >
      {variant === 'poster' ? (
        <>
          <span className="vp-frame" aria-hidden="true">
            <span className="vp-rec">
              <i className="rec-dot" />
              REC
            </span>
            <span className="vp-tc">00:00:00</span>
            <span className="vp-play">
              <IconPlayerPlayFilled size={22} />
            </span>
            <span className="vp-bar">
              <i data-kind="hook" />
              <i data-kind="concept" />
              <i data-kind="cta" />
            </span>
          </span>
          <span className="vp-caption">
            <strong>View demo video</strong>
            <IconArrowUpRight size={18} aria-hidden="true" />
          </span>
        </>
      ) : (
        <>
          <IconPlayerPlayFilled size={14} aria-hidden="true" />
          <span>View demo video</span>
        </>
      )}
    </a>
  );
}

export function AccessGateModal({ open, onUnlocked, onClose }: Props) {
  const uid = useId();
  const id = (k: string) => `${uid}-${k}`;

  const [mode, setMode] = useState<Mode>('enter_code');
  const [code, setCode] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [shake, setShake] = useState(false);

  // Request Access form fields
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [company, setCompany] = useState('');
  const [submittingLead, setSubmittingLead] = useState(false);
  const [requestSubmitted, setRequestSubmitted] = useState(false);

  const cardRef = useRef<HTMLDivElement>(null);
  const codeRef = useRef<HTMLInputElement>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useDialogA11y(open, cardRef, onClose);

  useEffect(() => {
    if (open) {
      // oxlint-disable-next-line react/set-state-in-effect
      setErrorMsg(null);
      setRequestSubmitted(false);
    }
  }, [open]);

  // Move focus to the first field of whichever view is showing.
  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => {
      (mode === 'enter_code' ? codeRef : nameRef).current?.focus();
    }, 80);
    return () => window.clearTimeout(t);
  }, [open, mode]);

  if (!open) return null;

  function fail(message: string) {
    setErrorMsg(message);
    setShake(true);
    window.setTimeout(() => setShake(false), 480);
  }

  function switchMode(next: Mode) {
    setMode(next);
    setErrorMsg(null);
    setRequestSubmitted(false);
  }

  function handleTabKey(e: KeyboardEvent<HTMLButtonElement>) {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      switchMode(mode === 'enter_code' ? 'request_access' : 'enter_code');
    }
  }

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
        fail(err.detail || 'Invalid or expired access code. Please request access.');
        return;
      }

      const data: VerifyAccessResponse = await res.json();
      localStorage.setItem('ug_access_code', clean);
      onUnlocked(data, clean);
    } catch {
      fail(`Cannot connect to authentication server at ${API_URL}.`);
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
        fail(err.detail || 'Failed to submit access request. Please try again.');
        return;
      }

      setRequestSubmitted(true);
    } catch {
      fail(`Cannot connect to server at ${API_URL}.`);
    } finally {
      setSubmittingLead(false);
    }
  }

  const view = mode === 'enter_code' ? 'code' : requestSubmitted ? 'done' : 'request';
  const title =
    view === 'code' ? 'Private demo access' : view === 'request' ? 'Request an access code' : 'Request received';

  return (
    <div className="gate-backdrop">
      <div
        ref={cardRef}
        className="gate"
        role="dialog"
        aria-modal="true"
        aria-labelledby={id('title')}
      >
        {/* ---------- Cover: brand, pitch, demo video ---------- */}
        <aside className="gate-cover">
          <div className="gate-slate" aria-hidden="true" />
          <div className="gate-brand">
            <span className="rec-dot" aria-hidden="true" />
            <span className="gate-wordmark">UG-Scripts</span>
            <span className="gate-tag">Private preview</span>
          </div>

          <p className="gate-headline">
            Product in.
            <br />
            <em>Ready-to-film</em> scripts out.
          </p>
          <p className="gate-lede">
            Describe a product, add its photo, and get three customer segments with a phone-ready
            UGC script for each.
          </p>

          <DemoVideoLink variant="poster" />
        </aside>

        {/* ---------- Panel: code entry / request access ---------- */}
        <section className="gate-panel">
          {onClose && (
            <button type="button" className="gate-close" onClick={onClose} aria-label="Close">
              <IconX size={18} aria-hidden="true" />
            </button>
          )}

          <div className="gate-tabs" role="tablist" aria-label="Access method" data-mode={mode}>
            <button
              type="button"
              role="tab"
              id={id('tab-code')}
              aria-selected={mode === 'enter_code'}
              aria-controls={id('panel')}
              tabIndex={mode === 'enter_code' ? 0 : -1}
              onClick={() => switchMode('enter_code')}
              onKeyDown={handleTabKey}
            >
              I have a code
            </button>
            <button
              type="button"
              role="tab"
              id={id('tab-request')}
              aria-selected={mode === 'request_access'}
              aria-controls={id('panel')}
              tabIndex={mode === 'request_access' ? 0 : -1}
              onClick={() => switchMode('request_access')}
              onKeyDown={handleTabKey}
            >
              Request access
            </button>
          </div>

          <div
            className="gate-view"
            key={view}
            role="tabpanel"
            id={id('panel')}
            aria-labelledby={id(mode === 'enter_code' ? 'tab-code' : 'tab-request')}
          >
            <h2 className="gate-title" id={id('title')}>
              {title}
            </h2>

            {view === 'code' && (
              <>
                <p className="gate-sub">
                  This preview is invite-only. Enter your demo access code to unlock the script
                  generator.
                </p>

                <form className="gate-form" onSubmit={handleVerify}>
                  <div className={`gate-ticket-wrap${shake ? ' is-shaking' : ''}`}>
                    <div className={`gate-ticket${errorMsg ? ' has-error' : ''}`}>
                      <div className="ticket-in">
                        <div className="ticket-stub" aria-hidden="true">
                          <IconKey size={20} />
                          <span>
                            Admit
                            <br />
                            one
                          </span>
                        </div>
                        <div className="ticket-body">
                          <label htmlFor={id('code')}>Access code</label>
                          <input
                            id={id('code')}
                            ref={codeRef}
                            type="text"
                            autoComplete="off"
                            autoCapitalize="characters"
                            spellCheck={false}
                            placeholder="BETA-DHAKA-01"
                            value={code}
                            onChange={(e) => setCode(e.target.value)}
                            aria-invalid={Boolean(errorMsg)}
                            aria-describedby={errorMsg ? id('error') : undefined}
                            required
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {errorMsg && (
                    <p className="gate-error" id={id('error')} role="alert">
                      <IconAlertCircle size={16} aria-hidden="true" />
                      <span>{errorMsg}</span>
                    </p>
                  )}

                  <button
                    type="submit"
                    className="gate-submit"
                    disabled={verifying || !code.trim()}
                    aria-busy={verifying}
                  >
                    {verifying ? (
                      <>
                        <span>Verifying…</span>
                        <IconLoader2 size={18} className="gate-spin" aria-hidden="true" />
                      </>
                    ) : (
                      <>
                        <span>Unlock app</span>
                        <IconArrowRight size={18} aria-hidden="true" />
                      </>
                    )}
                  </button>
                </form>

                <p className="gate-switch">
                  Don&rsquo;t have an access code?{' '}
                  <button type="button" className="gate-link" onClick={() => switchMode('request_access')}>
                    Request access
                  </button>
                </p>
              </>
            )}

            {view === 'request' && (
              <>
                <p className="gate-sub">
                  Fill in your details below. We will review and send you a demo access code.
                </p>

                {errorMsg && (
                  <p className="gate-error" role="alert">
                    <IconAlertCircle size={16} aria-hidden="true" />
                    <span>{errorMsg}</span>
                  </p>
                )}

                <form className="gate-form" onSubmit={handleRequestAccess}>
                  <div className="gate-field">
                    <label htmlFor={id('name')}>Your full name</label>
                    <input
                      id={id('name')}
                      ref={nameRef}
                      type="text"
                      autoComplete="name"
                      placeholder="e.g. Rahim Uddin"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="gate-field">
                    <label htmlFor={id('phone')}>Phone / WhatsApp number</label>
                    <input
                      id={id('phone')}
                      type="tel"
                      autoComplete="tel"
                      placeholder="e.g. +880 1712-345678"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      required
                    />
                  </div>
                  <div className="gate-field">
                    <label htmlFor={id('company')}>Company or brand name</label>
                    <input
                      id={id('company')}
                      type="text"
                      autoComplete="organization"
                      placeholder="e.g. Chaldal / D2C Brand"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    className="gate-submit"
                    disabled={submittingLead || !name.trim() || !phone.trim() || !company.trim()}
                    aria-busy={submittingLead}
                  >
                    <span>{submittingLead ? 'Submitting…' : 'Submit access request'}</span>
                    {submittingLead ? (
                      <IconLoader2 size={18} className="gate-spin" aria-hidden="true" />
                    ) : (
                      <IconSend size={18} aria-hidden="true" />
                    )}
                  </button>
                </form>
              </>
            )}

            {view === 'done' && (
              <div className="gate-done">
                <div className="gate-stamp" aria-hidden="true">
                  <span>Pending</span>
                </div>
                <p className="gate-sub">
                  Thank you, <strong>{name}</strong>. We received your request for{' '}
                  <strong>{company}</strong> and will contact you via phone or WhatsApp with your
                  code.
                </p>
                <button type="button" className="gate-submit is-ghost" onClick={() => switchMode('enter_code')}>
                  <span>Back to code entry</span>
                  <IconArrowRight size={18} aria-hidden="true" />
                </button>
              </div>
            )}
          </div>

          {/* Narrow screens: the poster is hidden, so keep a text link to the video. */}
          <div className="gate-foot">
            <DemoVideoLink variant="inline" />
          </div>
        </section>
      </div>
    </div>
  );
}
```

### 3.2 `apps/web/src/components/DemoProductPicker.tsx`

Props are unchanged (`onSelect`, `selectedId`).

```tsx
// apps/web/src/components/DemoProductPicker.tsx
import { useCallback, useEffect, useId, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { IconCheck, IconChevronDown, IconChevronLeft, IconChevronRight } from '@tabler/icons-react';
import type { DemoProduct } from 'api-types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

interface Props {
  onSelect: (product: DemoProduct) => void;
  selectedId?: string;
}

function LangChip({ lang }: { lang: string }) {
  const bn = lang === 'bn';
  return (
    <span className={`shelf-lang${bn ? ' is-bn' : ''}`} lang={bn ? 'bn' : 'en'}>
      {bn ? 'বাংলা' : 'EN'}
    </span>
  );
}

/**
 * "Sample shelf": a slim bar that fans out thumbnails of the samples. Opening it shows a floating
 * sheet with a horizontal rail of poster cards, so the form below never gets pushed down.
 */
export function DemoProductPicker({ onSelect, selectedId }: Props) {
  const sheetId = useId();
  const [open, setOpen] = useState(false);
  const [products, setProducts] = useState<DemoProduct[]>([]);
  const [category, setCategory] = useState('All');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const wrapRef = useRef<HTMLDivElement>(null);
  const barRef = useRef<HTMLButtonElement>(null);
  const railRef = useRef<HTMLDivElement>(null);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  // Fetched on mount (not on open) so the collapsed bar can show real thumbnails.
  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/demo-products`);
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = (await res.json()) as { products?: DemoProduct[] };
      if (alive.current && Array.isArray(data.products)) setProducts(data.products);
    } catch {
      if (alive.current) {
        setError('Could not load sample products. You can still upload your own photo below.');
      }
    } finally {
      if (alive.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    void fetchProducts();
  }, [fetchProducts]);

  // Outside click and Esc close the sheet.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false);
        barRef.current?.focus();
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const categories = ['All', ...Array.from(new Set(products.map((p) => p.category)))];
  const visible = category === 'All' ? products : products.filter((p) => p.category === category);
  const selected = products.find((p) => p.id === selectedId);
  const hasSelection = Boolean(selectedId);

  function scrollRail(dir: -1 | 1) {
    const rail = railRef.current;
    if (!rail) return;
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    rail.scrollBy({ left: dir * rail.clientWidth * 0.8, behavior: smooth ? 'smooth' : 'auto' });
  }

  const stackItems = products.slice(0, 4);

  return (
    <div className="shelf" ref={wrapRef}>
      <button
        ref={barRef}
        type="button"
        className={`shelf-bar${open ? ' is-open' : ''}`}
        aria-expanded={open}
        aria-controls={sheetId}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="shelf-stack" aria-hidden="true">
          {selected ? (
            <img className="shelf-thumb is-main" src={selected.image_url} alt="" />
          ) : stackItems.length > 0 ? (
            stackItems.map((p, i) => (
              <img
                key={p.id}
                className="shelf-thumb"
                src={p.image_url}
                alt=""
                style={{ '--i': i } as CSSProperties}
              />
            ))
          ) : (
            [0, 1, 2].map((i) => (
              <span key={i} className="shelf-thumb is-empty" style={{ '--i': i } as CSSProperties} />
            ))
          )}
        </span>

        <span className="shelf-copy">
          {hasSelection ? (
            <>
              <strong>{selected?.name ?? 'Sample loaded'}</strong>
              <span>Sample product, photo included</span>
            </>
          ) : (
            <>
              <strong>No photo handy?</strong>
              <span>
                {products.length > 0
                  ? `Start from one of ${products.length} sample products`
                  : 'Start from a sample product'}
              </span>
            </>
          )}
        </span>

        <span className="shelf-cta">
          {open ? 'Close' : hasSelection ? 'Change' : 'Browse'}
          <IconChevronDown size={16} aria-hidden="true" />
        </span>
      </button>

      {open && (
        <div className="shelf-sheet" id={sheetId} role="region" aria-label="Sample products">
          <div className="shelf-toolbar">
            {categories.length > 2 ? (
              <div className="shelf-tabs">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    className={`shelf-tab${category === cat ? ' is-active' : ''}`}
                    aria-pressed={category === cat}
                    onClick={() => setCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            ) : (
              <span className="shelf-tabs-empty" />
            )}

            {visible.length > 3 && (
              <div className="shelf-arrows">
                <button type="button" aria-label="Scroll samples left" onClick={() => scrollRail(-1)}>
                  <IconChevronLeft size={16} aria-hidden="true" />
                </button>
                <button type="button" aria-label="Scroll samples right" onClick={() => scrollRail(1)}>
                  <IconChevronRight size={16} aria-hidden="true" />
                </button>
              </div>
            )}
          </div>

          {error && (
            <p className="shelf-error" role="alert">
              {error}{' '}
              <button type="button" className="gate-link" onClick={() => void fetchProducts()}>
                Try again
              </button>
            </p>
          )}

          <div className="shelf-rail" ref={railRef}>
            {loading &&
              [0, 1, 2, 3, 4].map((i) => (
                <div key={i} className="shelf-card is-skeleton" aria-hidden="true">
                  <span className="shelf-photo" />
                  <span className="shelf-name">&nbsp;</span>
                </div>
              ))}

            {!loading &&
              visible.map((p) => {
                const isSelected = selectedId === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    className={`shelf-card${isSelected ? ' is-selected' : ''}`}
                    aria-pressed={isSelected}
                    title={p.description}
                    onClick={() => {
                      onSelect(p);
                      setOpen(false);
                    }}
                  >
                    <span className="shelf-photo">
                      <img
                        src={p.image_url}
                        alt=""
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.style.visibility = 'hidden';
                        }}
                      />
                      <LangChip lang={p.language} />
                      {isSelected && (
                        <span className="shelf-check">
                          <IconCheck size={14} aria-hidden="true" />
                        </span>
                      )}
                    </span>
                    <span className="shelf-name">{p.name}</span>
                    <span className="shelf-meta">{p.category}</span>
                  </button>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
```

### 3.3 `apps/web/src/components/TokenMeter.tsx` (new)

```tsx
// apps/web/src/components/TokenMeter.tsx
import { useEffect, useId, useRef, useState } from 'react';
import type { TokenTracker } from '../hooks/useTokenTracker';

interface Props {
  tracker: TokenTracker;
}

function MeterGlyph() {
  return (
    <svg className="meter-glyph" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
      <rect x="1.5" y="9.5" width="3" height="5" rx="1" />
      <rect x="6.5" y="5.5" width="3" height="9" rx="1" />
      <rect x="11.5" y="1.5" width="3" height="13" rx="1" />
    </svg>
  );
}

/**
 * Masthead usage pill. Click or Enter opens a small "receipt" with session and all-time totals,
 * plus an input/output split when the API reports one.
 */
export function TokenMeter({ tracker }: Props) {
  const popId = useId();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false);
        btnRef.current?.focus();
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const { sessionTokens, lifetimeTokens, sessionInput, sessionOutput } = tracker;
  const split = sessionInput + sessionOutput;
  const inputPct = split > 0 ? Math.round((sessionInput / split) * 100) : 0;

  return (
    <div className="meter" ref={wrapRef}>
      <button
        ref={btnRef}
        type="button"
        className={`meter-btn${open ? ' is-open' : ''}`}
        aria-expanded={open}
        aria-controls={popId}
        aria-label={`Token usage: ${sessionTokens.toLocaleString()} this session`}
        onClick={() => setOpen((o) => !o)}
      >
        <MeterGlyph />
        <span className="meter-label">Tokens</span>
        {/* Keyed by the value so the tick animation replays whenever usage changes. */}
        <span
          key={sessionTokens}
          className={`meter-value${sessionTokens > 0 ? ' is-tick' : ''}`}
        >
          {tracker.formattedSession}
        </span>
      </button>

      {open && (
        <div className="meter-pop" id={popId} role="region" aria-label="Token usage">
          <p className="meter-pop-title">Usage</p>

          <dl className="meter-ledger">
            <div>
              <dt>This session</dt>
              <dd className="meter-leader" aria-hidden="true" />
              <dd>{sessionTokens.toLocaleString()}</dd>
            </div>
            <div>
              <dt>All time</dt>
              <dd className="meter-leader" aria-hidden="true" />
              <dd>{lifetimeTokens.toLocaleString()}</dd>
            </div>
          </dl>

          {split > 0 && (
            <div className="meter-split">
              <div className="meter-split-bar" role="img" aria-label={`Input ${inputPct}%, output ${100 - inputPct}%`}>
                <i style={{ width: `${inputPct}%` }} />
              </div>
              <div className="meter-split-legend">
                <span>
                  <b className="dot is-in" /> Input {sessionInput.toLocaleString()}
                </span>
                <span>
                  <b className="dot is-out" /> Output {sessionOutput.toLocaleString()}
                </span>
              </div>
            </div>
          )}

          <p className="meter-note">
            Counted from the usage the API reports after each request. The all-time total is stored
            in this browser.
          </p>
        </div>
      )}
    </div>
  );
}
```

### 3.4 `apps/web/src/hooks/useTokenTracker.ts`

Backward compatible: every previous return field is still there.

```ts
// apps/web/src/hooks/useTokenTracker.ts
import { useEffect, useState } from 'react';
import type { TokenUsage } from 'api-types';

const LIFETIME_TOKENS_KEY = 'ug_lifetime_tokens';

// The API reports usage under different names depending on the provider wrapper.
// Trim these lists to the real field names in `TokenUsage` once you've checked api-types.
const INPUT_KEYS = ['input_tokens', 'prompt_tokens', 'prompt_token_count'];
const OUTPUT_KEYS = ['output_tokens', 'completion_tokens', 'candidates_token_count'];

function pick(usage: unknown, keys: string[]): number {
  const record = (usage ?? {}) as Record<string, unknown>;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'number' && Number.isFinite(value)) return value;
  }
  return 0;
}

export function formatCount(tokens: number): string {
  if (tokens < 1000) return tokens.toString();
  if (tokens < 10_000) return `${(tokens / 1000).toFixed(1)}k`;
  return `${Math.round(tokens / 1000)}k`;
}

export function useTokenTracker() {
  const [sessionTokens, setSessionTokens] = useState(0);
  const [sessionInput, setSessionInput] = useState(0);
  const [sessionOutput, setSessionOutput] = useState(0);
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
      const usage = (e as CustomEvent<TokenUsage | { total_tokens?: number }>).detail;
      const input = pick(usage, INPUT_KEYS);
      const output = pick(usage, OUTPUT_KEYS);
      const count = usage?.total_tokens ?? input + output;
      if (count > 0) {
        setSessionTokens((prev) => prev + count);
        setSessionInput((prev) => prev + input);
        setSessionOutput((prev) => prev + output);
        setLifetimeTokens((prev) => {
          const next = prev + count;
          try {
            localStorage.setItem(LIFETIME_TOKENS_KEY, next.toString());
          } catch {
            // Storage quota or privacy mode: ignore
          }
          return next;
        });
      }
    }

    window.addEventListener('ug:token-usage', handleTokenUsage);
    return () => window.removeEventListener('ug:token-usage', handleTokenUsage);
  }, []);

  return {
    sessionTokens,
    lifetimeTokens,
    sessionInput,
    sessionOutput,
    formattedSession: formatCount(sessionTokens),
    formattedLifetime: formatCount(lifetimeTokens),
  };
}

export type TokenTracker = ReturnType<typeof useTokenTracker>;
```

---

## 4. CSS

Append to `App.css` (or save as `apps/web/src/sprint3.css` and import it from `main.tsx` after `App.css`, so these rules win over the old `.saved-btn` styles).

```css
/* apps/web/src/sprint3.css  (or append to App.css)
   Replaces: "Token Pill & Access Button", "Access Gate Modal" and "Demo Product Picker" blocks.
   Uses only existing tokens: --ink, --ink-2, --ink-3, --card, --line, --tint, --rec, --hook, --concept, --cta,
   --font-display, --font-body. */

@keyframes gateSpin { to { rotate: 360deg; } }
@keyframes gateFade { from { opacity: 0; } }
@keyframes gateRise { from { opacity: 0; transform: translateY(18px) scale(0.985); } }
@keyframes gateIn { from { opacity: 0; transform: translateY(10px); } }
@keyframes gateShake { 20% { transform: translateX(-7px); } 45% { transform: translateX(6px); } 70% { transform: translateX(-3px); } }
@keyframes stampIn { from { opacity: 0; transform: rotate(-10deg) scale(1.9); } to { opacity: 0.92; transform: rotate(-10deg) scale(1); } }
@keyframes recBlink { 50% { opacity: 0.25; } }
@keyframes popIn { from { opacity: 0; transform: translateY(-4px); } }
@keyframes shimmer { to { background-position: -200% 0; } }
.gate-spin { animation: gateSpin 0.8s linear infinite; }

/* =====================================================================
   Masthead controls: one shared look for Tokens / Access / Saved scripts
   ===================================================================== */
.masthead-actions { display: flex; align-items: center; gap: 8px; }
.meter-btn,
.access-btn,
.saved-btn {
  display: inline-flex; align-items: center; gap: 8px; height: 36px; padding: 0 12px;
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  color: var(--ink); font: 600 0.8125rem/1 var(--font-body); cursor: pointer;
  transition: border-color 0.15s, background-color 0.15s;
}
.meter-btn:hover, .access-btn:hover, .saved-btn:hover, .meter-btn.is-open { border-color: var(--ink); }

/* ---------- Token meter ---------- */
.meter { position: relative; }
.meter-glyph { fill: currentColor; color: var(--ink-2); }
.meter-label { color: var(--ink-2); font-weight: 500; }
.meter-value { min-width: 2ch; margin-right: -4px; padding: 3px 6px; border-radius: 6px; font-variant-numeric: tabular-nums; text-align: right; }
.meter-value.is-tick { animation: meterTick 0.8s ease-out; }
@keyframes meterTick { from { background: var(--ink); color: #fff; } }

.meter-pop {
  position: absolute; right: 0; top: calc(100% + 8px); z-index: 60; width: 292px; padding: 16px 18px 14px;
  color: var(--ink); background: var(--card); border: 1px solid var(--ink); border-radius: 14px;
  font: 400 0.875rem/1.4 var(--font-body); /* the masthead may set a display font; reset it here */
  box-shadow: 0 18px 40px -12px rgba(20, 24, 26, 0.3); animation: popIn 0.16s ease-out;
}
.meter-pop-title { margin: 0 0 12px; padding-bottom: 10px; border-bottom: 3px double var(--ink); font: 600 1.0625rem/1 var(--font-display); letter-spacing: -0.01em; }
.meter-ledger { margin: 0; }
.meter-ledger > div { display: flex; align-items: baseline; gap: 8px; padding: 5px 0; }
.meter-ledger dt { color: var(--ink-2); font-size: 0.875rem; }
.meter-ledger dd { margin: 0; }
.meter-leader { flex: 1; min-width: 12px; border-bottom: 1.5px dotted var(--ink-3); transform: translateY(-3px); }
.meter-ledger dd:last-child { font: 600 1.0625rem/1 var(--font-body); font-variant-numeric: tabular-nums; }
.meter-split { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--line); }
.meter-split-bar { height: 6px; overflow: hidden; border-radius: 3px; background: #c9d1cd; }
.meter-split-bar i { display: block; height: 100%; background: var(--ink); }
.meter-split-legend { display: flex; justify-content: space-between; margin-top: 8px; color: var(--ink-2); font-size: 0.75rem; font-variant-numeric: tabular-nums; }
.meter-split-legend .dot { display: inline-block; width: 7px; height: 7px; margin-right: 4px; border-radius: 50%; }
.dot.is-in { background: var(--ink); }
.dot.is-out { background: #c9d1cd; }
.meter-note { margin: 12px 0 0; color: var(--ink-3); font-size: 0.75rem; line-height: 1.45; }

/* =====================================================================
   Access gate
   ===================================================================== */
.gate-backdrop {
  position: fixed; inset: 0; z-index: 100; display: flex; padding: 24px; overflow: auto;
  background:
    radial-gradient(circle at 1px 1px, rgba(255, 255, 255, 0.075) 1px, transparent 1.4px) 0 0 / 16px 16px,
    radial-gradient(ellipse at 50% 40%, transparent 35%, rgba(0, 0, 0, 0.55)),
    #0b0f11;
  animation: gateFade 0.35s ease-out;
}
.gate-backdrop::before {
  content: ''; position: fixed; inset: 0; pointer-events: none; opacity: 0.16;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .6 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
}
.gate {
  position: relative; display: grid; grid-template-columns: minmax(0, 1.02fr) minmax(0, 1fr);
  width: 100%; max-width: 960px; margin: auto; overflow: hidden;
  background: var(--card); border-radius: 20px;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.09), 0 50px 90px -24px rgba(0, 0, 0, 0.7);
  animation: gateRise 0.55s cubic-bezier(0.2, 0.7, 0.2, 1);
}

/* ---------- Cover ---------- */
.gate-cover {
  position: relative; display: flex; flex-direction: column; gap: 18px; min-height: 600px; padding: 58px 44px 34px;
  background: #14181a; color: #fff; isolation: isolate; overflow: hidden;
}
.gate-cover::before {
  content: ''; position: absolute; inset: 0; z-index: -1;
  background: radial-gradient(circle at 1px 1px, rgba(255, 255, 255, 0.07) 1px, transparent 1.4px) 0 0 / 14px 14px;
  -webkit-mask-image: linear-gradient(180deg, #000, transparent 65%); mask-image: linear-gradient(180deg, #000, transparent 65%);
}
.gate-slate {
  position: absolute; top: 0; left: 0; right: 0; height: 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.25);
  background: repeating-linear-gradient(-55deg, #f1efe8 0 14px, #14181a 14px 28px);
}
.gate-brand { display: flex; align-items: center; gap: 10px; }
.gate-wordmark { font: 600 1.25rem/1 var(--font-display); letter-spacing: -0.01em; }
.gate-tag { margin-left: auto; padding: 5px 10px; border: 1px solid rgba(255, 255, 255, 0.28); border-radius: 999px; color: rgba(255, 255, 255, 0.78); font: 500 0.6875rem/1 var(--font-body); letter-spacing: 0.06em; }
.gate-headline { margin: 18px 0 0; font: 500 clamp(2.1rem, 3.6vw, 3rem)/1.02 var(--font-display); letter-spacing: -0.028em; }
.gate-headline em { color: rgba(255, 255, 255, 0.55); font-style: italic; }
.gate-lede { max-width: 36ch; margin: 0; color: rgba(255, 255, 255, 0.64); font-size: 0.9375rem; line-height: 1.55; }

/* Demo video poster */
.gate-video { color: inherit; text-decoration: none; }
.gate-video.is-poster {
  display: block; margin-top: auto; overflow: hidden; color: #fff;
  background: #0b0e10; border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 14px;
  transition: border-color 0.2s, transform 0.2s;
}
.gate-video.is-poster:hover { border-color: rgba(255, 255, 255, 0.5); transform: translateY(-2px); }
.vp-frame {
  position: relative; display: block; aspect-ratio: 16 / 9;
  background:
    linear-gradient(90deg, transparent calc(33.33% - 0.5px), rgba(255, 255, 255, 0.09) calc(33.33% - 0.5px) calc(33.33% + 0.5px), transparent calc(33.33% + 0.5px) calc(66.66% - 0.5px), rgba(255, 255, 255, 0.09) calc(66.66% - 0.5px) calc(66.66% + 0.5px), transparent calc(66.66% + 0.5px)),
    linear-gradient(0deg, transparent calc(33.33% - 0.5px), rgba(255, 255, 255, 0.09) calc(33.33% - 0.5px) calc(33.33% + 0.5px), transparent calc(33.33% + 0.5px) calc(66.66% - 0.5px), rgba(255, 255, 255, 0.09) calc(66.66% - 0.5px) calc(66.66% + 0.5px), transparent calc(66.66% + 0.5px)),
    linear-gradient(160deg, #222b2f, #0d1113);
}
.vp-rec { position: absolute; left: 14px; top: 12px; display: inline-flex; align-items: center; gap: 6px; font: 700 0.6875rem/1 var(--font-body); letter-spacing: 0.1em; }
.vp-rec .rec-dot { width: 8px; height: 8px; animation: recBlink 1.4s ease-in-out infinite; }
.vp-tc { position: absolute; right: 14px; top: 12px; color: rgba(255, 255, 255, 0.6); font: 500 0.6875rem/1 var(--font-body); font-variant-numeric: tabular-nums; letter-spacing: 0.06em; }
.vp-play {
  position: absolute; left: 50%; top: 50%; display: grid; place-items: center; width: 58px; height: 58px; translate: -50% -50%;
  color: var(--ink); background: #fff; border-radius: 50%; transition: transform 0.2s;
}
.vp-play::after { content: ''; position: absolute; inset: -9px; border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 50%; transition: inset 0.25s, opacity 0.25s; }
.gate-video.is-poster:hover .vp-play { transform: scale(1.07); }
.gate-video.is-poster:hover .vp-play::after { inset: -14px; opacity: 0; }
.vp-play svg { margin-left: 2px; }
.vp-bar { position: absolute; left: 14px; right: 14px; bottom: 12px; display: flex; gap: 3px; height: 4px; }
.vp-bar i { display: block; border-radius: 2px; background: var(--kind); opacity: 0.85; }
.vp-bar i:nth-child(1) { flex: 3; --kind: var(--hook); }
.vp-bar i:nth-child(2) { flex: 8; --kind: var(--concept); }
.vp-bar i:nth-child(3) { flex: 2; --kind: var(--cta); }
.vp-caption { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-top: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.875rem; }
.vp-caption strong { font-weight: 600; }

/* ---------- Panel ---------- */
.gate-panel { position: relative; display: flex; flex-direction: column; padding: 40px 48px 28px; background: var(--card); }
.gate-close { position: absolute; top: 14px; right: 14px; display: grid; place-items: center; width: 32px; height: 32px; padding: 0; color: var(--ink-3); background: transparent; border: 0; border-radius: 50%; cursor: pointer; transition: background-color 0.15s, color 0.15s; }
.gate-close:hover { color: var(--ink); background: var(--tint); }

.gate-tabs { position: relative; display: grid; grid-template-columns: 1fr 1fr; border-bottom: 1px solid var(--line); }
.gate-tabs button { padding: 0 0 12px; color: var(--ink-3); background: none; border: 0; font: 600 0.875rem/1 var(--font-body); text-align: left; cursor: pointer; transition: color 0.15s; }
.gate-tabs button:hover { color: var(--ink-2); }
.gate-tabs button[aria-selected='true'] { color: var(--ink); }
.gate-tabs::after { content: ''; position: absolute; left: 0; bottom: -1px; width: 50%; height: 2px; background: var(--ink); transition: transform 0.35s cubic-bezier(0.2, 0.7, 0.2, 1); }
.gate-tabs[data-mode='request_access']::after { transform: translateX(100%); }

.gate-view { margin: auto 0; padding: 30px 0 10px; animation: gateIn 0.34s cubic-bezier(0.2, 0.7, 0.2, 1); }
.gate-title { margin: 0; font: 500 2.1rem/1.06 var(--font-display); letter-spacing: -0.022em; }
.gate-sub { max-width: 40ch; margin: 10px 0 0; color: var(--ink-2); font-size: 0.9375rem; line-height: 1.55; }
.gate-sub strong { color: var(--ink); font-weight: 600; }
.gate-form { display: grid; gap: 18px; margin-top: 26px; }

/* Admit-one ticket: two masked layers (border + paper) carve matching notches */
.gate-ticket-wrap { filter: drop-shadow(0 8px 12px rgba(20, 24, 26, 0.1)); transition: filter 0.2s; }
.gate-ticket-wrap:focus-within { filter: drop-shadow(0 0 6px rgba(2, 132, 199, 0.5)); }
.gate-ticket-wrap.is-shaking { animation: gateShake 0.46s; }
.gate-ticket {
  --stub: 104px; --r: 9px; --b: 1.5px;
  padding: var(--b); border-radius: 12px; background: var(--ink); transition: background-color 0.2s;
  -webkit-mask:
    radial-gradient(circle var(--r) at calc(var(--stub) + var(--b)) 0, #0000 98%, #000) top / 100% 51% no-repeat,
    radial-gradient(circle var(--r) at calc(var(--stub) + var(--b)) 100%, #0000 98%, #000) bottom / 100% 51% no-repeat;
  mask:
    radial-gradient(circle var(--r) at calc(var(--stub) + var(--b)) 0, #0000 98%, #000) top / 100% 51% no-repeat,
    radial-gradient(circle var(--r) at calc(var(--stub) + var(--b)) 100%, #0000 98%, #000) bottom / 100% 51% no-repeat;
}
.gate-ticket.has-error { background: var(--rec); }
.ticket-in {
  display: grid; grid-template-columns: var(--stub) 1fr; min-height: 78px; background: #fffdf8; border-radius: calc(12px - var(--b));
  -webkit-mask:
    radial-gradient(circle calc(var(--r) + var(--b)) at var(--stub) calc(var(--b) * -1), #0000 98%, #000) top / 100% 51% no-repeat,
    radial-gradient(circle calc(var(--r) + var(--b)) at var(--stub) calc(100% + var(--b)), #0000 98%, #000) bottom / 100% 51% no-repeat;
  mask:
    radial-gradient(circle calc(var(--r) + var(--b)) at var(--stub) calc(var(--b) * -1), #0000 98%, #000) top / 100% 51% no-repeat,
    radial-gradient(circle calc(var(--r) + var(--b)) at var(--stub) calc(100% + var(--b)), #0000 98%, #000) bottom / 100% 51% no-repeat;
}
.ticket-stub { position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 7px; color: var(--ink-2); background: #f2efe6; font: 700 0.625rem/1.2 var(--font-body); letter-spacing: 0.16em; text-align: center; text-transform: uppercase; }
.ticket-stub svg { color: var(--ink); }
.ticket-stub::after { content: ''; position: absolute; right: -1px; top: 15px; bottom: 15px; border-left: 2px dotted rgba(20, 24, 26, 0.5); }
.ticket-body { display: grid; align-content: center; gap: 5px; padding: 12px 18px; }
.ticket-body label { color: var(--ink-3); font: 600 0.6875rem/1 var(--font-body); letter-spacing: 0.1em; text-transform: uppercase; }
.ticket-body input { width: 100%; padding: 0; color: var(--ink); background: transparent; border: 0; outline: 0; font: 600 1.4rem/1.25 ui-monospace, 'SF Mono', Menlo, Consolas, monospace; letter-spacing: 0.06em; text-transform: uppercase; }
.ticket-body input::placeholder { color: var(--ink-3); opacity: 0.5; }

.gate-error { display: flex; align-items: flex-start; gap: 8px; margin: 0; color: #9f1239; font-size: 0.8125rem; font-weight: 500; line-height: 1.4; }
.gate-error svg { flex: none; margin-top: 1px; }
.gate-view > .gate-error { margin-top: 18px; }

.gate-submit {
  display: flex; align-items: center; justify-content: space-between; width: 100%; height: 52px; padding: 0 20px;
  color: #fff; background: var(--ink); border: 0; border-radius: 12px; font: 600 0.9375rem/1 var(--font-body); cursor: pointer;
  box-shadow: 0 12px 22px -10px rgba(20, 24, 26, 0.6); transition: transform 0.15s, background-color 0.15s, opacity 0.15s;
}
.gate-submit svg { transition: transform 0.2s; }
.gate-submit:hover:not(:disabled) { background: #000; transform: translateY(-1px); }
.gate-submit:hover:not(:disabled) svg { transform: translateX(3px); }
.gate-submit:disabled:not([aria-busy='true']) { opacity: 0.32; cursor: not-allowed; box-shadow: none; }
.gate-submit[aria-busy='true'] { cursor: progress; }
.gate-submit.is-ghost { color: var(--ink); background: transparent; box-shadow: none; outline: 1.5px solid var(--ink); outline-offset: -1.5px; }
.gate-submit.is-ghost:hover:not(:disabled) { color: #fff; }

.gate-field { display: grid; gap: 4px; }
.gate-field label { color: var(--ink-2); font: 600 0.75rem/1 var(--font-body); letter-spacing: 0.02em; }
.gate-field input { height: 42px; padding: 0 2px; color: var(--ink); background: transparent; border: 0; border-bottom: 1.5px solid var(--line); border-radius: 0; outline: 0; font: 500 1.0625rem/1 var(--font-body); transition: border-color 0.15s, box-shadow 0.15s; }
.gate-field input::placeholder { color: var(--ink-3); opacity: 0.55; }
.gate-field input:hover { border-bottom-color: var(--ink-3); }
.gate-field input:focus { border-bottom-color: var(--ink); box-shadow: 0 1px 0 0 var(--ink); }
.gate-field + .gate-field { margin-top: 2px; }

.gate-switch { margin: 20px 0 0; color: var(--ink-2); font-size: 0.875rem; }
.gate-link { padding: 0; color: var(--ink); background: none; border: 0; font: inherit; font-weight: 600; text-decoration: underline; text-decoration-thickness: 1.5px; text-underline-offset: 3px; cursor: pointer; }
.gate-link:hover { text-decoration-color: var(--rec); }

.gate-done { display: grid; justify-items: start; }
.gate-stamp { position: relative; display: grid; place-items: center; width: 116px; height: 116px; margin: 4px 0 22px; color: var(--rec); border: 3px solid currentColor; border-radius: 50%; transform: rotate(-10deg); opacity: 0.92; mix-blend-mode: multiply; animation: stampIn 0.55s cubic-bezier(0.2, 1.3, 0.4, 1) both; }
.gate-stamp::before { content: ''; position: absolute; inset: 5px; border: 1px solid currentColor; border-radius: 50%; }
.gate-stamp span { padding: 5px 0; border-block: 1.5px solid currentColor; font: 700 0.8125rem/1 var(--font-display); letter-spacing: 0.2em; text-transform: uppercase; }
.gate-done .gate-stamp { margin-top: 26px; }
.gate-done .gate-submit { margin-top: 26px; }

.gate-foot { display: none; margin-top: 22px; }
.gate-video.is-inline { display: inline-flex; align-items: center; gap: 8px; padding: 9px 14px; color: var(--ink); border: 1px solid var(--line); border-radius: 999px; font-size: 0.875rem; font-weight: 600; }

@media (max-width: 860px) {
  .gate-backdrop { padding: 12px; }
  .gate { grid-template-columns: 1fr; max-width: 480px; }
  .gate-cover { min-height: 0; gap: 12px; padding: 40px 24px 26px; }
  .gate-headline { margin-top: 6px; font-size: 1.9rem; }
  .gate-lede, .gate-video.is-poster { display: none; }
  .gate-panel { padding: 28px 24px 24px; }
  .gate-title { font-size: 1.75rem; }
  .gate-foot { display: block; }
  .gate-ticket { --stub: 88px; }
}

/* =====================================================================
   Sample shelf (demo product picker)
   ===================================================================== */
.shelf { position: relative; margin-bottom: 24px; }
.shelf-bar { display: flex; align-items: center; gap: 16px; width: 100%; padding: 10px 16px 10px 14px; color: var(--ink); background: var(--tint); border: 1px solid var(--line); border-radius: 14px; text-align: left; cursor: pointer; transition: background-color 0.15s, border-color 0.15s; }
.shelf-bar:hover, .shelf-bar.is-open { background: #fff; border-color: var(--ink); }
.shelf-stack { display: flex; flex: none; align-items: center; padding-left: 10px; }
.shelf-thumb { width: 36px; height: 46px; margin-left: -10px; object-fit: cover; background: var(--line); border: 2px solid var(--tint); border-radius: 6px; box-shadow: 0 2px 6px rgba(20, 24, 26, 0.2); transform: rotate(calc((var(--i, 0) - 1.5) * 4deg)); transition: transform 0.25s, border-color 0.15s; }
.shelf-bar:hover .shelf-thumb, .shelf-bar.is-open .shelf-thumb { border-color: #fff; transform: rotate(calc((var(--i, 0) - 1.5) * 7deg)) translateY(-2px); }
.shelf-thumb.is-main { width: 44px; height: 56px; margin-left: 0; transform: none !important; }
.shelf-copy { display: grid; flex: 1; gap: 3px; min-width: 0; }
.shelf-copy strong { overflow: hidden; font: 600 1rem/1.2 var(--font-display); letter-spacing: -0.005em; text-overflow: ellipsis; white-space: nowrap; }
.shelf-copy span { color: var(--ink-2); font-size: 0.8125rem; }
.shelf-cta { display: inline-flex; flex: none; align-items: center; gap: 6px; font: 600 0.8125rem/1 var(--font-body); }
.shelf-cta svg { transition: transform 0.2s; }
.shelf-bar.is-open .shelf-cta svg { transform: rotate(180deg); }

.shelf-sheet { position: absolute; left: 0; right: 0; top: calc(100% + 10px); z-index: 40; padding: 14px 0 4px; background: var(--card); border: 1px solid var(--ink); border-radius: 16px; box-shadow: 0 30px 60px -18px rgba(20, 24, 26, 0.4); animation: popIn 0.2s ease-out; }
.shelf-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 18px; border-bottom: 1px solid var(--line); }
.shelf-tabs { display: flex; gap: 20px; overflow-x: auto; }
.shelf-tab { margin-bottom: -1px; padding: 6px 0 10px; color: var(--ink-3); background: none; border: 0; border-bottom: 2px solid transparent; font: 600 0.8125rem/1 var(--font-body); white-space: nowrap; cursor: pointer; transition: color 0.15s; }
.shelf-tab:hover { color: var(--ink); }
.shelf-tab.is-active { color: var(--ink); border-bottom-color: var(--ink); }
.shelf-arrows { display: flex; gap: 6px; padding-bottom: 8px; }
.shelf-arrows button { display: grid; place-items: center; width: 30px; height: 30px; padding: 0; color: var(--ink); background: #fff; border: 1px solid var(--line); border-radius: 50%; cursor: pointer; transition: border-color 0.15s; }
.shelf-arrows button:hover { border-color: var(--ink); }

.shelf-rail { display: flex; gap: 14px; padding: 16px 18px 16px; overflow-x: auto; scroll-snap-type: x proximity; scroll-padding-inline: 18px; scrollbar-width: thin; }
.shelf-card { display: grid; flex: 0 0 164px; gap: 2px; align-content: start; padding: 0; color: var(--ink); background: none; border: 0; text-align: left; cursor: pointer; scroll-snap-align: start; }
.shelf-photo { position: relative; display: block; aspect-ratio: 4 / 5; margin-bottom: 8px; overflow: hidden; background: var(--tint); border-radius: 12px; box-shadow: inset 0 0 0 1px rgba(20, 24, 26, 0.08); transition: box-shadow 0.2s; }
.shelf-photo img { display: block; width: 100%; height: 100%; object-fit: cover; transition: transform 0.4s; }
.shelf-card:hover .shelf-photo { box-shadow: 0 12px 24px -10px rgba(20, 24, 26, 0.5); }
.shelf-card:hover .shelf-photo img { transform: scale(1.04); }
.shelf-card.is-selected .shelf-photo { outline: 2px solid var(--ink); outline-offset: 3px; }
.shelf-card:focus-visible { outline: none; }
.shelf-card:focus-visible .shelf-photo { outline: 2px solid var(--concept); outline-offset: 3px; }
.shelf-name { font: 600 0.9375rem/1.25 var(--font-display); letter-spacing: -0.005em; }
.shelf-meta { color: var(--ink-3); font-size: 0.75rem; }
.shelf-lang { position: absolute; left: 8px; top: 8px; padding: 4px 7px; color: var(--ink); background: rgba(255, 255, 255, 0.92); border-radius: 6px; font: 700 0.6875rem/1 var(--font-body); letter-spacing: 0.05em; -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px); }
.shelf-lang.is-bn { font-size: 0.75rem; letter-spacing: 0; }
.shelf-check { position: absolute; right: 8px; top: 8px; display: grid; place-items: center; width: 22px; height: 22px; color: #fff; background: var(--ink); border-radius: 50%; }
.shelf-card.is-skeleton { cursor: default; }
.shelf-card.is-skeleton .shelf-photo { background: linear-gradient(90deg, var(--tint) 30%, #fff 50%, var(--tint) 70%) 0 0 / 200% 100%; animation: shimmer 1.4s linear infinite; }
.shelf-card.is-skeleton .shelf-name { color: transparent; background: var(--tint); border-radius: 4px; }
.shelf-error { margin: 0; padding: 12px 18px 0; color: #9f1239; font-size: 0.8125rem; }

@media (max-width: 640px) {
  .shelf-card { flex-basis: 140px; }
  .shelf-arrows { display: none; }
  .shelf-cta { display: none; }
}
```

---

## 5. `App.tsx` changes

Import the new component and use the tracker object:

```tsx
import { TokenMeter } from './components/TokenMeter';
import { useTokenTracker } from './hooks/useTokenTracker';

// inside App():
const tokens = useTokenTracker();
```

Replace the token pill in the masthead. The rest of the actions row stays as it is:

```tsx
<div className="masthead-actions">
  <TokenMeter tracker={tokens} />

  <button type="button" className="access-btn" onClick={() => setAccessModalOpen(true)} title="Manage demo access key">
    <IconKey size={15} aria-hidden="true" />
    <span>Access</span>
  </button>

  <button type="button" className="saved-btn" onClick={() => setDrawerOpen(true)}>
    <IconBookmark size={16} aria-hidden="true" />
    <span>Saved scripts</span>
    {savedScripts.length > 0 && <span className="saved-count-pill">{savedScripts.length}</span>}
  </button>
</div>
```

The `AccessGateModal` mount at the bottom of `App.tsx` does not change.

If your `.masthead` rule sets the display font on the whole header (as the brand wordmark suggests), that is fine: `.meter-pop` and the three masthead buttons reset to the body font explicitly.

---

## 6. Verification checklist

1. Fresh profile (no `ug_access_code`): the gate opens as the first view, no close button, Esc does nothing, Tab never leaves the card.
2. Wrong code: the ticket border turns red, shakes once, and the error appears under it with `role="alert"`. A right code unlocks and writes `ug_access_code`.
3. "Request access" tab: the underline slides, the form validates, success shows the stamp and "Back to code entry" returns to the first tab.
4. Click **View demo video** with `DEMO_VIDEO_URL = ''`: nothing happens (no `#` jump, no navigation). With a URL set, it opens in a new tab.
5. Access button in the masthead while unlocked: the gate opens with a close button and Esc works; focus returns to the Access button afterwards.
6. Width 390px: cover shrinks to wordmark plus headline, the poster is hidden, and the text "View demo video" pill appears under the form.
7. Sample shelf: opening it does not move the form; outside click and Esc close it; picking a card loads the product, fills the form (existing `handleSelectDemo`) and the bar shows the product with "Change".
8. Dispatch `window.dispatchEvent(new CustomEvent('ug:token-usage', { detail: { total_tokens: 1200 } }))`: the meter figure ticks and the popover shows session and all-time totals.
