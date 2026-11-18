// apps/web/src/lib/googleDocs.ts
import type { Angle, LineKind, ScriptFormat, Segment } from 'api-types';

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const GIS_SCRIPT_URL = 'https://accounts.google.com/gsi/client';
const DRIVE_FILE_SCOPE = 'https://www.googleapis.com/auth/drive.file';
const DRIVE_UPLOAD_URL =
  'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink';

export interface ExportScriptLine {
  no: number;
  kind: LineKind;
  time?: string;
  text: string;
  visual?: string | null;
  speaker?: string | null;
}

export interface ExportScriptReason {
  title: string;
  why: string;
  lines: number[];
}

export interface ExportScriptPayload {
  product: string;
  category?: string;
  market: string;
  language: 'en' | 'bn';
  scriptFormat?: ScriptFormat;
  productAppearance?: string;
  facts?: string[];
  angles?: Angle[];
  segment: Segment;
  lines: ExportScriptLine[];
  reasons: ExportScriptReason[];
}

export interface GoogleDocExportResult {
  id: string;
  title: string;
  url: string;
}

interface GisTokenResponse {
  access_token?: string;
  expires_in?: number;
  error?: string;
  error_description?: string;
}

interface GisErrorCallbackArg {
  type?: string;
  message?: string;
}

interface GisTokenClient {
  requestAccessToken: (overrideConfig?: { prompt?: string }) => void;
}

interface GisOAuth2Namespace {
  initTokenClient: (config: {
    client_id: string;
    scope: string;
    callback: (response: GisTokenResponse) => void;
    error_callback?: (error: GisErrorCallbackArg) => void;
  }) => GisTokenClient;
}

declare global {
  interface Window {
    google?: {
      accounts?: {
        oauth2?: GisOAuth2Namespace;
      };
    };
  }
}

let cachedClientId: string | null = null;
let gisLoadPromise: Promise<void> | null = null;
let cachedToken: { accessToken: string; expiresAt: number } | null = null;

export function clearCachedGoogleToken() {
  cachedToken = null;
}

/**
 * Resolves the public Google OAuth Client ID from Vite build env or runtime /auth/config.
 * Only public client ID is ever read on the client; no client secret is used.
 */
export async function getGoogleClientId(): Promise<string> {
  const envClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined)?.trim();
  if (envClientId) {
    return envClientId;
  }
  if (cachedClientId) {
    return cachedClientId;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}/auth/config`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
  } catch {
    throw new Error(
      'Google Docs export is unavailable: could not reach server configuration. Use Download .md instead.',
    );
  }

  if (!res.ok) {
    throw new Error(
      'Google Docs export is not configured on this server. Use Download .md instead.',
    );
  }

  const data = (await res.json()) as { google_client_id?: string };
  const resolved = data.google_client_id?.trim() ?? '';
  if (!resolved) {
    throw new Error(
      'Google OAuth Client ID is missing. Configure VITE_GOOGLE_CLIENT_ID or use Download .md instead.',
    );
  }

  cachedClientId = resolved;
  return resolved;
}

/**
 * Loads Google Identity Services (GIS) client script dynamically on demand.
 */
export function loadGisClient(): Promise<void> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('Google sign-in requires a browser environment.'));
  }
  if (window.google?.accounts?.oauth2) {
    return Promise.resolve();
  }
  if (gisLoadPromise) {
    return gisLoadPromise;
  }

  gisLoadPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${GIS_SCRIPT_URL}"]`,
    );
    if (existing) {
      if (window.google?.accounts?.oauth2) {
        resolve();
        return;
      }
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener(
        'error',
        () => {
          gisLoadPromise = null;
          reject(new Error('Failed to load Google Sign-In script. Check your network connection.'));
        },
        { once: true },
      );
      return;
    }

    const script = document.createElement('script');
    script.src = GIS_SCRIPT_URL;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (window.google?.accounts?.oauth2) {
        resolve();
      } else {
        gisLoadPromise = null;
        reject(new Error('Google Sign-In loaded, but OAuth2 client is unavailable.'));
      }
    };
    script.onerror = () => {
      gisLoadPromise = null;
      reject(new Error('Failed to load Google Sign-In script. Check your network connection.'));
    };
    document.head.appendChild(script);
  });

  return gisLoadPromise;
}

