import type { ReactNode } from 'react';
import { IconRefresh } from '@tabler/icons-react';

export interface StaleAction {
  label: string;
  onClick: () => void;
  primary?: boolean;
  loading?: boolean;
}

interface BarProps {
  children: ReactNode;
  actions: StaleAction[];
  busy?: boolean;
}

/**
 * Hatched, passive strip. Never wraps or blocks the content it describes.
 */
export function StaleBar({ children, actions, busy = false }: BarProps) {
  return (
    <div className={`stale-bar${busy ? ' is-busy' : ''}`} role="status">
      <p>{children}</p>
      <div className="stale-actions">
        {actions.map((a) => {
          const isLoading = Boolean(a.loading || (busy && a.primary));
          return (
            <button
              key={a.label}
              type="button"
              className={`btn btn-sm ${a.primary ? 'btn-primary' : 'btn-quiet'}${isLoading ? ' is-loading' : ''}`}
              disabled={busy || isLoading}
              onClick={a.onClick}
            >
              {isLoading && (
                <IconRefresh size={14} className="btn-spinner" aria-hidden="true" />
              )}
              <span>{a.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Height-animating wrapper (grid-template-rows 0fr -> 1fr) so the facts cause bar
 * slides open without a layout jump. Closed content is inert.
 */
export function Collapse({ open, children }: { open: boolean; children: ReactNode }) {
  // `inert` is a boolean in modern React types; cast via spread for React 18 compatibility.
  const inertProps = open ? {} : ({ inert: '' } as Record<string, string>);
  return (
    <div className={`collapse${open ? ' is-open' : ''}`} {...inertProps}>
      <div className="collapse-inner">{children}</div>
    </div>
  );
}
