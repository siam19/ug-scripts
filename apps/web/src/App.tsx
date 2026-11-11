// apps/web/src/App.tsx
import { useEffect, useRef, useState } from 'react';
import './App.css';
import { IconBookmark, IconKey } from '@tabler/icons-react';
import { ProductForm } from './components/ProductForm';
import { LoadingState } from './components/LoadingState';
import { ResultsView } from './components/ResultsView';
import { ErrorBanner } from './components/ErrorBanner';
import { SavedScriptsDrawer } from './components/SavedScriptsDrawer';
import { AccessGateModal } from './components/AccessGateModal';
import { TokenMeter } from './components/TokenMeter';
import { useGenerateScript } from './hooks/useGenerateScript';
import { useSavedScripts } from './state/saved-scripts';
import { useTokenTracker } from './hooks/useTokenTracker';
import { INITIAL_VALUES } from './types/form';
import type { FormValues } from './types/form';

export default function App() {
  // Form values live here, so they survive loading, errors and retries.
  const [values, setValues] = useState<FormValues>(INITIAL_VALUES);
  const { status, data, error, runId, generate, retry, clearError } = useGenerateScript();
  const { savedScripts, remove } = useSavedScripts();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [accessModalOpen, setAccessModalOpen] = useState(() => !localStorage.getItem('ug_access_code'));
  const [accessInitialMode, setAccessInitialMode] = useState<'enter_code' | 'request_access'>('enter_code');
  const tokens = useTokenTracker();
  const outputRef = useRef<HTMLElement>(null);

  useEffect(() => {
    function handleUnauthorized() {
      localStorage.removeItem('ug_access_code');
      setAccessInitialMode('enter_code');
      setAccessModalOpen(true);
    }
    window.addEventListener('ug:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('ug:unauthorized', handleUnauthorized);
  }, []);

  function patch(update: Partial<FormValues>) {
    setValues((v) => ({ ...v, ...update }));
  }

  function scrollToBottom() {
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const runScroll = () => {
      window.scrollTo({
        top: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight),
        behavior: smooth ? 'smooth' : 'auto',
      });
    };
    requestAnimationFrame(runScroll);
    setTimeout(runScroll, 80);
    setTimeout(runScroll, 240);
  }

  function handleSubmit() {
    void generate(values);
    scrollToBottom();
  }

  function handleRetry() {
    retry();
    scrollToBottom();
  }

  return (
    <div className="shell">
      <header className="masthead">
        <div className="masthead-brand">
          <span className="rec-dot" aria-hidden="true" />
          <span className="masthead-title">Script Assistant</span>
        </div>

        <div className="masthead-actions">
          <TokenMeter tracker={tokens} />

          <button
            type="button"
            className="access-btn"
            onClick={() => {
              setAccessInitialMode('request_access');
              setAccessModalOpen(true);
            }}
            title="Manage demo access key"
            aria-label="Manage demo access key"
          >
            <IconKey size={15} aria-hidden="true" />
            <span className="access-btn-label">Access</span>
          </button>

          <button
            type="button"
            className="saved-btn"
            onClick={() => setDrawerOpen(true)}
            title={`Saved scripts (${savedScripts.length})`}
            aria-label={`Saved scripts (${savedScripts.length})`}
          >
            <IconBookmark size={16} aria-hidden="true" />
            <span className="saved-btn-label">Saved</span>
            <span className="saved-btn-full">&nbsp;scripts</span>
            {savedScripts.length > 0 && (
              <span className="saved-count-pill">{savedScripts.length}</span>
            )}
          </button>
        </div>
      </header>

      <section className="hero">
        <h1>UG-Scripts</h1>
        <p>
          Describe the product, add its photo, and get three customer segments with a
          phone-ready UGC ad script for each.
        </p>
      </section>

      <ProductForm
        values={values}
        onChange={patch}
        onSubmit={handleSubmit}
        submitting={status === 'loading' || status === 'streaming'}
      />

      <section ref={outputRef} className="output" aria-label="Generated scripts">
        {status === 'idle' && (
          <div className="empty">
            <h2>Your scripts will appear here</h2>
            <p>
              Fill in the product details and add a photo. You will get 3 customer
              segments, one script for each, and 3 reasons per script.
            </p>
          </div>
        )}

        {status === 'loading' && !data && <LoadingState />}

        {status === 'error' && error && (
          <ErrorBanner error={error} onRetry={handleRetry} onDismiss={clearError} />
        )}

        {data && (
          <ResultsView
            key={runId}
            data={data}
            isStreaming={status === 'streaming'}
            meta={{
              name: values.name,
              market: values.market,
              language: values.language,
              script_format: values.script_format,
            }}
          />
        )}
      </section>

      <SavedScriptsDrawer
        open={drawerOpen}
        scripts={savedScripts}
        onClose={() => setDrawerOpen(false)}
        onRemove={remove}
      />

      <AccessGateModal
        open={accessModalOpen}
        initialMode={accessInitialMode}
        onUnlocked={() => setAccessModalOpen(false)}
        onClose={localStorage.getItem('ug_access_code') ? () => setAccessModalOpen(false) : undefined}
      />
    </div>
  );
}
