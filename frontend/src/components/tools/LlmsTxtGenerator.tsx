import { useEffect, useState } from 'react';
import { generateLlmsTxt } from '../../lib/api';
import type { LlmsGenerateResult } from '../../lib/api';
import {
  trackLlmsGeneratorStarted,
  trackLlmsGeneratorCompleted,
  trackLlmsGeneratorFailed,
  trackLlmsTxtCopied,
  trackLlmsTxtDownloaded,
  trackPlanSelected,
} from '../../lib/geo_track';
import { normalizeUrl, toAuditableUrl } from '../../lib/urlInput';

// Stato del flusso di generazione.
type Status = 'idle' | 'loading' | 'error' | 'success';

// Dati di successo restituiti dal backend (non-null in stato 'success').
type LlmsData = NonNullable<LlmsGenerateResult['data']>;

// Opzioni per il select "max links per section". Default 10 (vedi backend).
const MAX_PER_SECTION_OPTIONS = [5, 10, 20] as const;
const DEFAULT_MAX_PER_SECTION = 10;

// Classi condivise del mondo console (input su ground bianco, ring pass al focus).
const FIELD_CLASSES =
  'w-full rounded-[4px] border border-ink/25 bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-mute transition-colors focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30 disabled:opacity-60';
const LABEL_CLASSES = 'mb-1.5 block text-sm font-medium text-ink';

// Formatta i byte in una stringa leggibile (B / KB).
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

