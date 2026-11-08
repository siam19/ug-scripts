import { IconChevronLeft, IconChevronRight } from '@tabler/icons-react';

/**
 * Position within the versions of whatever is selected (line, group, or whole script).
 */
export interface ScopeVersion {
  index: number; // 0-based cursor
  count: number;
  label: string; // e.g. "Rephrased · punchier"
  type?: 'script' | 'group' | 'line';
  targetUid?: string;
}

interface RailProps {
  scope: ScopeVersion | null;
  disabled?: boolean;
  topOffset?: number | null;
  onStep: (delta: -1 | 1) => void;
}

/**
 * Chevrons at the script card's side edges, vertically aligned with selected section.
 * Rendered as a child of `.script-card` (which is position: relative).
 */
export function VersionRail({ scope, disabled = false, topOffset, onStep }: RailProps) {
  if (!scope || scope.count < 2) return null;
  const atStart = scope.index === 0;
  const atEnd = scope.index === scope.count - 1;

  const btnStyle = topOffset != null ? { top: `${topOffset}px` } : undefined;

  return (
    <>
      <div className="version-rail" role="group" aria-label="Versions">
        <button
          type="button"
          className="rail-btn rail-prev"
          aria-label="Previous version"
          style={btnStyle}
          disabled={disabled || atStart}
          onClick={() => onStep(-1)}
        >
          <IconChevronLeft size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="rail-btn rail-next"
          aria-label="Next version"
          style={btnStyle}
          disabled={disabled || atEnd}
          onClick={() => onStep(1)}
        >
          <IconChevronRight size={18} aria-hidden="true" />
        </button>
      </div>
      <span className="sr-only" role="status" aria-live="polite">
        Version {scope.index + 1} of {scope.count}: {scope.label}
      </span>
    </>
  );
}

/**
 * "2/3" pill that ties the chevrons to the selected block.
 * Rendered on the selected line or group's first line.
 * Below 700px it displays its own inline ‹ › stepper.
 */
export function ScopeBadge({ scope, disabled = false, onStep }: RailProps) {
  if (!scope || scope.count < 2) return null;
  return (
    <span className="scope-badge" title={scope.label}>
      <button
        type="button"
        className="stepper"
        aria-label="Previous version"
        disabled={disabled || scope.index === 0}
        onClick={(e) => {
          e.stopPropagation();
          onStep(-1);
        }}
      >
        <IconChevronLeft size={12} aria-hidden="true" />
      </button>
      <span>
        {scope.index + 1}/{scope.count}
      </span>
      <button
        type="button"
        className="stepper"
        aria-label="Next version"
        disabled={disabled || scope.index === scope.count - 1}
        onClick={(e) => {
          e.stopPropagation();
          onStep(1);
        }}
      >
        <IconChevronRight size={12} aria-hidden="true" />
      </button>
    </span>
  );
}
