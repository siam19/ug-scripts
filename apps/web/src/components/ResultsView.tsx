import { useCallback, useEffect, useId, useReducer, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { IconChevronRight } from '@tabler/icons-react';
import type { LineKind, ProgressiveGenerateResponse, Segment } from 'api-types';
import { useRegenerate } from '../hooks/useRegenerate';
import {
  factsHash,
  scriptStaleMessage,
  scriptStaleReasons,
  slotNeedsRegen,
} from '../state/hash';
import { useSavedScripts } from '../state/saved-scripts';
import {
  collectVisibleUids,
  getActiveLines,
  getActiveScope,
  resolveVisibleCover,
} from '../state/script-tree';
import type { SegmentSlot, Uid } from '../state/types';
import { generateUid } from '../state/uid';
import { INITIAL_WORKSPACE, workspaceReducer } from '../state/workspace';
import { FactChips } from './FactChips';
import { AngleChips } from './AngleChips';
import { ReasonList } from './ReasonList';
import type { ReasonDisplayItem } from './ReasonList';
import { ScriptCard } from './ScriptCard';
import { SegmentCard } from './SegmentCard';
import { SegmentTab } from './SegmentTab';
import { Collapse, StaleBar } from './StaleBar';
import { ToastHost } from './ToastHost';
import type { ToastItem } from './ToastHost';

import type { ScriptFormat } from 'api-types';

interface Props {
  data: ProgressiveGenerateResponse;
  isStreaming?: boolean;
  meta?: { name: string; market: string; language: 'en' | 'bn'; script_format?: ScriptFormat };
}

export function ResultsView({
  data,
  isStreaming = false,
  meta = { name: 'Product', market: 'Global', language: 'en', script_format: 'ugc' },
}: Props) {
  const uid = useId();
  const [workspace, dispatch] = useReducer(workspaceReducer, INITIAL_WORKSPACE);
  const { save, isSaved, remove: removeSaved } = useSavedScripts();
  const {
    regenerateSegment,
    rewriteReasonLines,
    rephraseLine,
    regenerateLine,
    rewriteScript,
  } = useRegenerate(meta);

  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const segmentSectionRef = useRef<HTMLElement>(null);
  const workbenchRef = useRef<HTMLDivElement>(null);
  const tabsContainerRef = useRef<HTMLDivElement>(null);
  const [canScrollTabsRight, setCanScrollTabsRight] = useState(false);

  const checkTabsScroll = useCallback(() => {
    const el = tabsContainerRef.current;
    if (!el) return;
    const hasMore = el.scrollLeft + el.clientWidth < el.scrollWidth - 10;
    setCanScrollTabsRight(hasMore);
  }, []);

  function scrollTabsRight() {
    tabsContainerRef.current?.scrollBy({ left: 220, behavior: 'smooth' });
  }

  // Regeneration loading states
  const [isRegeneratingStale, setIsRegeneratingStale] = useState(false);
  const [rewritingSlotIds, setRewritingSlotIds] = useState<Set<Uid>>(new Set());

  // Client-side rate limiting & anti-spam guard
  const requestTimestamps = useRef<number[]>([]);
  const lastRequestTime = useRef<number>(0);

  const isRateLimited = useCallback((): boolean => {
    const now = Date.now();
    // 1. Rapid burst debounce: minimum 1.2s between user trigger clicks
    if (now - lastRequestTime.current < 1200) {
      return true;
    }
    // 2. 60-second sliding window: max 12 requests per minute
    const windowStart = now - 60_000;
    requestTimestamps.current = requestTimestamps.current.filter((t) => t > windowStart);
    if (requestTimestamps.current.length >= 12) {
      return true;
    }
    return false;
  }, []);

  const recordRequest = useCallback(() => {
    const now = Date.now();
    lastRequestTime.current = now;
    requestTimestamps.current.push(now);
  }, []);

  // Toasts
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const addToast = (
    msg: string,
    undoAction?: () => void,
    undoLabel?: string,
    isError?: boolean,
  ) => {
    const id = generateUid();
    setToasts((prev) => [...prev, { id, message: msg, undoAction, undoLabel, isError }]);
  };
  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Seed workspace from incoming data
  const seeded = useRef(false);
  useEffect(() => {
    if (!seeded.current && data.facts.length > 0 && data.segments.length > 0) {
      seeded.current = true;
      dispatch({
        type: 'SEED_WORKSPACE',
        facts: data.facts,
        angles: data.angles || [],
        segments: data.segments,
        meta: {
          name: meta.name || 'Product',
          market: meta.market || 'Global',
          language: meta.language || 'en',
          script_format: meta.script_format || data.script_format || 'ugc',
        },
      });
    }
  }, [data.facts, data.segments, meta]);

  // Feed streamed scripts progressively into workspace slots
  const ingestedScripts = useRef<Set<number>>(new Set());
  useEffect(() => {
    data.scripts.forEach((script, i) => {
      if (script && !ingestedScripts.current.has(i)) {
        ingestedScripts.current.add(i);
        dispatch({ type: 'SCRIPT_READY', index: i, script });
      }
    });
  }, [data.scripts]);

  // Staggered reveal for initial load
  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const totalFacts = data.facts.length;
  const totalAngles = (data.angles || []).length;
  const totalSegments = data.segments.length;

  const [visibleFactsCount, setVisibleFactsCount] = useState(() =>
    prefersReducedMotion ? totalFacts : 0,
  );
  const [visibleAnglesCount, setVisibleAnglesCount] = useState(() =>
    prefersReducedMotion ? totalAngles : 0,
  );
  const [visibleSegmentsCount, setVisibleSegmentsCount] = useState(() =>
    prefersReducedMotion ? totalSegments : 0,
  );

  useEffect(() => {
    if (prefersReducedMotion) return;
    let timer: number | null = null;
    if (visibleFactsCount < totalFacts) {
      timer = window.setTimeout(
        () => setVisibleFactsCount((c) => Math.min(c + 1, totalFacts)),
        visibleFactsCount === 0 ? 300 : 420,
      );
    } else if (visibleAnglesCount < totalAngles) {
      timer = window.setTimeout(
        () => setVisibleAnglesCount((c) => Math.min(c + 1, totalAngles)),
        visibleAnglesCount === 0 ? 360 : 460,
      );
    } else if (visibleSegmentsCount < totalSegments) {
      timer = window.setTimeout(
        () => setVisibleSegmentsCount((c) => Math.min(c + 1, totalSegments)),
        visibleSegmentsCount === 0 ? 400 : 540,
      );
    }
    return () => {
      if (timer) window.clearTimeout(timer);
    };
  }, [visibleFactsCount, visibleAnglesCount, visibleSegmentsCount, totalFacts, totalAngles, totalSegments, prefersReducedMotion]);

  const userScrolledUpRef = useRef(false);
  const scrollAnimRef = useRef<number | null>(null);

  // Reset cancellation on new data
  useEffect(() => {
    userScrolledUpRef.current = false;
  }, [data]);

  // Listen for user upward scroll to cancel auto-follow
  useEffect(() => {
    function onWheel(e: WheelEvent) {
      if (e.deltaY < -1) {
        userScrolledUpRef.current = true;
        if (scrollAnimRef.current) {
          cancelAnimationFrame(scrollAnimRef.current);
          scrollAnimRef.current = null;
        }
      }
    }

    let touchStartY = 0;
    function onTouchStart(e: TouchEvent) {
      if (e.touches.length > 0) touchStartY = e.touches[0].clientY;
    }
    function onTouchMove(e: TouchEvent) {
      if (e.touches.length > 0 && e.touches[0].clientY - touchStartY > 10) {
        userScrolledUpRef.current = true;
        if (scrollAnimRef.current) {
          cancelAnimationFrame(scrollAnimRef.current);
          scrollAnimRef.current = null;
        }
      }
    }

    function onKeyDown(e: globalThis.KeyboardEvent) {
      if (['ArrowUp', 'PageUp', 'Home'].includes(e.key)) {
        userScrolledUpRef.current = true;
        if (scrollAnimRef.current) {
          cancelAnimationFrame(scrollAnimRef.current);
          scrollAnimRef.current = null;
        }
      }
    }

    window.addEventListener('wheel', onWheel, { passive: true });
    window.addEventListener('touchstart', onTouchStart, { passive: true });
    window.addEventListener('touchmove', onTouchMove, { passive: true });
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('wheel', onWheel);
      window.removeEventListener('touchstart', onTouchStart);
      window.removeEventListener('touchmove', onTouchMove);
      window.removeEventListener('keydown', onKeyDown);
      if (scrollAnimRef.current) {
        cancelAnimationFrame(scrollAnimRef.current);
        scrollAnimRef.current = null;
      }
    };
  }, []);

  // Smooth easeInOutCubic scroll function
  const scrollToTargetY = useCallback(
    (targetY: number, duration = 380) => {
      if (userScrolledUpRef.current || prefersReducedMotion) return;
      if (scrollAnimRef.current) {
        cancelAnimationFrame(scrollAnimRef.current);
        scrollAnimRef.current = null;
      }

      const startY = window.scrollY || window.pageYOffset;
      const distance = targetY - startY;
      if (Math.abs(distance) < 8) return;

      const startTime = performance.now();

      function easeInOutCubic(t: number): number {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      }

      function step(now: number) {
        if (userScrolledUpRef.current) {
          scrollAnimRef.current = null;
          return;
        }
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / duration);
        const eased = easeInOutCubic(progress);

        window.scrollTo(0, startY + distance * eased);

        if (progress < 1) {
          scrollAnimRef.current = requestAnimationFrame(step);
        } else {
          scrollAnimRef.current = null;
        }
      }

      scrollAnimRef.current = requestAnimationFrame(step);
    },
    [prefersReducedMotion],
  );

  // Glue viewport to new generations as they pop into existence
  useEffect(() => {
    if (userScrolledUpRef.current || prefersReducedMotion) return;

    const t = window.setTimeout(() => {
      if (userScrolledUpRef.current) return;

      const viewportHeight = window.innerHeight;
      const scrollY = window.scrollY || window.pageYOffset;

      if (visibleSegmentsCount >= totalSegments && workbenchRef.current) {
        // Workbench has appeared: frame top of workbench comfortably
        const rect = workbenchRef.current.getBoundingClientRect();
        const targetY = Math.max(0, scrollY + rect.top - 24);
        if (targetY > scrollY + 10) {
          scrollToTargetY(targetY, 480);
        }
      } else if (visibleSegmentsCount > 0 && segmentSectionRef.current) {
        // Customer segments section popping in
        const rect = segmentSectionRef.current.getBoundingClientRect();
        if (rect.bottom > viewportHeight - 60) {
          const targetY = scrollY + rect.bottom - viewportHeight + 80;
          scrollToTargetY(targetY, 380);
        }
      } else if (visibleAnglesCount > 0) {
        // New angle card popping in
        const angleCards = document.querySelectorAll('.angles-grid .angle-card');
        const lastCard = angleCards[visibleAnglesCount - 1] as HTMLElement | undefined;
        if (lastCard) {
          const rect = lastCard.getBoundingClientRect();
          if (rect.bottom > viewportHeight - 60) {
            const targetY = scrollY + rect.bottom - viewportHeight + 90;
            scrollToTargetY(targetY, 360);
          }
        }
      } else if (visibleFactsCount > 0) {
        // New fact chip popping in
        const factChips = document.querySelectorAll('.chip-list .chip-fact');
        const lastChip = factChips[visibleFactsCount - 1] as HTMLElement | undefined;
        if (lastChip) {
          const rect = lastChip.getBoundingClientRect();
          if (rect.bottom > viewportHeight - 60) {
            const targetY = scrollY + rect.bottom - viewportHeight + 80;
            scrollToTargetY(targetY, 340);
          }
        }
      }
    }, 40);

    return () => window.clearTimeout(t);
  }, [visibleFactsCount, visibleAnglesCount, visibleSegmentsCount, totalSegments, prefersReducedMotion, scrollToTargetY]);

  // Check tab scroll overflow on mount / resize / segment reveal
  useEffect(() => {
    checkTabsScroll();
    const t1 = window.setTimeout(checkTabsScroll, 60);
    const t2 = window.setTimeout(checkTabsScroll, 250);
    window.addEventListener('resize', checkTabsScroll);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.removeEventListener('resize', checkTabsScroll);
    };
  }, [checkTabsScroll, visibleSegmentsCount, workspace.slots.length]);

  // Active slot and script
  const activeSlot =
    workspace.slots.find((s) => s.id === workspace.activeSlotId) || workspace.slots[0];
  const activeSlotIndex = workspace.slots.findIndex((s) => s.id === activeSlot?.id);
  const activeDoc = activeSlot?.script;
  const activeRev = activeDoc ? activeDoc.revisions[activeDoc.cursor] : null;

  const totalVisibleSlots = Math.min(workspace.slots.length, Math.max(1, visibleSegmentsCount));
  const currentSlotIndex = Math.max(0, activeSlotIndex);

  function handleCyclePersona(direction: -1 | 1) {
    if (totalVisibleSlots <= 1) return;
    const nextIdx = (currentSlotIndex + direction + totalVisibleSlots) % totalVisibleSlots;
    const nextSlot = workspace.slots[nextIdx];
    if (nextSlot) {
      dispatch({ type: 'SET_ACTIVE_SLOT', slotId: nextSlot.id });
    }
  }

  const isRewritingActiveScript = Boolean(activeSlot && rewritingSlotIds.has(activeSlot.id));
  const isScriptUpdating =
    isRegeneratingStale ||
    isRewritingActiveScript ||
    Boolean(activeDoc?.pending);

  // Staleness calculations
  const fHash = factsHash(workspace.facts);
  const originalFactsHash = factsHash(
    workspace.facts.filter((f) => f.original !== null).map((f) => ({ ...f, text: f.original! })),
  );
  const factsAreChanged = fHash !== originalFactsHash;
  const staleSlotsCount = workspace.slots.filter((s) => slotNeedsRegen(workspace, s)).length;
  const activeStaleReasons = activeSlot ? scriptStaleReasons(workspace, activeSlot) : [];

  // Keyboard navigation for segment tabs
  function handleTabKey(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    const count = workspace.slots.length;
    let next = index;
    if (e.key === 'ArrowRight') next = (index + 1) % count;
    else if (e.key === 'ArrowLeft') next = (index - 1 + count) % count;
    else return;
    e.preventDefault();
    const nextSlot = workspace.slots[next];
    if (nextSlot) {
      dispatch({ type: 'SET_ACTIVE_SLOT', slotId: nextSlot.id });
      tabRefs.current[next]?.focus();
    }
  }

  // Reason & Line bi-directional highlighting
  const [hoverReasonIndex, setHoverReasonIndex] = useState<number | null>(null);
  const [hoverLineUid, setHoverLineUid] = useState<Uid | null>(null);
  const [recentlyChangedUids, setRecentlyChangedUids] = useState<Set<Uid>>(new Set());

  // Global ESC key deselects any active selection (line or reason)
  useEffect(() => {
    function handleGlobalKeyDown(e: globalThis.KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        dispatch({ type: 'SELECT_NONE' });
        setHoverReasonIndex(null);
        setHoverLineUid(null);
        if (document.activeElement instanceof HTMLElement) {
          document.activeElement.blur();
        }
      }
    }
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  // Deselect pinned reason when clicking outside the workbench
  useEffect(() => {
    if (workspace.selection.kind !== 'reason') return;

    function handlePointerDown(e: PointerEvent) {
      const wb = workbenchRef.current;
      if (!wb) return;
      if (e.target instanceof Node && wb.contains(e.target)) {
        return;
      }
      dispatch({ type: 'SELECT_NONE' });
    }

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [workspace.selection.kind]);

  const markChanged = (uidToMark: Uid) => {
    setRecentlyChangedUids((prev) => new Set([...prev, uidToMark]));
    setTimeout(() => {
      setRecentlyChangedUids((prev) => {
        const next = new Set(prev);
        next.delete(uidToMark);
        return next;
      });
    }, 600);
  };

  const pinnedReasonIndex =
    workspace.selection.kind === 'reason' && activeRev
      ? (() => {
          const idx = activeRev.reasons.findIndex(
            (r) => r.uid === (workspace.selection as { reasonUid: Uid }).reasonUid,
          );
          return idx !== -1 ? idx : null;
        })()
      : null;

  const focusedReasonIndex = hoverReasonIndex ?? pinnedReasonIndex;

  // Lit line UIDs from focused reason
  const litLineUids = new Set<Uid>();
  if (focusedReasonIndex !== null && activeRev?.reasons[focusedReasonIndex]) {
    const r = activeRev.reasons[focusedReasonIndex];
    const cover = resolveVisibleCover(activeDoc, r.cites);
    if (cover) {
      cover.coverNodes.forEach((node) => {
        collectVisibleUids(node).forEach((id) => litLineUids.add(id));
      });
    }
  }

  // Lit reason indexes from hovered or selected line
  const litReasonIndexes = new Set<number>();
  const activeLineUid = hoverLineUid ?? (workspace.selection.kind === 'line' ? workspace.selection.uid : null);
  if (activeLineUid && activeRev) {
    activeRev.reasons.forEach((r, idx) => {
      const cover = resolveVisibleCover(activeDoc, r.cites);
      if (cover) {
        const lineIdsInCover = cover.coverNodes.flatMap(collectVisibleUids);
        if (lineIdsInCover.includes(activeLineUid)) {
          litReasonIndexes.add(idx);
        }
      }
    });
  } else if (focusedReasonIndex !== null) {
    litReasonIndexes.add(focusedReasonIndex);
  }

  // Active Scope
  const activeScope = getActiveScope(workspace);

  // Saved snapshot checking
  const activeLines = getActiveLines(activeDoc);
  const isCurrentSaved = activeSlot
    ? isSaved(
        factsHash([
          { id: '', text: JSON.stringify(activeSlot.segment), original: null },
          ...activeLines.map((l) => ({ id: '', text: `${l.node.kind}:${l.text}`, original: null })),
        ]),
      )
    : false;

  // --- Action Handlers ---

  async function handleSegmentRefresh(slot: SegmentSlot) {
    if (isRateLimited()) {
      addToast('Slow down. Too many requests in 1 minute. Try again later.', undefined, undefined, true);
      return;
    }
    recordRequest();

    dispatch({ type: 'REPLACE_SEGMENT_START', slotId: slot.id });
    const others = workspace.slots.filter((s) => s.id !== slot.id).map((s) => s.segment);
    const factsList = workspace.facts.map((f) => f.text);

    try {
      const newSeg = await regenerateSegment(slot.segment, others, factsList);
      dispatch({ type: 'REPLACE_SEGMENT_SUCCESS', slotId: slot.id, segment: newSeg });
      addToast(
        `Segment replaced with “${newSeg.name}”`,
        () => dispatch({ type: 'REPLACE_SEGMENT_UNDO', slotId: slot.id }),
        'Undo',
      );

      // Auto-trigger script generation for the new segment
      handleRewriteScript(slot.id, newSeg, true);
    } catch (err: unknown) {
      dispatch({ type: 'REPLACE_SEGMENT_FAIL', slotId: slot.id });
      const msg = err instanceof Error ? err.message : 'Failed to regenerate segment';
      addToast(msg, undefined, undefined, true);
    }
  }

  async function handleRewriteScript(slotId: Uid, segOverride?: Segment, skipRateLimitCheck = false) {
    const slot = workspace.slots.find((s) => s.id === slotId);
    if (!slot) return;

    if (rewritingSlotIds.has(slotId)) return;

    if (!skipRateLimitCheck && isRateLimited()) {
      addToast('Slow down. Too many requests in 1 minute. Try again later.', undefined, undefined, true);
      return;
    }
    if (!skipRateLimitCheck) {
      recordRequest();
    }

    setRewritingSlotIds((prev) => new Set([...prev, slotId]));
    dispatch({ type: 'REWRITE_SCRIPT_START', slotId });
    try {
      const factsList = workspace.facts.map((f) => f.text);
      const newScript = await rewriteScript(segOverride || slot.segment, factsList);
      dispatch({ type: 'REWRITE_SCRIPT_SUCCESS', slotId, script: newScript });
      addToast('Script rewritten for current segment');
    } catch (err: unknown) {
      dispatch({ type: 'REWRITE_SCRIPT_FAIL', slotId });
      const msg = err instanceof Error ? err.message : 'Failed to rewrite script';
      addToast(msg, undefined, undefined, true);
    } finally {
      setRewritingSlotIds((prev) => {
        const next = new Set(prev);
        next.delete(slotId);
        return next;
      });
    }
  }

  async function handleRegenerateStale() {
    if (isRegeneratingStale) return;

    if (isRateLimited()) {
      addToast('Slow down. Too many requests in 1 minute. Try again later.', undefined, undefined, true);
      return;
    }

    const staleSlots = workspace.slots.filter((s) => slotNeedsRegen(workspace, s));
    if (staleSlots.length === 0) return;

    setIsRegeneratingStale(true);
    recordRequest();
    try {
      await Promise.all(staleSlots.map((s) => handleRewriteScript(s.id, undefined, true)));
    } finally {
      setIsRegeneratingStale(false);
    }
  }

  async function handleReasonRefresh(reasonUid: Uid) {
    if (!activeRev) return;
    const reason = activeRev.reasons.find((r) => r.uid === reasonUid);
    if (!reason || !activeDoc) return;

    if (isRateLimited()) {
      addToast('Slow down. Too many requests in 1 minute. Try again later.', undefined, undefined, true);
      return;
    }
    recordRequest();

    dispatch({ type: 'SELECT_REASON', reasonUid });
    dispatch({ type: 'REWRITE_REASON_START', reasonUid });

    const cover = resolveVisibleCover(activeDoc, reason.cites);
    if (!cover) {
      dispatch({ type: 'REWRITE_REASON_FAIL', reasonUid });
      return;
    }

    const visibleUids = cover.coverNodes.flatMap(collectVisibleUids);
    const linesToRewrite = getActiveLines(activeDoc)
      .filter((l) => visibleUids.includes(l.node.uid))
      .map((l) => ({ kind: l.node.kind, text: l.text }));

    const fullScript = activeLines.map((l, idx) => ({
      id: idx + 1,
      kind: l.node.kind,
      text: l.text,
    }));
    const targetLineIds = activeLines
      .map((l, idx) => (visibleUids.includes(l.node.uid) ? idx + 1 : null))
      .filter((id): id is number => id !== null);
    const factsList = workspace.facts.map((f) => f.text);

    try {
      const newLines = await rewriteReasonLines(
        reason.title,
        reason.why,
        linesToRewrite,
        {
          segment: activeSlot?.segment,
          facts: factsList,
          fullScript,
          targetLineIds,
        },
      );
      dispatch({ type: 'REWRITE_REASON_SUCCESS', reasonUid, newLines });
      visibleUids.forEach(markChanged);
      addToast(`Lines rewritten for “${reason.title}”`);
    } catch (err: unknown) {
      dispatch({ type: 'REWRITE_REASON_FAIL', reasonUid });
      const msg = err instanceof Error ? err.message : 'Failed to rewrite lines for reason';
      addToast(msg, undefined, undefined, true);
    }
  }

  async function handleRephrase(lineUid: Uid) {
    const line = activeLines.find((l) => l.node.uid === lineUid);
    if (!line) return;

    if (isRateLimited()) {
      addToast('Slow down. Too many requests in 1 minute. Try again later.', undefined, undefined, true);
      return;
    }
    recordRequest();

    dispatch({ type: 'REPHRASE_LINE_START', lineUid });

    const lineIdx = activeLines.findIndex((l) => l.node.uid === lineUid);
    const lineId = lineIdx !== -1 ? lineIdx + 1 : 1;
    const scriptContext = activeLines.map((l, idx) => ({
      id: idx + 1,
      kind: l.node.kind,
      text: l.text,
    }));
    const avoidTones = line.node.versions
      .map((v) => v.detail)
      .filter((d): d is string => Boolean(d));
    const factsList = workspace.facts.map((f) => f.text);

    try {
      const res = await rephraseLine(line.text, line.node.kind, {
        segment: activeSlot?.segment,
        facts: factsList,
        scriptContext,
        lineId,
        avoidTones,
      });
      dispatch({
        type: 'REPHRASE_LINE_SUCCESS',
        lineUid,
        text: res.text,
        tone: res.tone,
      });
      markChanged(lineUid);
    } catch (err: unknown) {
      dispatch({ type: 'LINE_ACTION_FAIL', lineUid });
      const msg = err instanceof Error ? err.message : 'Failed to rephrase line';
      addToast(msg, undefined, undefined, true);
    }
  }

  async function handleRegenerateLine(lineUid: Uid) {
    const line = activeLines.find((l) => l.node.uid === lineUid);
    if (!line) return;

    if (isRateLimited()) {
      addToast('Slow down. Too many requests in 1 minute. Try again later.', undefined, undefined, true);
      return;
    }
    recordRequest();

    dispatch({ type: 'REGENERATE_LINE_START', lineUid });

    const lineIdx = activeLines.findIndex((l) => l.node.uid === lineUid);
    const lineId = lineIdx !== -1 ? lineIdx + 1 : 1;
    const scriptContext = activeLines.map((l, idx) => ({
      id: idx + 1,
      kind: l.node.kind,
      text: l.text,
    }));
    const factsList = workspace.facts.map((f) => f.text);

    try {
      const newText = await regenerateLine(line.text, line.node.kind, {
        segment: activeSlot?.segment,
        facts: factsList,
        scriptContext,
        lineId,
      });
      dispatch({ type: 'REGENERATE_LINE_SUCCESS', lineUid, text: newText });
      markChanged(lineUid);
    } catch (err: unknown) {
      dispatch({ type: 'LINE_ACTION_FAIL', lineUid });
      const msg = err instanceof Error ? err.message : 'Failed to regenerate line';
      addToast(msg, undefined, undefined, true);
    }
  }

  function handleSaveCurrentScript() {
    if (!activeSlot || !activeDoc || !activeRev) return;
    const linesToSave = activeLines.map((l) => ({ kind: l.node.kind, text: l.text }));
    const reasonsToSave = activeRev.reasons.map((r) => {
      const cover = resolveVisibleCover(activeDoc, r.cites);
      const uids = cover ? cover.coverNodes.flatMap(collectVisibleUids) : [];
      const lineNumbers = activeLines
        .map((l, idx) => (uids.includes(l.node.uid) ? idx + 1 : null))
        .filter((n): n is number => n !== null);
      return { title: r.title, why: r.why, lines: lineNumbers };
    });

    const saved = save({
      product: workspace.meta.name || 'Product',
      market: workspace.meta.market || 'Global',
      language: workspace.meta.language || 'en',
      segment: activeSlot.segment,
      lines: linesToSave,
      reasons: reasonsToSave,
    });

    addToast(`Saved “${activeSlot.segment.name}” script`, () => removeSaved(saved.id), 'Undo');
  }

  // Reasons display items
  const reasonDisplayItems: ReasonDisplayItem[] = (activeRev?.reasons || []).map((r) => {
    const cover = resolveVisibleCover(activeDoc, r.cites);
    const visibleUids = cover ? cover.coverNodes.flatMap(collectVisibleUids) : [];
    const refs = activeLines
      .map((l, idx) => (visibleUids.includes(l.node.uid) ? { no: idx + 1, kind: l.node.kind } : null))
      .filter((ref): ref is { no: number; kind: LineKind } => ref !== null);

    return {
      uid: r.uid,
      title: r.title,
      why: r.why,
      refs,
      orphan: refs.length === 0,
      pending:
        Boolean(r.pending) ||
        (workspace.selection.kind === 'reason' &&
          workspace.selection.reasonUid === r.uid &&
          Boolean(cover?.coverNodes.some((n) => n.type === 'group' && n.pending))),
    };
  });

  return (
    <div className="results">
      {/* 1. Facts Section */}
      {workspace.facts.length > 0 && (
        <section className="results-section">
          <div className="section-head">
            <h2>Facts the scripts rely on</h2>
            <p>Pulled from your description and photo. The scripts only use these.</p>
          </div>

          <FactChips
            facts={workspace.facts.slice(0, visibleFactsCount)}
            onEdit={(id, text) => dispatch({ type: 'EDIT_FACT', id, text })}
            onRemove={(id) => {
              const removed = workspace.facts.find((f) => f.id === id);
              dispatch({ type: 'REMOVE_FACT', id });
              if (removed) {
                addToast(
                  `Fact removed: “${removed.text.slice(0, 24)}…”`,
                  () => dispatch({ type: 'ADD_FACT', text: removed.text }),
                  'Undo',
                );
              }
            }}
            onAdd={(text) => dispatch({ type: 'ADD_FACT', text })}
          />

          <Collapse open={factsAreChanged}>
            <StaleBar
              busy={isRegeneratingStale}
              actions={[
                {
                  label: 'Reset facts',
                  onClick: () => dispatch({ type: 'RESET_FACTS' }),
                },
                {
                  label: isRegeneratingStale ? 'Regenerating…' : 'Regenerate',
                  primary: true,
                  loading: isRegeneratingStale,
                  onClick: handleRegenerateStale,
                },
              ]}
            >
              Facts have been updated. Existing customer segments and scripts are based on earlier facts.
            </StaleBar>
          </Collapse>
        </section>
      )}

      {/* 1b. Creative Angles Section */}
      {workspace.angles && workspace.angles.length > 0 && visibleAnglesCount > 0 && (
        <section className="results-section">
          <div className="section-head">
            <h2>Creative angles</h2>
            <p>
              Hooks, objection handling, and psychological moments connecting product facts to buyer motivations.
            </p>
          </div>
          <AngleChips angles={workspace.angles.slice(0, visibleAnglesCount)} />
        </section>
      )}

      {/* 2. Customer Segments Section */}
      {workspace.slots.length > 0 && visibleSegmentsCount > 0 && (
        <section
          ref={segmentSectionRef}
          className="results-section segment-section-animated"
          data-stale={staleSlotsCount > 0 ? '' : undefined}
        >
          <div className="section-head">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <h2>Customer segments</h2>
              {staleSlotsCount > 0 && (
                <span className="hint" style={{ fontSize: '0.8125rem' }}>
                  ({staleSlotsCount} of {workspace.slots.length} based on earlier facts)
                </span>
              )}
            </div>
            <p>
              Auto-generated target demographics based on your product details. Each segment has its
              own tailored script—switch between them without waiting.
            </p>
          </div>

          {/* Segment Tabs */}
          <div className="tabs-wrap">
            <div
              ref={tabsContainerRef}
              onScroll={checkTabsScroll}
              className="tabs"
              role="tablist"
              aria-label="Customer segments"
            >
              {workspace.slots.slice(0, visibleSegmentsCount).map((slot, i) => {
                const isReady = slot.scriptStatus === 'ready';
                const isOutdated = slotNeedsRegen(workspace, slot);

                return (
                  <SegmentTab
                    key={slot.id}
                    index={i}
                    name={slot.segment.name}
                    active={workspace.activeSlotId === slot.id}
                    outdated={isOutdated}
                    generating={isStreaming && !isReady}
                    replacing={Boolean(slot.pending)}
                    tabId={`${uid}-tab-${i}`}
                    panelId={`${uid}-panel`}
                    tabRef={(el) => {
                      tabRefs.current[i] = el;
                    }}
                    onSelect={() => dispatch({ type: 'SET_ACTIVE_SLOT', slotId: slot.id })}
                    onKeyDown={(e) => handleTabKey(e, i)}
                    onRefresh={() => handleSegmentRefresh(slot)}
                  />
                );
              })}
            </div>

            {canScrollTabsRight && (
              <button
                type="button"
                className="tabs-scroll-chevron"
                aria-label="Scroll more customer segments right"
                onClick={scrollTabsRight}
              >
                <IconChevronRight size={18} aria-hidden="true" />
              </button>
            )}
          </div>

          {/* Segment Panel */}
          <div
            className="tab-panel"
            role="tabpanel"
            id={`${uid}-panel`}
            aria-labelledby={`${uid}-tab-${activeSlotIndex}`}
          >
            {activeSlot && (
              <SegmentCard
                segment={activeSlot.segment}
                angles={workspace.angles}
                edited={activeSlot.edited}
                isSaved={isCurrentSaved}
                canSave={Boolean(activeDoc && !activeDoc.pending)}
                onSave={handleSaveCurrentScript}
                onEdit={(newSeg) =>
                  dispatch({ type: 'EDIT_SEGMENT', slotId: activeSlot.id, segment: newSeg })
                }
              />
            )}

            {/* Workbench Stale Bar */}
            {activeStaleReasons.length > 0 && (
              <StaleBar
                busy={isRewritingActiveScript}
                actions={[
                  {
                    label: 'Keep as is',
                    onClick: () =>
                      dispatch({ type: 'KEEP_SCRIPT_AS_IS', slotId: activeSlot.id }),
                  },
                  {
                    label: isRewritingActiveScript ? 'Rewriting…' : 'Rewrite script',
                    primary: true,
                    loading: isRewritingActiveScript,
                    onClick: () => handleRewriteScript(activeSlot.id),
                  },
                ]}
              >
                {scriptStaleMessage(activeStaleReasons, Boolean(activeSlot?.previous))}
              </StaleBar>
            )}

            {/* Script & Reasoning Workbench */}
            {activeDoc ? (
              <div
                ref={workbenchRef}
                className={`workbench${isScriptUpdating ? ' is-updating' : ''}`}
              >
                <ScriptCard
                  doc={activeDoc}
                  scope={activeScope}
                  selectedLineUid={
                    workspace.selection.kind === 'line' ? workspace.selection.uid : null
                  }
                  litLineUids={litLineUids}
                  hoveredLineUid={hoverLineUid}
                  reasonFocused={focusedReasonIndex !== null}
                  recentlyChangedUids={recentlyChangedUids}
                  personaInfo={{
                    current: currentSlotIndex + 1,
                    total: totalVisibleSlots,
                    name: activeSlot?.segment.name || 'Segment',
                    onPrev: () => handleCyclePersona(-1),
                    onNext: () => handleCyclePersona(1),
                  }}
                  onLineHover={setHoverLineUid}
                  onLineSelect={(lineUid) =>
                    lineUid
                      ? dispatch({ type: 'SELECT_LINE', uid: lineUid })
                      : dispatch({ type: 'SELECT_NONE' })
                  }
                  onEditLine={(lineUid, text) => {
                    dispatch({ type: 'EDIT_LINE', lineUid, text });
                    markChanged(lineUid);
                  }}
                  onRephraseLine={handleRephrase}
                  onRegenerateLine={handleRegenerateLine}
                  onUndoLine={(lineUid) =>
                    dispatch({ type: 'UNDO_LINE', lineUid })
                  }
                  onRedoLine={(lineUid) =>
                    dispatch({ type: 'REDO_LINE', lineUid })
                  }
                  onDeleteLine={(lineUid) =>
                    dispatch({ type: 'DELETE_LINE', lineUid })
                  }
                  onStepScope={(delta) =>
                    dispatch({ type: 'STEP_SCOPE', delta })
                  }
                />

                <ReasonList
                  items={reasonDisplayItems}
                  litIndexes={litReasonIndexes}
                  pinnedIndex={pinnedReasonIndex}
                  onHover={(idx) => setHoverReasonIndex(idx)}
                  onPin={(idx) => {
                    const reason = activeRev?.reasons[idx];
                    if (!reason) return;
                    if (
                      workspace.selection.kind === 'reason' &&
                      workspace.selection.reasonUid === reason.uid
                    ) {
                      dispatch({ type: 'SELECT_NONE' });
                    } else {
                      dispatch({
                        type: 'SELECT_REASON',
                        reasonUid: reason.uid,
                      });
                    }
                  }}
                  onRefresh={handleReasonRefresh}
                />
              </div>
            ) : isStreaming ? (
              <div className="panel script-skeleton-card">
                <div className="script-skeleton-head">
                  <span className="rec-dot" aria-hidden="true" />
                  <h3>Writing script for {activeSlot?.segment?.name ?? 'segment'}…</h3>
                </div>
                <p className="hint">Crafting hook, timestamped lines, and psychological reasoning…</p>
                <div className="skeleton" aria-hidden="true">
                  <span style={{ height: '20px', width: '92%' }} />
                  <span style={{ height: '20px', width: '78%' }} />
                  <span style={{ height: '20px', width: '85%' }} />
                  <span style={{ height: '20px', width: '60%' }} />
                </div>
              </div>
            ) : (
              <p className="hint">No script came back for this segment. Try generating again.</p>
            )}
          </div>
        </section>
      )}

      {/* Floating Notifications */}
      <ToastHost toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
