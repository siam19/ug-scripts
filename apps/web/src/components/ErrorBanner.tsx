// apps/web/src/components/ErrorBanner.tsx
import type { FriendlyError } from '../hooks/useGenerateScript';

interface Props {
  error: FriendlyError;
  onRetry: () => void;
  onDismiss: () => void;
}

export function ErrorBanner({ error, onRetry, onDismiss }: Props) {
  return (
    <div className="error-banner" role="alert">
      <div className="error-copy">
        <strong>{error.title}</strong>
        <p>{error.message}</p>
        <p className="hint">Your form is unchanged, so you can retry or edit it first.</p>
      </div>
      <div className="error-actions">
        <button type="button" className="btn btn-primary" onClick={onRetry}>
          Try again
        </button>
        <button type="button" className="btn btn-quiet" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}
