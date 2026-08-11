import { useState } from 'react';
import { trackAuditStarted } from '../lib/geo_track';
import { toAuditableUrl } from '../lib/urlInput';

export default function AuditForm() {
  const [url, setUrl] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    const trimmed = url.trim();
    if (!trimmed) {
      setErrorMsg('Enter a URL to audit.');
      return;
    }

    // toAuditableUrl supplies the scheme, so a bare "example.com" — what the
    // placeholder shows — reaches the report page as a full URL.
    const normalized = toAuditableUrl(trimmed);
    if (!normalized) {
      setErrorMsg('Enter a valid website address, for example example.com.');
      return;
    }

    trackAuditStarted();
    setIsLoading(true);
    window.location.href = `/report/audit?url=${encodeURIComponent(normalized)}`;
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <label htmlFor="audit-url" className="sr-only">
          Website URL to audit
        </label>
        <input
          id="audit-url"
          type="text"
          inputMode="url"
          required
          placeholder="https://example.com"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (errorMsg) setErrorMsg('');
          }}
          disabled={isLoading}
          className="flex-1 px-4 py-3 rounded-2xl border border-border bg-bg-surface text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal focus:border-transparent transition-shadow disabled:opacity-60"
          aria-describedby={errorMsg ? 'audit-error' : undefined}
        />
        <button
          type="submit"
          disabled={isLoading}
          className="px-6 py-3 rounded-2xl bg-accent-teal text-white font-medium text-sm hover:bg-accent-teal-dark transition-colors shrink-0 disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Running…
            </>
          ) : (
            'Run Audit'
          )}
        </button>
      </form>

      {errorMsg && (
        <div
          id="audit-error"
          role="alert"
          className="p-4 rounded-2xl border border-accent-danger/20 bg-accent-danger/5 text-accent-danger text-sm"
        >
          {errorMsg}
        </div>
      )}
    </div>
  );
}
