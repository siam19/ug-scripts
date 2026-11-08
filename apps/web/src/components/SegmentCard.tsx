// apps/web/src/components/SegmentCard.tsx
import type { Segment } from 'api-types';
import { IconUsers } from '@tabler/icons-react';

interface Props {
  segment: Segment;
}

export function SegmentCard({ segment }: Props) {
  return (
    <article className="panel segment-card">
      <div className="segment-main">
        <h3>
          <IconUsers size={24} className="segment-title-icon" aria-hidden="true" />
          <span>{segment.name}</span>
        </h3>
        <p className="segment-who">{segment.who}</p>
        <ul className="tag-list" aria-label="Recommended platforms">
          {segment.platforms.map((p) => (
            <li key={p} className="tag">
              {p}
            </li>
          ))}
        </ul>
      </div>

      <figure className="pain">
        <figcaption>In their words</figcaption>
        <blockquote>&ldquo;{segment.pain_point}&rdquo;</blockquote>
      </figure>
    </article>
  );
}
