import type { KeyboardEvent } from 'react';
import { IconRefresh } from '@tabler/icons-react';

interface Props {
  index: number;
  name: string;
  active: boolean;
  outdated: boolean; // based on earlier facts
  generating: boolean; // script being written
  replacing: boolean; // this segment is being regenerated
  tabId: string;
  panelId: string;
  tabRef: (el: HTMLButtonElement | null) => void;
  onSelect: () => void;
  onKeyDown: (e: KeyboardEvent<HTMLButtonElement>) => void;
  onRefresh: () => void;
}

/**
 * Tab button wrapped in `.tab-wrap` so `.tab-refresh` is a sibling,
 * avoiding nesting a button inside a button.
 */
export function SegmentTab({
  index,
  name,
  active,
  outdated,
  generating,
  replacing,
  tabId,
  panelId,
  tabRef,
  onSelect,
  onKeyDown,
  onRefresh,
}: Props) {
  return (
    <div
      className={`tab-wrap tab-animated${replacing ? ' is-pending' : ''}`}
      role="presentation"
    >
      <button
        ref={tabRef}
        type="button"
        role="tab"
        id={tabId}
        aria-selected={active}
        aria-controls={panelId}
        tabIndex={active ? 0 : -1}
        className={`tab${active ? ' is-active' : ''}`}
        onClick={onSelect}
        onKeyDown={onKeyDown}
      >
        <span>
          {index + 1}. {name}
        </span>
        {generating ? (
          <span
            className="tab-status-dot"
            role="img"
            aria-label="Generating script"
            title="Generating script…"
          />
        ) : outdated ? (
          <span
            className="tab-stale-ring"
            role="img"
            aria-label="Based on earlier facts"
            title="Based on earlier facts"
          />
        ) : null}
      </button>

      <button
        type="button"
        className="tab-refresh"
        aria-label={`Replace “${name}” with a new segment`}
        tabIndex={active ? 0 : -1}
        disabled={replacing}
        onClick={(e) => {
          e.stopPropagation();
          onRefresh();
        }}
      >
        <IconRefresh size={16} aria-hidden="true" />
      </button>
    </div>
  );
}
