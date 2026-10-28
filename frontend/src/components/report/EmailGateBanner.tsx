import React, { useState } from 'react';
import { trackCtaClicked } from '../../lib/geo_track';
import type { CategoryScore } from '../../lib/mockData';

// Optional email delivery of the full report. The on-screen report is complete
// (no locked categories): this banner only offers a copy in the inbox, matching
// the pricing promise "no email required".
interface EmailGateBannerProps {
  score: number;
  categories: CategoryScore[];
  claimToken: string | null;
}

const API_BASE = import.meta.env.PUBLIC_API_BASE || '/api';

export default function EmailGateBanner({ score, categories, claimToken }: EmailGateBannerProps) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  void score;
  void categories;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || status === 'submitting' || !claimToken) return;

    setStatus('submitting');
    setErrorMsg('');

    try {
      const res = await fetch(`${API_BASE}/public/email-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          claim_token: claimToken,
        }),
      });

      if (res.ok) {
        setStatus('success');
        trackCtaClicked({ cta_location: 'email_report_optional', cta_text: 'Email me this report' });
      } else {
        const data = await res.json().catch(() => ({}));
        setStatus('error');
        setErrorMsg(data.detail || data.message || 'Something went wrong. Try again.');
      }
    } catch {
      setStatus('error');
      setErrorMsg('Network error. Please try again.');
    }
  }

  // Success state — a copy of the report is on its way
  if (status === 'success') {
    return (
      <div className="rounded-[10px] border border-pass/50 bg-pass-wash/60 p-6 text-center">
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-pass-wash">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-pass-deep">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <path d="M22 4L12 14.01l-3-3" />
          </svg>
        </div>
        <p className="mb-1 text-sm font-semibold text-ink">
          Report sent to your inbox
        </p>
        <p className="mx-auto max-w-sm text-xs leading-relaxed text-ink-soft">
          Check <strong className="font-semibold text-ink">{email}</strong> for a copy of the complete
          9-category GEO breakdown with scores, signals, and recommendations.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-[10px] border border-rail bg-white p-5">
      <div className="mb-2 flex items-center gap-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-ink-mute" aria-hidden="true">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
        <span className="text-sm font-semibold text-ink">
          Want this report in your inbox?
        </span>
      </div>

      <p className="mb-3 text-sm leading-snug text-ink-soft">
        Optional: the full report is already on this page. Enter your email and we'll
        send you a copy of the complete 9-category breakdown to keep or share.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-2 sm:flex-row">
        <input
          type="email"
          required
          placeholder="you@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={status === 'submitting'}
          className="flex-1 rounded-[10px] border border-ink/25 bg-white px-3 py-2 text-sm text-ink caret-pass-deep placeholder:text-ink-mute focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={status === 'submitting' || !email || !claimToken}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-[10px] bg-pass-deep px-4 py-2 font-text text-[13px] font-semibold text-white transition-colors hover:bg-pass disabled:cursor-not-allowed disabled:opacity-50"
        >
          {status === 'submitting' ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-20" />
                <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
              </svg>
              Sending...
            </>
          ) : (
            <>
              Email me this report
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </>
          )}
        </button>
      </form>

      {status === 'error' && (
        <p className="mt-2 text-xs text-fail">{errorMsg}</p>
      )}

      <p className="mt-2 text-[10px] text-ink-mute">
        One email with your report copy. No spam, unsubscribe anytime.{' '}
        <a href="/privacy/" className="text-ink-mute underline underline-offset-2 hover:text-ink-soft">Privacy Policy</a>
      </p>
    </div>
  );
}
