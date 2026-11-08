import { useCallback } from 'react';
import type { LineKind, Script, Segment } from 'api-types';

/**
 * Local simulation generators for Sprint 2 actions while backend endpoints are prepared.
 */
export function useRegenerate() {
  const regenerateSegment = useCallback(
    async (current: Segment, others: Segment[], _facts: string[]): Promise<Segment> => {
      // Small simulated delay
      await new Promise((r) => setTimeout(r, 650));

      const variations = [
        {
          name: 'Budget-Savvy Explorers',
          who: 'College students and early-career pros who prioritize value, versatility, and real user reviews.',
          pain_point: "I want quality that works without burning my entire month's allowance.",
          platforms: ['TikTok', 'Instagram Reels'],
        },
        {
          name: 'Daily Commuters & Hustlers',
          who: 'Busy urban commuters balancing long work hours, public transit, and fast-paced living.',
          pain_point: 'I need something effortless that keeps up with my hectic schedule all day.',
          platforms: ['Instagram Reels', 'Facebook Watch'],
        },
        {
          name: 'Mindful Minimalists',
          who: 'Conscious shoppers seeking clean ingredients, sustainable packaging, and zero fluff.',
          pain_point: 'Tired of exaggerated claims and overcomplicated 10-step routines.',
          platforms: ['YouTube Shorts', 'Instagram Reels'],
        },
        {
          name: 'Weekend Enthusiasts',
          who: 'Active trend-followers who love sharing practical finds and lifestyle upgrades with friends.',
          pain_point: "I need dependable recommendations that look good on camera and actually deliver.",
          platforms: ['TikTok', 'Snapchat'],
        },
      ];

      const otherNames = new Set([...others.map((o) => o.name), current.name]);
      const candidate = variations.find((v) => !otherNames.has(v.name)) || {
        name: `${current.name} (Refined)`,
        who: `${current.who} with a sharper focus on fast daily routines.`,
        pain_point: current.pain_point,
        platforms: current.platforms,
      };

      return candidate;
    },
    [],
  );

  const rewriteReasonLines = useCallback(
    async (
      title: string,
      _why: string,
      currentLines: { kind: LineKind; text: string }[],
    ): Promise<{ kind: LineKind; text: string }[]> => {
      await new Promise((r) => setTimeout(r, 700));

      return currentLines.map((l) => {
        if (l.kind === 'hook') {
          return {
            kind: 'hook',
            text: `Stop scrolling if you care about real results—here is the breakdown.`,
          };
        }
        if (l.kind === 'cta') {
          return {
            kind: 'cta',
            text: `Tap the link below before stocks run out today!`,
          };
        }
        return {
          kind: 'concept',
          text: `It specifically addresses ${title.toLowerCase()}: built for everyday reliability and zero fuss.`,
        };
      });
    },
    [],
  );

  const rephraseLine = useCallback(
    async (
      currentText: string,
      _kind: LineKind,
    ): Promise<{ text: string; tone: string }> => {
      await new Promise((r) => setTimeout(r, 500));

      const toneVariants = [
        { text: `Honestly? ${currentText.replace(/^([A-Z])/, (_, c) => c.toLowerCase())}`, tone: 'casual' },
        { text: `Quick fact: ${currentText}`, tone: 'punchy' },
        { text: `Here's what you need to know: ${currentText}`, tone: 'direct' },
        { text: `No exaggerations here—${currentText.toLowerCase()}`, tone: 'authentic' },
      ];

      const pick = toneVariants[Math.floor(Math.random() * toneVariants.length)];
      return pick;
    },
    [],
  );

  const regenerateLine = useCallback(
    async (_currentText: string, kind: LineKind): Promise<string> => {
      await new Promise((r) => setTimeout(r, 600));

      if (kind === 'hook') {
        return `Wait, did you know most people get this completely wrong?`;
      }
      if (kind === 'cta') {
        return `Check it out now and grab yours while it's still available.`;
      }
      return `Formulated to work smoothly without any unnecessary extras or greasy residue.`;
    },
    [],
  );

  const rewriteScript = useCallback(
    async (segment: Segment, facts: string[]): Promise<Script> => {
      await new Promise((r) => setTimeout(r, 900));

      return {
        segment: segment.name,
        lines: [
          {
            id: 1,
            kind: 'hook',
            text: `If you're part of the ${segment.name.toLowerCase()}, this one is tailored for you.`,
          },
          {
            id: 2,
            kind: 'concept',
            text: `Here are the verified facts: ${facts[0] || 'Quality ingredients you can trust.'}`,
          },
          {
            id: 3,
            kind: 'concept',
            text: `Directly tackles your biggest struggle: "${segment.pain_point}".`,
          },
          {
            id: 4,
            kind: 'cta',
            text: `Get yours today on ${segment.platforms[0] || 'our shop'}!`,
          },
        ],
        reasons: [
          {
            title: 'Direct Persona Callout',
            why: 'Hooks the exact demographic immediately within the first 3 seconds.',
            line_ids: [1],
          },
          {
            title: 'Verifiable Proof Point',
            why: 'Anchors consumer trust by highlighting grounded claims.',
            line_ids: [2, 3],
          },
          {
            title: 'Urgent Platform CTA',
            why: 'Directs viewers to take action right on their favorite channel.',
            line_ids: [4],
          },
        ],
      };
    },
    [],
  );

  return {
    regenerateSegment,
    rewriteReasonLines,
    rephraseLine,
    regenerateLine,
    rewriteScript,
  };
}
