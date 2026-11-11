// apps/web/src/components/AccessGateModal.tsx
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent, RefObject } from 'react';
import {
  IconAlertCircle,
  IconArrowRight,
  IconArrowUpRight,
  IconCheck,
  IconLoader2,
  IconLock,
  IconSend,
  IconX,
} from '@tabler/icons-react';
import type { VerifyAccessResponse } from 'api-types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

/**
 * Demo video URL (YouTube, Loom, Vimeo, hosted .mp4, etc.).
 * When empty, clicking the button does nothing.
 */
export const DEMO_VIDEO_URL = '';

interface Props {
  open: boolean;
  initialMode?: Mode;
  onUnlocked: (data: VerifyAccessResponse, code: string) => void;
  onClose?: () => void;
}

type Mode = 'enter_code' | 'request_access';

/** Focus trap, Esc-to-close (only when closable), scroll lock, and focus restore. */
function useDialogA11y(open: boolean, ref: RefObject<HTMLElement | null>, onClose?: () => void) {
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

/** Standard shadcn-style OTP slot input (5 characters) */
function ShadcnOtpInput({
  value,
  onChange,
  error,
  inputRef,
  id,
}: {
  value: string;
  onChange: (v: string) => void;
  error?: boolean;
  inputRef?: RefObject<HTMLInputElement | null>;
  id?: string;
}) {
  const [focused, setFocused] = useState(false);
  const internalRef = useRef<HTMLInputElement>(null);
  const ref = inputRef || internalRef;

  // 5-character alphanumeric access codes
  const clean = value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 5);

  return (
    <div
      className={`shadcn-otp-container${focused ? ' is-focused' : ''}${error ? ' has-error' : ''}`}
      onClick={() => ref.current?.focus()}
    >
      <input
        ref={ref}
        id={id}
        type="text"
        autoComplete="off"
        autoCapitalize="characters"
        spellCheck={false}
        value={clean}
        onChange={(e) => {
          const val = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 5);
          onChange(val);
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="shadcn-otp-native-input"
        maxLength={5}
      />

      <div className="shadcn-otp-slots" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => {
          const char = clean[i] || '';
          const isCurrent = focused && i === clean.length;

          return (
            <div
              key={i}
              className={`shadcn-otp-cell${isCurrent ? ' is-current' : ''}${char ? ' is-filled' : ''}`}
            >
              {char}
              {isCurrent && <span className="shadcn-otp-cursor" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function AccessGateModal({ open, initialMode = 'enter_code', onUnlocked, onClose }: Props) {
  const uid = useId();
  const id = (k: string) => `${uid}-${k}`;

  const [mode, setMode] = useState<Mode>(initialMode);
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
      setMode(initialMode);
      setErrorMsg(null);
      setRequestSubmitted(false);
    }
  }, [open, initialMode]);

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

  async function submitCode(rawCode: string) {
    const clean = rawCode.trim().toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 5);
    if (!clean || clean.length < 5 || verifying) return;

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
        fail(err.detail || 'Invalid or expired access code. Please check your code or request access.');
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

  function handleCodeChange(val: string) {
    setCode(val);
    setErrorMsg(null);
    if (val.length === 5) {
      codeRef.current?.blur();
      void submitCode(val);
    }
  }

  async function handleVerify(e: FormEvent) {
    e.preventDefault();
    await submitCode(code);
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

  return (
    <div className="gate-backdrop">
      <div
        ref={cardRef}
        className="gate-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby={id('title')}
      >
        {onClose && (
          <button type="button" className="gate-close" onClick={onClose} aria-label="Close">
            <IconX size={18} aria-hidden="true" />
          </button>
        )}

        <div className="gate-top-bar">
          <div className="gate-brand">
            <span className="gate-wordmark">UG-Scripts</span>
            <span className="gate-version">v0.4.1</span>
          </div>
        </div>

        {requestSubmitted ? (
          <div className="gate-success">
            <div className="gate-success-icon" aria-hidden="true">
              <IconCheck size={28} />
            </div>
            <h2 className="gate-title">Request received!</h2>
            <p className="gate-sub">
              Thank you, <strong>{name}</strong>. We received your request for <strong>{company}</strong> and will contact you via phone or WhatsApp with your code.
            </p>
            <button
              type="button"
              className="gate-submit is-ghost"
              onClick={() => switchMode('enter_code')}
            >
              <span>Back to code entry</span>
              <IconArrowRight size={18} aria-hidden="true" />
            </button>
          </div>
        ) : (
          <>
            <div className="gate-header">
              <h2 className="gate-title" id={id('title')}>
                <IconLock size={20} className="gate-title-lock" aria-hidden="true" />
                <span>{mode === 'enter_code' ? 'Private demo access' : 'Request an access code'}</span>
              </h2>
              <p className="gate-sub">
                {mode === 'enter_code'
                  ? 'This preview is invite-only. Enter your 5-character demo access code to unlock the script generator.'
                  : 'Fill in your details below. We will review and send you a 5-character demo access code.'}
              </p>
            </div>

            <div className="gate-tabs" role="tablist" aria-label="Access options">
              <button
                type="button"
                role="tab"
                id={id('tab-code')}
                aria-selected={mode === 'enter_code'}
                className={mode === 'enter_code' ? 'is-active' : ''}
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
                className={mode === 'request_access' ? 'is-active' : ''}
                tabIndex={mode === 'request_access' ? 0 : -1}
                onClick={() => switchMode('request_access')}
                onKeyDown={handleTabKey}
              >
                Request access
              </button>
            </div>

            <div className="gate-view">
              {mode === 'enter_code' ? (
                <>
                  <form className={`gate-form${shake ? ' is-shaking' : ''}`} onSubmit={handleVerify}>
                    <div className="gate-field">
                      <label htmlFor={id('code')}>Access Code</label>
                      <ShadcnOtpInput
                        id={id('code')}
                        inputRef={codeRef}
                        value={code}
                        onChange={handleCodeChange}
                        error={Boolean(errorMsg)}
                      />
                    </div>

                    {errorMsg && (
                      <p className="gate-error" role="alert">
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

                    <a
                      className="gate-demo-video-btn"
                      href={DEMO_VIDEO_URL || '#'}
                      target={DEMO_VIDEO_URL ? '_blank' : undefined}
                      rel="noopener noreferrer"
                      onClick={(e) => {
                        if (!DEMO_VIDEO_URL) e.preventDefault();
                      }}
                      title={DEMO_VIDEO_URL ? 'Watch preview video in new tab' : 'Demo video coming soon'}
                    >
                      <span>View demo video</span>
                      <IconArrowUpRight size={18} aria-hidden="true" />
                    </a>
                  </form>

                  <p className="gate-switch">
                    Don&rsquo;t have an access code?{' '}
                    <button type="button" className="gate-link" onClick={() => switchMode('request_access')}>
                      Request access
                    </button>
                  </p>
                </>
              ) : (
                <>
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
                        className="shadcn-input"
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
                        className="shadcn-input"
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
                        className="shadcn-input"
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

                    <a
                      className="gate-demo-video-btn"
                      href={DEMO_VIDEO_URL || '#'}
                      target={DEMO_VIDEO_URL ? '_blank' : undefined}
                      rel="noopener noreferrer"
                      onClick={(e) => {
                        if (!DEMO_VIDEO_URL) e.preventDefault();
                      }}
                      title={DEMO_VIDEO_URL ? 'Watch preview video in new tab' : 'Demo video coming soon'}
                    >
                      <span>View demo video</span>
                      <IconArrowUpRight size={18} aria-hidden="true" />
                    </a>
                  </form>

                  <p className="gate-switch">
                    Already have an access code?{' '}
                    <button type="button" className="gate-link" onClick={() => switchMode('enter_code')}>
                      Enter code
                    </button>
                  </p>
                </>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
