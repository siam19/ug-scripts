// apps/web/src/hooks/useGoogleDocsExport.ts
import { useCallback, useState } from 'react';
import {
  downloadMarkdownDocument,
  exportScriptToGoogleDocs,
} from '../lib/googleDocs';
import type {
  ExportScriptPayload,
  GoogleDocExportResult,
} from '../lib/googleDocs';

export function useGoogleDocsExport() {
  const [exporting, setExporting] = useState(false);
  const [exportingKey, setExportingKey] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<GoogleDocExportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const exportToDocs = useCallback(
    async (
      payload: ExportScriptPayload,
      key?: string,
    ): Promise<GoogleDocExportResult | null> => {
      if (exporting) return null;
      setExporting(true);
      setExportingKey(key ?? null);
      setError(null);
      try {
        const result = await exportScriptToGoogleDocs(payload);
        setLastResult(result);
        return result;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to export to Google Docs.';
        setError(msg);
        throw new Error(msg);
      } finally {
        setExporting(false);
        setExportingKey(null);
      }
    },
    [exporting],
  );

  const downloadMarkdown = useCallback((payload: ExportScriptPayload): string => {
    return downloadMarkdownDocument(payload);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return {
    exporting,
    exportingKey,
    lastResult,
    error,
    exportToDocs,
    downloadMarkdown,
    clearError,
  };
}
