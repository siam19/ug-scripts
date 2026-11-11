import { useMemo, useState } from 'react';
import type { Angle, AngleType } from 'api-types';
import {
  IconChevronDown,
  IconChevronUp,
} from '@tabler/icons-react';

interface Props {
  angles: Angle[];
}

export function formatAngleType(type: AngleType): string {
  switch (type) {
    case 'benefit':
      return 'Benefit';
    case 'demo':
      return 'Visual Demo';
    case 'objection':
      return 'Objection';
    case 'use_moment':
      return 'Use Moment';
    case 'identity':
      return 'Identity';
    case 'contrast':
      return 'Contrast';
    case 'audience_context':
      return 'Context';
    default:
      return type;
  }
}

const CLAIM_BEARING_TYPES: Set<AngleType> = new Set(['benefit', 'demo', 'objection']);

export function AngleChips({ angles }: Props) {
  const [filter, setFilter] = useState<'all' | 'claims' | 'framing'>('all');
  const [expanded, setExpanded] = useState(false);

  const filteredAngles = useMemo(() => {
    if (filter === 'claims') {
      return angles.filter((a) => CLAIM_BEARING_TYPES.has(a.type));
    }
    if (filter === 'framing') {
      return angles.filter((a) => !CLAIM_BEARING_TYPES.has(a.type));
    }
    return angles;
  }, [angles, filter]);

  if (!angles || angles.length === 0) {
    return null;
  }

  const initialDisplayCount = 6;
  const showToggle = filteredAngles.length > initialDisplayCount;
  const displayedAngles =
    expanded || !showToggle
      ? filteredAngles
      : filteredAngles.slice(0, initialDisplayCount);

  return (
    <div className="angles-container">
      <div className="angles-toolbar">
        <div className="angles-filter-group" role="tablist" aria-label="Angle categories">
          <button
            type="button"
            className={`angles-filter-btn${filter === 'all' ? ' is-active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All ({angles.length})
          </button>
          <button
            type="button"
            className={`angles-filter-btn${filter === 'claims' ? ' is-active' : ''}`}
            onClick={() => setFilter('claims')}
          >
            Claim-bearing ({angles.filter((a) => CLAIM_BEARING_TYPES.has(a.type)).length})
          </button>
          <button
            type="button"
            className={`angles-filter-btn${filter === 'framing' ? ' is-active' : ''}`}
            onClick={() => setFilter('framing')}
          >
            Framing ({angles.filter((a) => !CLAIM_BEARING_TYPES.has(a.type)).length})
          </button>
        </div>

        {showToggle && (
          <button
            type="button"
            className="angles-toggle-btn"
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? (
              <>
                Show fewer <IconChevronUp size={14} aria-hidden="true" />
              </>
            ) : (
              <>
                Show all {filteredAngles.length} <IconChevronDown size={14} aria-hidden="true" />
              </>
            )}
          </button>
        )}
      </div>

      <div className="angles-grid">
        {displayedAngles.map((angle) => {
          const isClaim = CLAIM_BEARING_TYPES.has(angle.type);
          return (
            <div
              key={angle.id}
              className={`angle-card chip-animated angle-card-${angle.type}`}
            >
              <div className="angle-card-header">
                <span className={`angle-badge angle-badge-${angle.type}`}>
                  {formatAngleType(angle.type)}
                </span>
                {angle.based_on && angle.based_on.length > 0 && (
                  <span
                    className="angle-based-badge"
                    title={`Grounded in product Fact #${angle.based_on.join(', #')}`}
                  >
                    Fact #{angle.based_on.join(', #')}
                  </span>
                )}
                {!isClaim && (
                  <span className="angle-framing-badge" title="Creative situational framing">
                    Framing
                  </span>
                )}
              </div>
              <p className="angle-text">{angle.text}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
