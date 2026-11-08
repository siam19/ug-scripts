import { useCallback, useEffect, useState } from 'react';
import type { LineKind, Segment } from 'api-types';
import { hash } from './hash';
import type { Uid } from './types';
import { generateUid } from './uid';

const STORAGE_KEY = 'ug-scripts:saved:v1';
const MAX_SAVED = 50;

export interface SavedScript {
  id: Uid;
  savedAt: number;
  hash: string;
  product: string;
  market: string;
  language: 'en' | 'bn';
  segment: Segment;
  lines: { kind: LineKind; text: string }[];
  reasons: { title: string; why: string; lines: number[] }[];
}

export function computeScriptSnapshotHash(
  segment: Segment,
  lines: { kind: LineKind; text: string }[],
): string {
  const segPart = JSON.stringify([
    segment.name.trim(),
    segment.who.trim(),
    segment.pain_point.trim(),
    [...segment.platforms].sort(),
  ]);
  const linesPart = lines.map((l) => `${l.kind}:${l.text.trim()}`).join('\n');
  return hash(`${segPart}\n---\n${linesPart}`);
}

function loadFromStorage(): SavedScript[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveToStorage(list: SavedScript[]) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, MAX_SAVED)));
  } catch {
    // quota exceeded or private mode
  }
}

export function useSavedScripts() {
  const [savedScripts, setSavedScripts] = useState<SavedScript[]>(loadFromStorage);

  useEffect(() => {
    function handleStorage(e: StorageEvent) {
      if (e.key === STORAGE_KEY) {
        setSavedScripts(loadFromStorage());
      }
    }
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const save = useCallback(
    (item: Omit<SavedScript, 'id' | 'savedAt' | 'hash'>): SavedScript => {
      const snapHash = computeScriptSnapshotHash(item.segment, item.lines);
      const newSaved: SavedScript = {
        ...item,
        id: generateUid(),
        savedAt: Date.now(),
        hash: snapHash,
      };

      setSavedScripts((prev) => {
        const next = [newSaved, ...prev.filter((s) => s.hash !== snapHash)].slice(
          0,
          MAX_SAVED,
        );
        saveToStorage(next);
        return next;
      });

      return newSaved;
    },
    [],
  );

  const remove = useCallback((id: Uid) => {
    setSavedScripts((prev) => {
      const next = prev.filter((s) => s.id !== id);
      saveToStorage(next);
      return next;
    });
  }, []);

  const isSaved = useCallback(
    (snapHash: string) => savedScripts.some((s) => s.hash === snapHash),
    [savedScripts],
  );

  return { savedScripts, save, remove, isSaved };
}
