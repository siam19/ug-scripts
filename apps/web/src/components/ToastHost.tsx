import { useEffect } from 'react';

export interface ToastItem {
  id: string;
  message: string;
  undoAction?: () => void;
  undoLabel?: string;
  durationMs?: number;
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
  const duration = toast.durationMs ?? (toast.undoAction ? 12_000 : 4_000);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      onDismiss(toast.id);
    }, duration);
    return () => window.clearTimeout(timer);
  }, [toast.id, duration, onDismiss]);

  return (
    <div className="toast" role="status">
      <span>{toast.message}</span>
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
    </div>
  );
}