export default function LlmsTxtGenerator() {
  // ── Campi del form ──────────────────────────────────────────────────────
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [sitemapUrl, setSitemapUrl] = useState('');
  const [siteName, setSiteName] = useState('');
  const [description, setDescription] = useState('');
  const [maxPerSection, setMaxPerSection] = useState<number>(DEFAULT_MAX_PER_SECTION);

  // ── Stato del flusso ────────────────────────────────────────────────────
  const [status, setStatus] = useState<Status>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [result, setResult] = useState<LlmsData | null>(null);

  // Contenuto editabile della textarea di output (stato controllato).
  const [editedContent, setEditedContent] = useState('');
  // Feedback temporaneo per il pulsante "Copy".
  const [copied, setCopied] = useState(false);

  // Resetta il feedback "Copied!" dopo 2 secondi.
  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrorMsg('');

    // Validazione inline: la URL del sito è obbligatoria.
    const trimmedWebsite = toAuditableUrl(websiteUrl);
    if (!trimmedWebsite) {
      setStatus('error');
      setErrorMsg('Enter a valid website address, for example example.com.');
      return;
    }

    const trimmedSitemap = sitemapUrl.trim() ? normalizeUrl(sitemapUrl) : '';
    const hasCustomSitemap = Boolean(trimmedSitemap);

    trackLlmsGeneratorStarted({
      has_custom_sitemap: hasCustomSitemap,
      max_per_section: maxPerSection,
    });

    setStatus('loading');
    setResult(null);

    const { data, error } = await generateLlmsTxt({
      base_url: trimmedWebsite,
      sitemap_url: trimmedSitemap || undefined,
      site_name: siteName.trim() || undefined,
      description: description.trim() || undefined,
      max_per_section: maxPerSection,
    });

    if (error || !data) {
      setStatus('error');
      setErrorMsg(error || 'Something went wrong while generating llms.txt. Please try again.');
      trackLlmsGeneratorFailed({ has_custom_sitemap: hasCustomSitemap });
      return;
    }

    setResult(data);
    setEditedContent(data.content);
    setStatus('success');
    trackLlmsGeneratorCompleted({
      found_sitemap: data.found_sitemap,
      url_count: data.url_count,
      line_count: data.line_count,
      size_bytes: data.size_bytes,
      max_per_section: maxPerSection,
    });
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(editedContent);
      setCopied(true);
      trackLlmsTxtCopied();
    } catch {
      // Se la clipboard non è disponibile (es. contesto non sicuro) non blocchiamo l'UI.
      setCopied(false);
    }
  }

  function handleDownload() {
    // Genera un blob di testo e forza il download come "llms.txt".
    const blob = new Blob([editedContent], { type: 'text/plain;charset=utf-8' });
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = 'llms.txt';
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(objectUrl);
    // Riportiamo la dimensione del contenuto effettivamente scaricato.
    trackLlmsTxtDownloaded({ size_bytes: new Blob([editedContent]).size });
  }

  const isLoading = status === 'loading';

  return (
    <div className="space-y-8">
      {/* ── Form di input ────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        <div>
          <label htmlFor="llms-website" className={LABEL_CLASSES}>
            Website URL <span className="text-fail">*</span>
          </label>
          <input
            id="llms-website"
            type="text"
            inputMode="url"
            required
            placeholder="https://example.com"
            value={websiteUrl}
            onChange={(e) => {
              setWebsiteUrl(e.target.value);
              if (errorMsg) setErrorMsg('');
            }}
            disabled={isLoading}
            aria-describedby={status === 'error' ? 'llms-error' : undefined}
            className={`${FIELD_CLASSES} font-mono`}
          />
        </div>

        <div>
          <label htmlFor="llms-sitemap" className={LABEL_CLASSES}>
            Sitemap URL <span className="font-normal text-ink-mute">(optional)</span>
          </label>
          <input
            id="llms-sitemap"
            type="text"
            inputMode="url"
            placeholder="https://example.com/sitemap.xml"
            value={sitemapUrl}
            onChange={(e) => setSitemapUrl(e.target.value)}
            disabled={isLoading}
            className={`${FIELD_CLASSES} font-mono`}
          />
          <p className="mt-1.5 text-xs text-ink-mute">
            Leave blank to let us discover it automatically from your site.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="llms-site-name" className={LABEL_CLASSES}>
              Site name <span className="font-normal text-ink-mute">(optional)</span>
            </label>
            <input
              id="llms-site-name"
              type="text"
              placeholder="Example Inc."
              value={siteName}
              onChange={(e) => setSiteName(e.target.value)}
              disabled={isLoading}
              className={FIELD_CLASSES}
            />
          </div>

          <div>
            <label htmlFor="llms-max" className={LABEL_CLASSES}>
              Max links per section
            </label>
            <select
              id="llms-max"
              value={maxPerSection}
              onChange={(e) => setMaxPerSection(Number(e.target.value))}
              disabled={isLoading}
              className={FIELD_CLASSES}
            >
              {MAX_PER_SECTION_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value} links
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="llms-description" className={LABEL_CLASSES}>
            Description <span className="font-normal text-ink-mute">(optional)</span>
          </label>
          <textarea
            id="llms-description"
            rows={3}
            placeholder="A short summary of what your site is about."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isLoading}
            className={`${FIELD_CLASSES} resize-y`}
          />
        </div>

        {/* Messaggio di errore inline — annunciato dagli screen reader. */}
        {status === 'error' && errorMsg && (
          <p
            id="llms-error"
            role="alert"
            className="flex items-start gap-3 rounded-[4px] border border-fail/30 bg-fail-wash px-4 py-3 text-sm text-fail"
          >
            <span aria-hidden="true" className="mt-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em]">
              err
            </span>
            <span>{errorMsg}</span>
          </p>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="inline-flex w-full items-center justify-center gap-2 rounded-[4px] bg-pass-deep px-6 py-3 font-mono text-[13px] font-semibold tracking-[0.08em] text-white transition-colors hover:bg-pass disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
        >
          {isLoading ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Generating…
            </>
          ) : (
            'Generate llms.txt'
          )}
        </button>
      </form>

      {/* Regione di stato per gli screen reader (loading / esito). */}
      <div aria-live="polite" className="sr-only">
        {status === 'loading' && 'Generating your llms.txt file.'}
        {status === 'success' && 'Your llms.txt file is ready.'}
      </div>

      {/* ── Risultato ────────────────────────────────────────────────────── */}
      {status === 'success' && result && (
        <section className="space-y-5" aria-label="Generated llms.txt">
          {/* Riga di statistiche sintetiche — griglia hairline, valori mono. */}
          <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-[4px] border border-rail bg-rail sm:grid-cols-4">
            <div className="bg-white px-4 py-3">
              <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-mute">Sitemap found</dt>
              <dd className="mt-1 font-mono text-lg font-semibold text-ink">
                {result.found_sitemap ? 'Yes' : 'No'}
              </dd>
            </div>
            <div className="bg-white px-4 py-3">
              <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-mute">URLs</dt>
              <dd className="mt-1 font-mono text-lg font-semibold tabular-nums text-ink">
                {result.url_count}
              </dd>
            </div>
            <div className="bg-white px-4 py-3">
              <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-mute">Lines</dt>
              <dd className="mt-1 font-mono text-lg font-semibold tabular-nums text-ink">
                {result.line_count}
              </dd>
            </div>
            <div className="bg-white px-4 py-3">
              <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-mute">Size</dt>
              <dd className="mt-1 font-mono text-lg font-semibold tabular-nums text-ink">
                {formatBytes(result.size_bytes)}
              </dd>
            </div>
          </dl>

          {/* Nota informativa quando nessuna sitemap è stata trovata (NON è un errore). */}
          {!result.found_sitemap && (
            <p className="rounded-[4px] border border-warn/30 bg-warn-wash px-4 py-3 text-sm text-ink-soft">
              No sitemap was found — generated a minimal file from the homepage. You can edit it below or
              provide a sitemap URL.
            </p>
          )}

          {/* Editor del contenuto — il log well della pagina: output di prima parte
              da POST /api/llms/generate, incorniciato come log con header strip. */}
          <div className="overflow-hidden rounded-[4px] bg-well">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-well-ink/15 px-4 py-2.5">
              <label htmlFor="llms-output" className="font-mono text-[11px] font-semibold tracking-[0.08em] text-well-mute">
                Your llms.txt
              </label>
              <span className="font-mono text-[11px] tracking-[0.08em] text-well-mute">POST /api/llms/generate</span>
            </div>
            <textarea
              id="llms-output"
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              rows={16}
              spellCheck={false}
              className="block w-full resize-y bg-transparent px-4 py-4 font-mono text-xs leading-relaxed text-well-ink focus:outline-none focus:ring-2 focus:ring-inset focus:ring-pass"
            />
          </div>

          {/* Azioni: copia e download. */}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-2 rounded-[4px] bg-pass-deep px-4 py-2 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-white transition-colors hover:bg-pass"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="rounded-[4px] border border-rail bg-white px-4 py-2 font-mono text-[12px] font-semibold tracking-[0.08em] text-ink transition-colors hover:bg-pass-wash"
            >
              Download llms.txt
            </button>
          </div>

          {/* Promemoria onesto: llms.txt è un file di orientamento, NON un ranking factor. */}
          <p className="text-xs leading-relaxed text-ink-mute">
            An llms.txt file helps AI systems understand and navigate your site's most important pages. It is
            a guidance file, not a confirmed ranking factor — no major AI engine guarantees it changes how
            your site is cited or ranked. Place it at the root of your domain (e.g. /llms.txt).
          </p>

          {/* CTA verso l'audit completo + link alla guida. */}
          <div className="flex flex-wrap items-center gap-4 border-t border-rail pt-4">
            <a
              href="/ai-seo-audit/"
              data-cta="llms_generator_result_ai_seo_audit"
              className="rounded-[4px] bg-pass-deep px-5 py-2.5 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-white transition-colors hover:bg-pass"
            >
              Run a full AI SEO audit
            </a>
            <a
              href="https://app.geoready.dev/signup?plan=pro&intent=llms&utm_source=llms_txt_generator&utm_medium=tool_result&utm_campaign=tool_to_paid"
              onClick={() => trackPlanSelected({
                plan_id: 'pro',
                plan_name: 'Pro',
                billing_period: 'monthly',
                price: '19',
                currency: 'USD',
                cta_location: 'llms_generator_result_monitoring',
              })}
              className="rounded-[4px] border border-rail bg-white px-5 py-2.5 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-ink transition-colors hover:bg-pass-wash"
            >
              Monitor weekly changes
            </a>
            <a href="/guides/what-is-llms-txt/" className="text-sm text-pass-deep underline decoration-rail underline-offset-4 hover:decoration-pass-deep">
              What is llms.txt?
            </a>
          </div>
        </section>
      )}
    </div>
  );
}
