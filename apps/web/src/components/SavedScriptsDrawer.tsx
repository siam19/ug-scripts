import { useEffect, useState } from 'react';
import {
  IconCheck,
  IconChevronDown,
  IconChevronUp,
  IconCopy,
  IconDownload,
  IconExternalLink,
  IconFileText,
  IconLoader2,
  IconTrash,
  IconX,
} from '@tabler/icons-react';
import { useGoogleDocsExport } from '../hooks/useGoogleDocsExport';
import type { ExportScriptPayload, GoogleDocExportResult } from '../lib/googleDocs';
import type { SavedScript } from '../state/saved-scripts';
import { countWords, formatTime, SECONDS_PER_WORD } from '../state/script-tree';

interface Props {
  open: boolean;
  scripts: SavedScript[];
  onClose: () => void;
  onRemove: (id: string) => void;
  onCopyNotice?: () => void;
}

function savedScriptToExportPayload(script: SavedScript): ExportScriptPayload {
  let cursorTime = 0;
  const lines = script.lines.map((line, idx) => {
    const words = countWords(line.text);
    const duration = Math.max(words * SECONDS_PER_WORD, 0.8);
    const time = formatTime(cursorTime);
    cursorTime += duration;
    return {
      no: idx + 1,
      kind: line.kind,
      time,
      text: line.text,
    };
  });

  return {
    product: script.product,
    market: script.market,
    language: script.language,
    segment: script.segment,
    lines,
    reasons: script.reasons,
  };
}

export function SavedScriptsDrawer({
  open,
  scripts,
  onClose,
  onRemove,
  onCopyNotice,
}: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [exportedDocs, setExportedDocs] = useState<Record<string, GoogleDocExportResult>>({});
  const [exportErrors, setExportErrors] = useState<Record<string, string>>({});
  const { exporting, exportingKey, exportToDocs, downloadMarkdown } = useGoogleDocsExport();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  async function handleCopy(script: SavedScript) {
    const text = script.lines.map((l) => l.text).join('\n\n');
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(script.id);
      onCopyNotice?.();
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // fallback
    }
  }

  async function handleExportGoogleDocs(script: SavedScript) {
    setExportErrors((prev) => {
      const next = { ...prev };
      delete next[script.id];
      return next;
    });
    try {
      const result = await exportToDocs(savedScriptToExportPayload(script), script.id);
      if (result) {
        setExportedDocs((prev) => ({ ...prev, [script.id]: result }));
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to export to Google Docs.';
      setExportErrors((prev) => ({ ...prev, [script.id]: msg }));
    }
  }

  function handleDownloadMarkdown(script: SavedScript) {
    downloadMarkdown(savedScriptToExportPayload(script));
  }

  return (
    <>
      <div
        className="drawer-backdrop"
        aria-hidden="true"
        onClick={onClose}
      />
      <aside
        className="drawer"
        role="dialog"
        aria-label="Saved scripts"
        aria-modal="true"
      >
        <header className="drawer-head">
          <h3>Saved Scripts ({scripts.length})</h3>
          <button
            type="button"
            className="drawer-close"
            aria-label="Close saved scripts"
            onClick={onClose}
          >
            <IconX size={20} aria-hidden="true" />
          </button>
        </header>

        <div className="drawer-body">
          {scripts.length === 0 ? (
            <p className="hint">
              Save a script from any customer segment card. Saved scripts stay here
              even if you regenerate or edit segments.
            </p>
          ) : (
            scripts.map((script) => {
              const isExpanded = expandedId === script.id;
              const dateStr = new Date(script.savedAt).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
              });

              const firstHook =
                script.lines.find((l) => l.kind === 'hook')?.text ||
                script.lines[0]?.text ||
                '';

              return (
                <div key={script.id} className="saved-accordion">
                  <button
                    type="button"
                    className="saved-item-header"
                    onClick={() => setExpandedId(isExpanded ? null : script.id)}
                  >
                    <div className="saved-item-title">
                      <span>
                        {script.segment.name} · {script.product}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="hint" style={{ fontSize: '0.75rem' }}>
                          {dateStr}
                        </span>
                        {isExpanded ? (
                          <IconChevronUp size={16} aria-hidden="true" />
                        ) : (
                          <IconChevronDown size={16} aria-hidden="true" />
                        )}
                      </div>
                    </div>
                    {!isExpanded && (
                      <p className="saved-item-hook">&ldquo;{firstHook}&rdquo;</p>
                    )}
                  </button>

                  {isExpanded && (
                    <div className="saved-item-body">
                      <div className="saved-lines-preview">
                        {script.lines.map((line, idx) => (
                          <div key={idx} className="saved-line-row">
                            <span className="kind">{line.kind}</span>
                            <span className="ln-text" style={{ fontSize: '0.9375rem' }}>
                              {line.text}
                            </span>
                          </div>
                        ))}
                      </div>

                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                        {script.reasons.map((r, idx) => (
                          <span
                            key={idx}
                            className="tag"
                            style={{ fontSize: '0.75rem' }}
                            title={r.why}
                          >
                            {r.title}
                          </span>
                        ))}
                      </div>

                      <div className="saved-item-actions">
                        <button
                          type="button"
                          className="btn btn-sm btn-quiet"
                          onClick={() => onRemove(script.id)}
                        >
                          <IconTrash size={14} aria-hidden="true" />
                          <span>Remove</span>
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-quiet"
                          onClick={() => handleDownloadMarkdown(script)}
                          title="Download script as Markdown (.md)"
                        >
                          <IconDownload size={14} aria-hidden="true" />
                          <span>.md</span>
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-quiet"
                          disabled={exporting}
                          onClick={() => handleExportGoogleDocs(script)}
                          title="Export script to Google Docs"
                        >
                          {exporting && exportingKey === script.id ? (
                            <>
                              <IconLoader2 size={14} className="export-spinner" aria-hidden="true" />
                              <span>Exporting…</span>
                            </>
                          ) : (
                            <>
                              <IconFileText size={14} aria-hidden="true" />
                              <span>Google Docs</span>
                            </>
                          )}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-primary"
                          onClick={() => handleCopy(script)}
                        >
                          {copiedId === script.id ? (
                            <>
                              <IconCheck size={14} aria-hidden="true" />
                              <span>Copied!</span>
                            </>
                          ) : (
                            <>
                              <IconCopy size={14} aria-hidden="true" />
                              <span>Copy script</span>
                            </>
                          )}
                        </button>
                      </div>

                      {exportedDocs[script.id] && (
                        <div className="saved-export-status is-success" role="status">
                          <span>Exported to Google Docs</span>
                          <a
                            href={exportedDocs[script.id].url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="saved-export-link"
                          >
                            <span>Open Doc</span>
                            <IconExternalLink size={13} aria-hidden="true" />
                          </a>
                        </div>
                      )}

                      {exportErrors[script.id] && (
                        <div className="saved-export-status is-error" role="alert">
                          <span>{exportErrors[script.id]}</span>
                          <button
                            type="button"
                            className="saved-export-dismiss"
                            aria-label="Dismiss export error"
                            onClick={() =>
                              setExportErrors((prev) => {
                                const next = { ...prev };
                                delete next[script.id];
                                return next;
                              })
                            }
                          >
                            <IconX size={13} aria-hidden="true" />
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </aside>
    </>
  );
}
