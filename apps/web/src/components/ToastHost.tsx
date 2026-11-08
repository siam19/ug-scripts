import { useEffect } from 'react';
import { IconX } from '@tabler/icons-react';

export interface ToastItem {
  id: string;
  message: string;
  undoAction?: () => void;
  undoLabel?: string;
  durationMs?: number;
  isError?: boolean;
}

interface Props {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

export function ToastHost({ toasts, onDismiss }: Props) {
  return (
    <div className="toast-host" role="region" aria-label="Notifications">
      {toasts.map((t) => (
        <ToastSingle key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastSingle({
  toast,
  onDismiss,
}: {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}) {
  const duration =
    toast.durationMs ??
    (toast.isError ? 6_000 : toast.undoAction ? 7_000 : 4_000);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      onDismiss(toast.id);
    }, duration);
    return () => window.clearTimeout(timer);
  }, [toast.id, duration, onDismiss]);

  return (
    <div
      className={`toast${toast.isError ? ' is-error' : ''}`}
      role={toast.isError ? 'alert' : 'status'}
      aria-live={toast.isError ? 'assertive' : 'polite'}
    >
      <span className="toast-message">{toast.message}</span>
      {toast.undoAction && (
        <button
          type="button"
          className="toast-undo"
          onClick={() => {
            toast.undoAction?.();
            onDismiss(toast.id);
          }}
        >
          {toast.undoLabel ?? 'Undo'}
        </button>
      )}
      <button
        type="button"
        className="toast-close"
        aria-label="Dismiss notification"
        title="Dismiss"
        onClick={() => onDismiss(toast.id)}
      >
        <IconX size={14} aria-hidden="true" />
      </button>
    </div>
  );
}
