import { useEffect, useState } from 'react';
import { generateLlmsTxt } from '../../lib/api';
import type { LlmsGenerateResult } from '../../lib/api';
import {
  trackLlmsGeneratorStarted,
  trackLlmsGeneratorCompleted,
  trackLlmsGeneratorFailed,
  trackLlmsTxtCopied,
  trackLlmsTxtDownloaded,
} from '../../lib/geo_track';

// Stato del flusso di generazione.
type Status = 'idle' | 'loading' | 'error' | 'success';

// Dati di successo restituiti dal backend (non-null in stato 'success').
type LlmsData = NonNullable<LlmsGenerateResult['data']>;

// Opzioni per il select "max links per section". Default 10 (vedi backend).
const MAX_PER_SECTION_OPTIONS = [5, 10, 20] as const;
const DEFAULT_MAX_PER_SECTION = 10;

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
    const trimmedWebsite = websiteUrl.trim();
    if (!trimmedWebsite) {
      setStatus('error');
      setErrorMsg('Enter your website URL, for example https://example.com.');
      return;
    }

    const trimmedSitemap = sitemapUrl.trim();
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
          <label htmlFor="llms-website" className="block text-sm font-medium text-text-primary mb-1.5">
            Website URL <span className="text-accent-danger">*</span>
          </label>
          <input
            id="llms-website"
            type="url"
            required
            placeholder="https://example.com"
            value={websiteUrl}
            onChange={(e) => {
              setWebsiteUrl(e.target.value);
              if (errorMsg) setErrorMsg('');
            }}
            disabled={isLoading}
            aria-describedby={status === 'error' ? 'llms-error' : undefined}
            className="w-full px-3 py-2 rounded-lg border border-border bg-bg-surface text-text-primary text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors disabled:opacity-60"
          />
        </div>

        <div>
          <label htmlFor="llms-sitemap" className="block text-sm font-medium text-text-primary mb-1.5">
            Sitemap URL <span className="text-text-muted font-normal">(optional)</span>
          </label>
          <input
            id="llms-sitemap"
            type="url"
            placeholder="https://example.com/sitemap.xml"
            value={sitemapUrl}
            onChange={(e) => setSitemapUrl(e.target.value)}
            disabled={isLoading}
            className="w-full px-3 py-2 rounded-lg border border-border bg-bg-surface text-text-primary text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors disabled:opacity-60"
          />
          <p className="mt-1.5 text-xs text-text-muted">
            Leave blank to let us discover it automatically from your site.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label htmlFor="llms-site-name" className="block text-sm font-medium text-text-primary mb-1.5">
              Site name <span className="text-text-muted font-normal">(optional)</span>
            </label>
            <input
              id="llms-site-name"
              type="text"
              placeholder="Example Inc."
              value={siteName}
              onChange={(e) => setSiteName(e.target.value)}
              disabled={isLoading}
              className="w-full px-3 py-2 rounded-lg border border-border bg-bg-surface text-text-primary text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors disabled:opacity-60"
            />
          </div>

          <div>
            <label htmlFor="llms-max" className="block text-sm font-medium text-text-primary mb-1.5">
              Max links per section
            </label>
            <select
              id="llms-max"
              value={maxPerSection}
              onChange={(e) => setMaxPerSection(Number(e.target.value))}
              disabled={isLoading}
              className="w-full px-3 py-2 rounded-lg border border-border bg-bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors disabled:opacity-60"
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
          <label htmlFor="llms-description" className="block text-sm font-medium text-text-primary mb-1.5">
            Description <span className="text-text-muted font-normal">(optional)</span>
          </label>
          <textarea
            id="llms-description"
            rows={3}
            placeholder="A short summary of what your site is about."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isLoading}
            className="w-full px-3 py-2 rounded-lg border border-border bg-bg-surface text-text-primary text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors resize-y disabled:opacity-60"
          />
        </div>

        {/* Messaggio di errore inline — annunciato dagli screen reader. */}
        {status === 'error' && errorMsg && (
          <p
            id="llms-error"
            role="alert"
            className="text-sm text-accent-danger bg-accent-danger/5 border border-accent-danger/20 rounded-lg px-3 py-2"
          >
            {errorMsg}
          </p>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-accent-teal text-white font-semibold text-sm hover:bg-accent-teal-dark transition-colors disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
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
          {/* Riga di statistiche sintetiche. */}
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg border border-border bg-bg-surface px-4 py-3">
              <dt className="text-xs text-text-muted">Sitemap found</dt>
              <dd className="mt-1 text-lg font-semibold font-mono text-text-primary">
                {result.found_sitemap ? 'Yes' : 'No'}
              </dd>
            </div>
            <div className="rounded-lg border border-border bg-bg-surface px-4 py-3">
              <dt className="text-xs text-text-muted">URLs</dt>
              <dd className="mt-1 text-lg font-semibold font-mono text-text-primary tabular-nums">
                {result.url_count}
              </dd>
            </div>
            <div className="rounded-lg border border-border bg-bg-surface px-4 py-3">
              <dt className="text-xs text-text-muted">Lines</dt>
              <dd className="mt-1 text-lg font-semibold font-mono text-text-primary tabular-nums">
                {result.line_count}
              </dd>
            </div>
            <div className="rounded-lg border border-border bg-bg-surface px-4 py-3">
              <dt className="text-xs text-text-muted">Size</dt>
              <dd className="mt-1 text-lg font-semibold font-mono text-text-primary tabular-nums">
                {formatBytes(result.size_bytes)}
              </dd>
            </div>
          </dl>

          {/* Nota informativa quando nessuna sitemap è stata trovata (NON è un errore). */}
          {!result.found_sitemap && (
            <p className="text-sm text-text-secondary bg-bg-subtle border border-border rounded-lg px-4 py-3">
              No sitemap was found — generated a minimal file from the homepage. You can edit it below or
              provide a sitemap URL.
            </p>
          )}

          {/* Editor del contenuto. */}
          <div>
            <label htmlFor="llms-output" className="block text-sm font-medium text-text-primary mb-1.5">
              Your llms.txt
            </label>
            <textarea
              id="llms-output"
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              rows={16}
              spellCheck={false}
              className="w-full px-3 py-3 rounded-lg border border-border bg-bg-surface text-text-primary text-xs font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors resize-y"
            />
          </div>

          {/* Azioni: copia e download. */}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleCopy}
              className="px-4 py-2 rounded-lg bg-accent-teal text-white font-medium text-sm hover:bg-accent-teal-dark transition-colors inline-flex items-center gap-2"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="px-4 py-2 rounded-lg border border-border bg-bg-surface text-text-primary font-medium text-sm hover:bg-bg-subtle transition-colors"
            >
              Download llms.txt
            </button>
          </div>

          {/* Promemoria onesto: llms.txt è un file di orientamento, NON un ranking factor. */}
          <p className="text-xs text-text-muted leading-relaxed">
            An llms.txt file helps AI systems understand and navigate your site's most important pages. It is
            a guidance file, not a confirmed ranking factor — no major AI engine guarantees it changes how
            your site is cited or ranked. Place it at the root of your domain (e.g. /llms.txt).
          </p>

          {/* CTA verso l'audit completo + link alla guida. */}
          <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-border">
            <a
              href="/#audit-form"
              className="px-5 py-2.5 rounded-lg bg-accent-teal text-white font-semibold text-sm hover:bg-accent-teal-dark transition-colors"
            >
              Run a full AI SEO audit
            </a>
            <a href="/guides/what-is-llms-txt/" className="text-sm text-accent-teal hover:underline">
              What is llms.txt?
            </a>
          </div>
        </section>
      )}
    </div>
  );
}
