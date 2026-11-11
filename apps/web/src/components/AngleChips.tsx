import { useMemo, useRef, useState } from 'react';
import type { Angle, AngleType } from 'api-types';
import {
  IconChevronDown,
  IconChevronLeft,
  IconChevronRight,
  IconChevronUp,
  IconInfoCircle,
} from '@tabler/icons-react';

export interface AngleTypeMeta {
  label: string;
  meaning: string;
  category: 'claim' | 'framing';
  categoryLabel: string;
}

export const ANGLE_TYPE_META: Record<AngleType, AngleTypeMeta> = {
  benefit: {
    label: 'Benefit',
    meaning: 'Highlights a direct, tangible outcome or core advantage grounded in product facts.',
    category: 'claim',
    categoryLabel: 'Claim-bearing',
  },
  demo: {
    label: 'Visual Demo',
    meaning: 'Showcases a physical demonstration, test, or visible proof moment on camera.',
    category: 'claim',
    categoryLabel: 'Claim-bearing',
  },
  objection: {
    label: 'Objection',
    meaning: 'Proactively addresses buyer hesitation, skepticism, or perceived friction.',
    category: 'claim',
    categoryLabel: 'Claim-bearing',
  },
  use_moment: {
    label: 'Use Moment',
    meaning: 'Frames a specific, relatable daily routine or situation where the product shines.',
    category: 'framing',
    categoryLabel: 'Situational Framing',
  },
  identity: {
    label: 'Identity',
    meaning: 'Taps into who the buyer aspires to be, how they feel, and self-perception.',
    category: 'framing',
    categoryLabel: 'Situational Framing',
  },
  contrast: {
    label: 'Contrast',
    meaning: 'Dramatizes the frustrating status quo or painful legacy alternatives.',
    category: 'framing',
    categoryLabel: 'Situational Framing',
  },
  audience_context: {
    label: 'Context',
    meaning: 'Grounds the hook in local cultural norms, environment, or daily reality.',
    category: 'framing',
    categoryLabel: 'Situational Framing',
  },
};

export function formatAngleType(type: AngleType): string {
  return ANGLE_TYPE_META[type]?.label ?? type;
}

const CLAIM_BEARING_TYPES: Set<AngleType> = new Set(['benefit', 'demo', 'objection']);

/**
 * Interactive Angle Type pill with an elegant hover tooltip explaining its meaning.
 */
function AngleTypeBadge({ type }: { type: AngleType }) {
  const meta = ANGLE_TYPE_META[type] ?? {
    label: type,
    meaning: 'Creative strategy connecting product truths to buyer intent.',
    category: 'framing' as const,
    categoryLabel: 'Strategy',
  };
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className="angle-type-pill-wrap"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
      tabIndex={0}
      role="note"
      aria-label={`${meta.label}: ${meta.meaning}`}
    >
      <span className={`angle-badge angle-badge-${type}`}>
        <span>{meta.label}</span>
        <IconInfoCircle size={12} className="angle-info-icon" aria-hidden="true" />
      </span>

      {showTooltip && (
        <div className="angle-tooltip" role="tooltip">
          <div className="angle-tooltip-head">
            <strong>{meta.label}</strong>
            <span className={`angle-tooltip-cat ${meta.category}`}>{meta.categoryLabel}</span>
          </div>
          <p className="angle-tooltip-desc">{meta.meaning}</p>
        </div>
      )}
    </div>
  );
}

interface Props {
  angles: Angle[];
}

export function AngleChips({ angles }: Props) {
  const [filter, setFilter] = useState<'all' | 'claims' | 'framing'>('all');
  const [expanded, setExpanded] = useState(false);
  const railRef = useRef<HTMLDivElement>(null);

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

  function scrollRail(direction: 'left' | 'right') {
    if (!railRef.current) return;
    const offset = direction === 'left' ? -300 : 300;
    railRef.current.scrollBy({ left: offset, behavior: 'smooth' });
  }

  return (
    <div className="angles-container">
      <div className="angles-toolbar">
        <div className="angles-filter-group" role="tablist" aria-label="Angle categories">
          <button
            type="button"
            className={`angles-filter-btn${filter === 'all' ? ' is-active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All <span className="angles-count-pill">{angles.length}</span>
          </button>
          <button
            type="button"
            className={`angles-filter-btn${filter === 'claims' ? ' is-active' : ''}`}
            onClick={() => setFilter('claims')}
          >
            Claim-bearing{' '}
            <span className="angles-count-pill">
              {angles.filter((a) => CLAIM_BEARING_TYPES.has(a.type)).length}
            </span>
          </button>
          <button
            type="button"
            className={`angles-filter-btn${filter === 'framing' ? ' is-active' : ''}`}
            onClick={() => setFilter('framing')}
          >
            Framing{' '}
            <span className="angles-count-pill">
              {angles.filter((a) => !CLAIM_BEARING_TYPES.has(a.type)).length}
            </span>
          </button>
        </div>

        <div className="angles-actions">
          {/* Mobile carousel scroll controls */}
          <div className="angles-mobile-controls" aria-label="Scroll angles">
            <button
              type="button"
              className="angles-scroll-btn"
              aria-label="Previous angle"
              onClick={() => scrollRail('left')}
            >
              <IconChevronLeft size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              className="angles-scroll-btn"
              aria-label="Next angle"
              onClick={() => scrollRail('right')}
            >
              <IconChevronRight size={16} aria-hidden="true" />
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
                  <span>Show fewer</span>
                  <IconChevronUp size={14} aria-hidden="true" />
                </>
              ) : (
                <>
                  <span>Show all {filteredAngles.length}</span>
                  <IconChevronDown size={14} aria-hidden="true" />
                </>
              )}
            </button>
          )}
        </div>
      </div>

      <div className="angles-grid" ref={railRef}>
        {displayedAngles.map((angle) => {
          const isClaim = CLAIM_BEARING_TYPES.has(angle.type);
          return (
            <div
              key={angle.id}
              className={`angle-card chip-animated angle-card-${angle.type}`}
            >
              <div className="angle-card-header">
                <span className="angle-number-badge">#{angle.id}</span>
                <AngleTypeBadge type={angle.type} />
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
