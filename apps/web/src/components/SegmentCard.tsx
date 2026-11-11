import { useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { Angle, Segment } from 'api-types';
import {
  IconBookmark,
  IconCheck,
  IconPencil,
  IconUsers,
  IconX,
} from '@tabler/icons-react';
import { formatAngleType } from './AngleChips';

interface Props {
  segment: Segment;
  angles?: Angle[];
  edited?: boolean;
  isSaved?: boolean;
  canSave?: boolean;
  onSave?: () => void;
  onEdit?: (segment: Segment) => void;
}

export function SegmentCard({
  segment,
  angles = [],
  edited = false,
  isSaved = false,
  canSave = true,
  onSave,
  onEdit,
}: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(segment.name);
  const [who, setWho] = useState(segment.who);
  const [platforms, setPlatforms] = useState<string[]>(segment.platforms);
  const [newPlatform, setNewPlatform] = useState('');

  const leadAngles = (angles || []).filter(
    (a) => segment.lead_angle_ids?.includes(a.id),
  );

  function startEdit() {
    setName(segment.name);
    setWho(segment.who);
    setPlatforms([...segment.platforms]);
    setNewPlatform('');
    setIsEditing(true);
  }

  function cancelEdit() {
    setIsEditing(false);
  }

  function commitEdit() {
    const trimmedName = name.trim();
    if (!trimmedName) return;

    const trimmedWho = who.trim();
    const finalPlatforms = [...platforms];
    if (newPlatform.trim() && !finalPlatforms.includes(newPlatform.trim())) {
      finalPlatforms.push(newPlatform.trim());
    }

    onEdit?.({
      ...segment,
      name: trimmedName,
      who: trimmedWho,
      platforms: finalPlatforms,
    });
    setIsEditing(false);
  }

  function handleAddPlatform() {
    const p = newPlatform.trim();
    if (p && !platforms.includes(p)) {
      setPlatforms([...platforms, p]);
      setNewPlatform('');
    }
  }

  function handlePlatformKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddPlatform();
    }
  }

  function removePlatform(tag: string) {
    setPlatforms(platforms.filter((p) => p !== tag));
  }

  return (
    <article className="panel segment-card">
      <div className="segment-main">
        {isEditing ? (
          <>
            <div>
              <label htmlFor="edit-segment-name" className="sr-only">
                Segment Title
              </label>
              <input
                id="edit-segment-name"
                className="segment-title-input"
                type="text"
                required
                value={name}
                placeholder="Segment name"
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="edit-segment-who" className="sr-only">
                Target Demographics
              </label>
              <textarea
                id="edit-segment-who"
                className="segment-who-edit"
                rows={3}
                value={who}
                placeholder="Who this audience is..."
                onChange={(e) => setWho(e.target.value)}
              />
            </div>

            <div className="tag-edit-wrap">
              {platforms.map((p) => (
                <span key={p} className="tag is-editing">
                  {p}
                  <button
                    type="button"
                    className="tag-remove"
                    aria-label={`Remove ${p}`}
                    onClick={() => removePlatform(p)}
                  >
                    <IconX size={12} aria-hidden="true" />
                  </button>
                </span>
              ))}
              <input
                type="text"
                className="tag-add-input"
                placeholder="+ Add platform"
                value={newPlatform}
                onChange={(e) => setNewPlatform(e.target.value)}
                onKeyDown={handlePlatformKey}
                onBlur={handleAddPlatform}
              />
            </div>

            <div className="segment-actions">
              <button
                type="button"
                className="btn btn-sm btn-quiet"
                onClick={cancelEdit}
              >
                <IconX size={14} aria-hidden="true" />
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-sm btn-primary"
                disabled={!name.trim()}
                onClick={commitEdit}
              >
                <IconCheck size={14} aria-hidden="true" />
                Done
              </button>
            </div>
          </>
        ) : (
          <>
            <h3>
              <IconUsers size={24} className="segment-title-icon" aria-hidden="true" />
              <span>{segment.name}</span>
              {edited && <span className="edited-badge">Edited</span>}
            </h3>

            <p className="segment-who">{segment.who}</p>

            <ul className="tag-list" aria-label="Recommended platforms">
              {segment.platforms.map((p) => (
                <li key={p} className="tag">
                  {p}
                </li>
              ))}
            </ul>

            {leadAngles.length > 0 && (
              <div className="segment-lead-angles">
                <span className="segment-lead-title">Lead Angles:</span>
                <div className="segment-lead-chips">
                  {leadAngles.map((a) => (
                    <span
                      key={a.id}
                      className={`angle-badge angle-badge-${a.type}`}
                      title={a.text}
                    >
                      {formatAngleType(a.type)}: “{a.text.slice(0, 50)}{a.text.length > 50 ? '…' : ''}”
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="segment-actions">
              {onSave && (
                <button
                  type="button"
                  className={`btn btn-sm ${isSaved ? 'btn-primary' : 'btn-quiet'}`}
                  disabled={!canSave}
                  onClick={onSave}
                >
                  <IconBookmark size={15} aria-hidden="true" />
                  <span>{isSaved ? 'Saved' : 'Save'}</span>
                </button>
              )}
              {onEdit && (
                <button
                  type="button"
                  className="btn btn-sm btn-quiet"
                  onClick={startEdit}
                >
                  <IconPencil size={15} aria-hidden="true" />
                  <span>Edit</span>
                </button>
              )}
            </div>
          </>
        )}
      </div>

      <figure className="pain">
        <figcaption>In their words</figcaption>
        <blockquote>&ldquo;{segment.pain_point}&rdquo;</blockquote>
      </figure>
    </article>
  );
}
