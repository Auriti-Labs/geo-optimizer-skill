import { useState } from 'react';

// Cattura email → platform endpoint (CORS già aperto per geoready.dev).
// Dedupe e validazione server-side; source distingue i punti di ingresso.
const CAPTURE_URL = 'https://app.geoready.dev/api/email/capture';

type Status = 'idle' | 'loading' | 'done' | 'error';

interface Props {
  source: string;
  title?: string;
  detail?: string;
}

export default function NewsletterSignup({
  source,
  title = 'Get the monthly GeoReady newsletter',
  detail = 'One email a month: fresh State of GEO benchmark data, one practical GEO lesson, and what changed in AI search. No spam, unsubscribe anytime.',
}: Props) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<Status>('idle');

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed.includes('@')) {
      setStatus('error');
      return;
    }
    setStatus('loading');
    // Record the opt-in page so the backend can store it on the consent record.
    const sourceUrl = typeof window !== 'undefined' ? window.location.href : undefined;
    try {
      const res = await fetch(CAPTURE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: trimmed, source, source_url: sourceUrl }),
      });
      setStatus(res.ok ? 'done' : 'error');
    } catch {
      setStatus('error');
    }
  }

  if (status === 'done') {
    return (
      <div className="flex items-start gap-2.5 rounded-[10px] border border-pass/50 bg-pass-wash px-5 py-4 text-sm text-ink">
        <svg aria-hidden="true" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-pass-deep" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
        <span>Check your inbox and confirm your subscription. Nothing is sent until you click the link.</span>
      </div>
    );
  }

  return (
    <div className="rounded-[10px] border border-rail bg-raised px-5 py-5">
      <p className="text-base font-semibold text-ink">{title}</p>
      <p className="mt-1 text-sm text-ink-soft">{detail}</p>
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-2 sm:flex-row">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
          className="flex-1 rounded-[10px] border border-ink/25 bg-raised px-3 py-2 font-mono text-sm text-ink placeholder:text-ink-mute focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30"
        />
        <button
          type="submit"
          disabled={status === 'loading'}
          className="rounded-[10px] bg-pass-deep px-5 py-2 font-text text-[13px] font-semibold text-on-accent transition-colors hover:bg-pass disabled:opacity-50"
        >
          {status === 'loading' ? 'Subscribing…' : 'Notify me'}
        </button>
      </form>
      {/* Must mirror STATE_OF_GEO_CONSENT_PURPOSE (geoready-newsletter-monthly-2026-v1)
          recorded server-side on capture — change both together. */}
      <p className="mt-2 text-xs text-ink-mute">
        By submitting, you agree to receive the monthly GeoReady newsletter: benchmark data from the
        State of GEO dataset, practical GEO guidance, and product updates. You can unsubscribe
        anytime. See our{' '}
        <a href="https://geoready.dev/privacy/" className="underline decoration-rail underline-offset-2 hover:text-ink">
          Privacy Policy
        </a>
        .
      </p>
      {status === 'error' && (
        <p className="mt-2 flex items-start gap-2 text-xs text-fail">
          <span aria-hidden="true" className="font-text font-semibold">err</span>
          <span>Something went wrong — check the email and try again.</span>
        </p>
      )}
    </div>
  );
}
