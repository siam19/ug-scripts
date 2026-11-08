import type { ReactNode } from 'react';

export interface StaleAction {
  label: string;
  onClick: () => void;
  primary?: boolean;
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
    <div className="stale-bar" role="status">
      <p>{children}</p>
      <div className="stale-actions">
        {actions.map((a) => (
          <button
            key={a.label}
            type="button"
            className={`btn btn-sm ${a.primary ? 'btn-primary' : 'btn-quiet'}`}
            disabled={busy}
            onClick={a.onClick}
          >
            {a.label}
          </button>
        ))}
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
