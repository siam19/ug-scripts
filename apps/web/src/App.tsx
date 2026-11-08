// apps/web/src/App.tsx
import { useRef, useState } from 'react';
import './App.css';
import { ProductForm } from './components/ProductForm';
import { LoadingState } from './components/LoadingState';
import { ResultsView } from './components/ResultsView';
import { ErrorBanner } from './components/ErrorBanner';
import { useGenerateScript } from './hooks/useGenerateScript';
import { INITIAL_VALUES } from './types/form';
import type { FormValues } from './types/form';

export default function App() {
  // Form values live here, so they survive loading, errors and retries.
  const [values, setValues] = useState<FormValues>(INITIAL_VALUES);
  const { status, data, error, runId, generate, retry, clearError } = useGenerateScript();
  const outputRef = useRef<HTMLElement>(null);

  function patch(update: Partial<FormValues>) {
    setValues((v) => ({ ...v, ...update }));
  }

  function scrollToOutput() {
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    outputRef.current?.scrollIntoView({
      behavior: smooth ? 'smooth' : 'auto',
      block: 'start',
    });
  }

  function handleSubmit() {
    void generate(values);
    scrollToOutput();
  }

  function handleRetry() {
    retry();
    scrollToOutput();
  }

  return (
    <div className="shell">
      <header className="masthead">
        <span className="rec-dot" aria-hidden="true" />
        Script Assistant
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

        {data && <ResultsView key={runId} data={data} isStreaming={status === 'streaming'} />}
      </section>
    </div>
  );
}
