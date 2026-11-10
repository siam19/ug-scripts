// apps/web/src/components/DemoProductPicker.tsx
import { useCallback, useEffect, useId, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { IconCheck, IconChevronDown, IconChevronLeft, IconChevronRight } from '@tabler/icons-react';
import type { DemoProduct } from 'api-types';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

interface Props {
  onSelect: (product: DemoProduct) => void;
  selectedId?: string;
}

function LangChip({ lang }: { lang: string }) {
  const bn = lang === 'bn';
  return (
    <span className={`shelf-lang${bn ? ' is-bn' : ''}`} lang={bn ? 'bn' : 'en'}>
      {bn ? 'বাংলা' : 'EN'}
    </span>
  );
}

/**
 * "Sample shelf": a slim bar that fans out thumbnails of the samples. Opening it shows a floating
 * sheet with a horizontal rail of poster cards, so the form below never gets pushed down.
 */
export function DemoProductPicker({ onSelect, selectedId }: Props) {
  const sheetId = useId();
  const [open, setOpen] = useState(false);
  const [products, setProducts] = useState<DemoProduct[]>([]);
  const [category, setCategory] = useState('All');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const wrapRef = useRef<HTMLDivElement>(null);
  const barRef = useRef<HTMLButtonElement>(null);
  const railRef = useRef<HTMLDivElement>(null);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  // Fetched on mount (not on open) so the collapsed bar can show real thumbnails.
  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/demo-products`);
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data = (await res.json()) as { products?: DemoProduct[] };
      if (alive.current && Array.isArray(data.products)) setProducts(data.products);
    } catch {
      if (alive.current) {
        setError('Could not load sample products. You can still upload your own photo below.');
      }
    } finally {
      if (alive.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    void fetchProducts();
  }, [fetchProducts]);

  // Outside click and Esc close the sheet.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false);
        barRef.current?.focus();
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const categories = ['All', ...Array.from(new Set(products.map((p) => p.category)))];
  const visible = category === 'All' ? products : products.filter((p) => p.category === category);
  const selected = products.find((p) => p.id === selectedId);
  const hasSelection = Boolean(selectedId);

  function scrollRail(dir: -1 | 1) {
    const rail = railRef.current;
    if (!rail) return;
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    rail.scrollBy({ left: dir * rail.clientWidth * 0.8, behavior: smooth ? 'smooth' : 'auto' });
  }

  const stackItems = products.slice(0, 4);

  return (
    <div className="shelf" ref={wrapRef}>
      <button
        ref={barRef}
        type="button"
        className={`shelf-bar${open ? ' is-open' : ''}`}
        aria-expanded={open}
        aria-controls={sheetId}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="shelf-stack" aria-hidden="true">
          {selected ? (
            <img className="shelf-thumb is-main" src={selected.image_url} alt="" />
          ) : stackItems.length > 0 ? (
            stackItems.map((p, i) => (
              <img
                key={p.id}
                className="shelf-thumb"
                src={p.image_url}
                alt=""
                style={{ '--i': i } as CSSProperties}
              />
            ))
          ) : (
            [0, 1, 2].map((i) => (
              <span key={i} className="shelf-thumb is-empty" style={{ '--i': i } as CSSProperties} />
            ))
          )}
        </span>

        <span className="shelf-copy">
          {hasSelection ? (
            <>
              <strong>{selected?.name ?? 'Sample loaded'}</strong>
              <span>Sample product, photo included</span>
            </>
          ) : (
            <>
              <strong>No photo handy?</strong>
              <span>
                {products.length > 0
                  ? `Start from one of ${products.length} sample products`
                  : 'Start from a sample product'}
              </span>
            </>
          )}
        </span>

        <span className="shelf-cta">
          {open ? 'Close' : hasSelection ? 'Change' : 'Browse'}
          <IconChevronDown size={16} aria-hidden="true" />
        </span>
      </button>

      {open && (
        <div className="shelf-sheet" id={sheetId} role="region" aria-label="Sample products">
          <div className="shelf-toolbar">
            {categories.length > 2 ? (
              <div className="shelf-tabs">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    className={`shelf-tab${category === cat ? ' is-active' : ''}`}
                    aria-pressed={category === cat}
                    onClick={() => setCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            ) : (
              <span className="shelf-tabs-empty" />
            )}

            {visible.length > 3 && (
              <div className="shelf-arrows">
                <button type="button" aria-label="Scroll samples left" onClick={() => scrollRail(-1)}>
                  <IconChevronLeft size={16} aria-hidden="true" />
                </button>
                <button type="button" aria-label="Scroll samples right" onClick={() => scrollRail(1)}>
                  <IconChevronRight size={16} aria-hidden="true" />
                </button>
              </div>
            )}
          </div>

          {error && (
            <p className="shelf-error" role="alert">
              {error}{' '}
              <button type="button" className="gate-link" onClick={() => void fetchProducts()}>
                Try again
              </button>
            </p>
          )}

          <div className="shelf-rail" ref={railRef}>
            {loading &&
              [0, 1, 2, 3, 4].map((i) => (
                <div key={i} className="shelf-card is-skeleton" aria-hidden="true">
                  <span className="shelf-photo" />
                  <span className="shelf-name">&nbsp;</span>
                </div>
              ))}

            {!loading &&
              visible.map((p) => {
                const isSelected = selectedId === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    className={`shelf-card${isSelected ? ' is-selected' : ''}`}
                    aria-pressed={isSelected}
                    title={p.description}
                    onClick={() => {
                      onSelect(p);
                      setOpen(false);
                    }}
                  >
                    <span className="shelf-photo">
                      <img
                        src={p.image_url}
                        alt=""
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.style.visibility = 'hidden';
                        }}
                      />
                      <LangChip lang={p.language} />
                      {isSelected && (
                        <span className="shelf-check">
                          <IconCheck size={14} aria-hidden="true" />
                        </span>
                      )}
                    </span>
                    <span className="shelf-name">{p.name}</span>
                    <span className="shelf-meta">{p.category}</span>
                  </button>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
