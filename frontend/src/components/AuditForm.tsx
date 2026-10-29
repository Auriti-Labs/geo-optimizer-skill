import { useState } from 'react';
import { trackAuditStarted } from '../lib/geo_track';
import { toAuditableUrl } from '../lib/urlInput';

interface AuditFormProps {
  /** Retained for call-site compatibility: since wave 2 the console world is
   *  the only rendering, so the prop no longer changes anything. */
  variant?: 'default' | 'console';
}

export default function AuditForm({ variant: _variant = 'console' }: AuditFormProps) {
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
      <div className="space-y-3">
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
          <label htmlFor="audit-url" className="sr-only">
            Website URL to audit
          </label>
          <div className="flex min-w-0 flex-1 items-stretch overflow-hidden rounded-[10px] border border-ink/25 bg-raised transition-shadow focus-within:border-pass-deep focus-within:ring-2 focus-within:ring-pass/30">
            <span aria-hidden="true" className="hidden shrink-0 items-center border-r border-pass/15 bg-pass/10 px-4 font-mono text-[13px] font-medium text-ink-mute md:flex whitespace-nowrap select-none">
              $ geo audit
            </span>
            <input
              id="audit-url"
              type="text"
              inputMode="url"
              required
              placeholder="example.com"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (errorMsg) setErrorMsg('');
              }}
              disabled={isLoading}
              className="w-full min-w-0 flex-1 bg-transparent py-3.5 pl-4 pr-4 font-mono text-[15px] text-ink caret-pass-deep placeholder:text-ink-mute focus:outline-none disabled:opacity-60"
              aria-describedby={errorMsg ? 'audit-error' : undefined}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="flex shrink-0 items-center justify-center gap-2 rounded-[10px] bg-pass-deep px-7 py-3.5 font-text text-[13px] font-semibold text-on-accent transition-colors hover:bg-pass disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? (
              <>
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Running…
              </>
            ) : (
              <>
                Run audit
                <svg className="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
                  <path d="M3 1.5 9.5 6 3 10.5V1.5Z" />
                </svg>
              </>
            )}
          </button>
        </form>

        {errorMsg && (
          <div
            id="audit-error"
            role="alert"
            className="flex items-start gap-3 rounded-[10px] border border-fail/30 bg-fail-wash px-4 py-3 text-sm text-fail"
          >
            <span aria-hidden="true" className="font-text text-[12.5px] font-semibold mt-0.5">
              err
            </span>
            <span>{errorMsg}</span>
          </div>
        )}
      </div>
  );
}