function requestAccessToken(clientId: string): Promise<string> {
  if (cachedToken && Date.now() < cachedToken.expiresAt - 30_000) {
    return Promise.resolve(cachedToken.accessToken);
  }

  const oauth2 = window.google?.accounts?.oauth2;
  if (!oauth2) {
    return Promise.reject(new Error('Google OAuth2 client is not loaded.'));
  }

  return new Promise<string>((resolve, reject) => {
    const client = oauth2.initTokenClient({
      client_id: clientId,
      scope: DRIVE_FILE_SCOPE,
      callback: (resp) => {
        if (resp.error || !resp.access_token) {
          if (resp.error === 'access_denied') {
            reject(new Error('Google Drive permission was denied.'));
          } else {
            reject(
              new Error(
                resp.error_description || resp.error || 'Google sign-in did not return an access token.',
              ),
            );
          }
          return;
        }
        const expiresInSec =
          typeof resp.expires_in === 'number' && resp.expires_in > 0 ? resp.expires_in : 3600;
        cachedToken = {
          accessToken: resp.access_token,
          expiresAt: Date.now() + expiresInSec * 1000,
        };
        resolve(resp.access_token);
      },
      error_callback: (err) => {
        if (err.type === 'popup_closed') {
          reject(new Error('Google sign-in popup was closed before completing.'));
        } else if (err.type === 'popup_failed_to_open') {
          reject(new Error('Google sign-in popup was blocked. Please allow popups and try again.'));
        } else {
          reject(new Error(err.message || 'Google sign-in failed.'));
        }
      },
    });

    client.requestAccessToken({ prompt: '' });
  });
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function textWithBreaks(text: string): string {
  return escapeHtml(text).replace(/\r?\n/g, '<br />');
}

function formatLanguageLabel(lang: 'en' | 'bn'): string {
  return lang === 'bn' ? 'Bangla (বাংলা)' : 'English';
}

function formatScriptTypeLabel(format?: ScriptFormat): string {
  return format === 'commercial_30s' ? '30s Commercial' : 'UGC Video';
}

export function buildDocumentTitle(payload: ExportScriptPayload): string {
  return `${payload.product} — ${payload.segment.name} (Script)`;
}

function renderMetaRow(label: string, valueHtml: string, isLast = false): string {
  const borderBottom = isLast ? 'none' : '1px solid #e4e9e6';
  return `
    <tr>
      <td style="width:135pt;padding:6pt 10pt;background-color:#f4f7f5;border-bottom:${borderBottom};font-size:9.5pt;font-weight:700;color:#444d51;vertical-align:top;">
        ${escapeHtml(label)}
      </td>
      <td style="padding:6pt 10pt;background-color:#ffffff;border-bottom:${borderBottom};font-size:10.5pt;color:#14181a;vertical-align:top;">
        ${valueHtml}
      </td>
    </tr>
  `;
}

/**
 * Builds clean, UTF-8 / Bengali-safe HTML structured with tables for faithful
 * Google Docs import aesthetics.
 */
export function buildGoogleDocHtml(payload: ExportScriptPayload): string {
  const title = buildDocumentTitle(payload);
  const langAttr = payload.language === 'bn' ? 'bn' : 'en';
  const fontStack = "'Hind Siliguri', 'Noto Sans Bengali', Arial, sans-serif";

  const productRows: Array<[string, string]> = [
    ['Product', escapeHtml(payload.product)],
    ...(payload.category ? [['Category', escapeHtml(payload.category)] as [string, string]] : []),
    ['Target Market', escapeHtml(payload.market)],
    ['Language', escapeHtml(formatLanguageLabel(payload.language))],
    ['Format', escapeHtml(formatScriptTypeLabel(payload.scriptFormat))],
  ];

  const productMetaTable = `
    <table width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;border:1px solid #d7dfda;margin-bottom:14pt;">
      ${productRows
        .map(([label, val], idx) => renderMetaRow(label, val, idx === productRows.length - 1))
        .join('\n')}
    </table>
  `;

  const personaRows: Array<[string, string]> = [
    ['Segment', escapeHtml(payload.segment.name)],
    ['Who They Are', textWithBreaks(payload.segment.who)],
  ];

  const personaSection = `
    <h2 style="font-size:13pt;font-weight:700;color:#14181a;border-bottom:1.5pt solid #2a5c45;padding-bottom:4pt;margin:18pt 0 10pt 0;">
      Customer Segment Persona
    </h2>
    <table width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;border:1px solid #d7dfda;margin-bottom:10pt;">
      ${personaRows
        .map(([label, val], idx) => renderMetaRow(label, val, idx === personaRows.length - 1))
        .join('\n')}
    </table>
    <table width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;margin-bottom:14pt;">
      <tr>
        <td style="padding:9pt 13pt;background-color:#f4f7f5;border-left:3pt solid #2a5c45;font-size:10.5pt;color:#1f2623;">
          <span style="font-size:9pt;font-weight:700;color:#2a5c45;text-transform:uppercase;letter-spacing:0.4pt;">Pain Point</span><br />
          <em>&ldquo;${textWithBreaks(payload.segment.pain_point)}&rdquo;</em>
        </td>
      </tr>
    </table>
  `;

  const scriptLinesHtml = payload.lines
    .map((line, idx) => {
      const lineNum = line.no ?? idx + 1;
      const speakerText = line.speaker?.trim();
      const visualText = line.visual?.trim();
      const hasMeta = Boolean(speakerText || visualText);

      const directionBoxHtml = hasMeta
        ? `
          <table width="100%" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;margin:0 0 6pt 0;">
            <tr>
              <td style="padding:7pt 12pt;background-color:#f4f7f5;border:none;border-left:2.5pt solid #2a5c45;">
                ${
                  speakerText
                    ? `<p style="margin:0${visualText ? ' 0 2pt 0' : ''};font-size:9.5pt;color:#14181a;">
                         <span style="font-weight:700;color:#2a5c45;text-transform:uppercase;letter-spacing:0.4pt;">Speaker:</span>
                         <span style="font-weight:600;color:#14181a;"> ${escapeHtml(speakerText)}</span>
                       </p>`
                    : ''
                }
                ${
                  visualText
                    ? `<p style="margin:0;font-size:9.5pt;color:#444d51;line-height:1.45;">
                         <strong style="color:#14181a;">Visual Direction:</strong> <em>${textWithBreaks(visualText)}</em>
                       </p>`
                    : ''
                }
              </td>
            </tr>
          </table>
        `
        : '';

      return `
        ${directionBoxHtml}
        <p style="margin:5pt 0 14pt 0;font-size:11.5pt;line-height:1.65;color:#14181a;">
          <strong style="color:#2a5c45;">${lineNum}.</strong> ${textWithBreaks(line.text)}
        </p>
      `;
    })
    .join('\n');

  return `<!DOCTYPE html>
<html lang="${langAttr}">
<head>
  <meta charset="UTF-8" />
  <title>${escapeHtml(title)}</title>
</head>
<body style="font-family:${fontStack};color:#14181a;line-height:1.5;font-size:11pt;max-width:660pt;">
  <h1 style="font-size:20pt;font-weight:700;margin:0 0 4pt 0;color:#14181a;">${escapeHtml(title)}</h1>
  <p style="margin:0 0 16pt 0;color:#5c6662;font-size:9.5pt;">
    UG-Scripts &middot; ${escapeHtml(payload.market)} &middot; ${escapeHtml(formatLanguageLabel(payload.language))} &middot; ${escapeHtml(formatScriptTypeLabel(payload.scriptFormat))}
  </p>

  <h2 style="font-size:13pt;font-weight:700;color:#14181a;border-bottom:1.5pt solid #2a5c45;padding-bottom:4pt;margin:0 0 10pt 0;">
    Product Info
  </h2>
  ${productMetaTable}

  ${personaSection}

  <h2 style="font-size:13pt;font-weight:700;color:#14181a;border-bottom:1.5pt solid #2a5c45;padding-bottom:4pt;margin:18pt 0 10pt 0;">
    Script
  </h2>
  ${scriptLinesHtml}
</body>
</html>`;
}

/**
 * Builds a clean Markdown fallback document for offline download without Google sign-in.
 */
export function buildMarkdownDocument(payload: ExportScriptPayload): string {
  const parts: string[] = [];
  parts.push(`# ${buildDocumentTitle(payload)}`);
  parts.push('');
  parts.push('## Product Info');
  parts.push(`- **Product:** ${payload.product}`);
  if (payload.category) parts.push(`- **Category:** ${payload.category}`);
  parts.push(`- **Target Market:** ${payload.market}`);
  parts.push(`- **Language:** ${formatLanguageLabel(payload.language)}`);
  parts.push(`- **Format:** ${formatScriptTypeLabel(payload.scriptFormat)}`);

  parts.push('');
  parts.push('## Customer Segment Persona');
  parts.push(`- **Segment:** ${payload.segment.name}`);
  parts.push(`- **Who They Are:** ${payload.segment.who}`);
  parts.push('');
  parts.push(`> "${payload.segment.pain_point}"`);

  parts.push('');
  parts.push('## Script');
  payload.lines.forEach((line, idx) => {
    const lineNum = line.no ?? idx + 1;
    const speakerText = line.speaker?.trim();
    const visualText = line.visual?.trim();
    if (speakerText || visualText) {
      if (speakerText) {
        parts.push(`> **Speaker:** ${speakerText}`);
      }
      if (visualText) {
        parts.push(`> *Visual Direction:* ${visualText}`);
      }
      parts.push('');
    }
    parts.push(`${lineNum}. ${line.text}`);
    if (idx < payload.lines.length - 1) {
      parts.push('');
    }
  });

  return parts.join('\n').trimEnd() + '\n';
}

function slugify(value: string): string {
  const cleaned = value
    .toLowerCase()
    .replace(/[^a-z0-9\u0980-\u09ff]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return cleaned.slice(0, 48);
}

/**
 * Triggers a browser download of the script as a UTF-8 Markdown (.md) file.
 */
export function downloadMarkdownDocument(payload: ExportScriptPayload): string {
  const markdown = buildMarkdownDocument(payload);
  const productSlug = slugify(payload.product) || 'product';
  const segmentSlug = slugify(payload.segment.name) || 'script';
  const filename = `${productSlug}-${segmentSlug}.md`;

  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  return filename;
}

async function uploadHtmlToGoogleDoc(
  title: string,
  html: string,
  accessToken: string,
): Promise<GoogleDocExportResult> {
  const boundary = `ug_scripts_doc_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  const metadata = JSON.stringify({
    name: title,
    mimeType: 'application/vnd.google-apps.document',
  });

  const bodyString = [
    `--${boundary}`,
    'Content-Type: application/json; charset=UTF-8',
    '',
    metadata,
    `--${boundary}`,
    'Content-Type: text/html; charset=UTF-8',
    '',
    html,
    `--${boundary}--`,
    '',
  ].join('\r\n');

  const bodyBlob = new Blob([bodyString], {
    type: `multipart/related; boundary=${boundary}`,
  });

  let res: Response;
  try {
    res = await fetch(DRIVE_UPLOAD_URL, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': `multipart/related; boundary=${boundary}`,
      },
      body: bodyBlob,
    });
  } catch {
    throw new Error('Could not reach Google Drive. Check your internet connection and try again.');
  }

  if (res.status === 401) {
    clearCachedGoogleToken();
    throw new Error('Your Google session expired. Please click Export to Google Docs again.');
  }

  if (!res.ok) {
    let detail = '';
    try {
      const errJson = (await res.json()) as { error?: { message?: string } };
      detail = errJson.error?.message || '';
    } catch {
      // Ignore JSON parse error
    }
    throw new Error(detail || `Google Drive upload failed (status ${res.status}).`);
  }

  const created = (await res.json()) as { id?: string; name?: string };
  if (!created.id) {
    throw new Error('Google Drive did not return a document ID.');
  }

  return {
    id: created.id,
    title: created.name || title,
    url: `https://docs.google.com/document/d/${created.id}/edit`,
  };
}

/**
 * Authenticates via Google Identity Services (drive.file scope) and creates a native Google Doc.
 */
export async function exportScriptToGoogleDocs(
  payload: ExportScriptPayload,
): Promise<GoogleDocExportResult> {
  const [clientId] = await Promise.all([getGoogleClientId(), loadGisClient()]);
  const accessToken = await requestAccessToken(clientId);
  const title = buildDocumentTitle(payload);
  const html = buildGoogleDocHtml(payload);
  return uploadHtmlToGoogleDoc(title, html, accessToken);
}
