import { Menu, Toolbar } from '@base-ui/react';
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconDots,
  IconPencil,
  IconRefresh,
  IconTrash,
  IconWand,
} from '@tabler/icons-react';

import { MOD, SHIFT } from '../state/keyboard';

export type LinePending = 'rephrase' | 'regenerate';

export interface LineToolbarProps {
  pending?: LinePending;
  canUndo: boolean;
  canRedo: boolean;
  canDelete: boolean;
  /** Label of the version Undo returns to, e.g. "Original". */
  undoHint?: string;
  onEdit: () => void;
  onRephrase: () => void;
  onRegenerate: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onDelete: () => void;
}

/**
 * (Edit · Rephrase · Regenerate) | (⋯ menu)
 * Toolbar.Root provides roving arrow-key focus; Menu.Trigger is composed into Toolbar.Button
 * so the dots menu button is part of the same roving tab stop.
 */
export function LineToolbar(p: LineToolbarProps) {
  const busy = p.pending !== undefined;

  return (
    <Toolbar.Root className="line-toolbar" aria-label="Line actions">
      <Toolbar.Button className="tb-btn" disabled={busy} onClick={p.onEdit}>
        <IconPencil size={16} aria-hidden="true" />
        <span>Edit</span>
      </Toolbar.Button>

      <Toolbar.Button className="tb-btn" disabled={busy} onClick={p.onRephrase}>
        <IconWand size={16} aria-hidden="true" />
        <span>{p.pending === 'rephrase' ? 'Rephrasing…' : 'Rephrase'}</span>
      </Toolbar.Button>

      <Toolbar.Button
        className={`tb-btn${p.pending === 'regenerate' ? ' is-spinning' : ''}`}
        disabled={busy}
        onClick={p.onRegenerate}
      >
        <IconRefresh size={16} aria-hidden="true" />
        <span>{p.pending === 'regenerate' ? 'Regenerating…' : 'Regenerate'}</span>
      </Toolbar.Button>

      <Toolbar.Separator className="tb-sep" />

      <Menu.Root>
        <Toolbar.Button
          render={<Menu.Trigger />}
          className="tb-btn tb-dots"
          aria-label="More line actions"
          disabled={busy}
        >
          <IconDots size={18} aria-hidden="true" />
        </Toolbar.Button>

        <Menu.Portal>
          <Menu.Positioner className="menu-positioner" side="bottom" align="end" sideOffset={6}>
            <Menu.Popup className="menu">
              <Menu.Item className="menu-item" disabled={!p.canUndo} onClick={p.onUndo}>
                <IconArrowBackUp size={16} aria-hidden="true" />
                <span>Undo</span>
                <span className="menu-hint">{p.undoHint ?? `${MOD}Z`}</span>
              </Menu.Item>
              <Menu.Item className="menu-item" disabled={!p.canRedo} onClick={p.onRedo}>
                <IconArrowForwardUp size={16} aria-hidden="true" />
                <span>Redo</span>
                <span className="menu-hint">{`${SHIFT}${MOD}Z`}</span>
              </Menu.Item>

              <Menu.Separator className="menu-sep" />

              <Menu.Item
                className="menu-item is-danger"
                disabled={!p.canDelete}
                onClick={p.onDelete}
              >
                <IconTrash size={16} aria-hidden="true" />
                <span>Delete line</span>
              </Menu.Item>
            </Menu.Popup>
          </Menu.Positioner>
        </Menu.Portal>
      </Menu.Root>
    </Toolbar.Root>
  );
}
