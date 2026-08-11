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
      <div className="rounded-xl border border-accent-teal/25 bg-accent-teal/5 p-6 text-center">
        <div className="w-12 h-12 rounded-full bg-accent-teal/10 flex items-center justify-center mx-auto mb-3">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-teal">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <path d="M22 4L12 14.01l-3-3" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-text-primary mb-1">
          Report sent to your inbox
        </p>
        <p className="text-xs text-text-secondary max-w-sm mx-auto leading-relaxed">
          Check <strong className="text-text-primary">{email}</strong> for a copy of the complete
          8-category GEO breakdown with scores, signals, and recommendations.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-accent-teal/25 bg-accent-teal/5 p-5">
      <div className="flex items-center gap-2 mb-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-teal shrink-0" aria-hidden="true">
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
          <polyline points="22,6 12,13 2,6" />
        </svg>
        <span className="text-sm font-semibold text-text-primary">
          Want this report in your inbox?
        </span>
      </div>

      <p className="text-sm text-text-secondary leading-snug mb-3">
        Optional — the full report is already on this page. Enter your email and we'll
        send you a copy of the complete 8-category breakdown to keep or share.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2">
        <input
          type="email"
          required
          placeholder="you@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={status === 'submitting'}
          className="flex-1 px-3 py-2 rounded-lg border border-border bg-bg-surface text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-teal focus:ring-1 focus:ring-accent-teal/30"
        />
        <button
          type="submit"
          disabled={status === 'submitting' || !email || !claimToken}
          className="shrink-0 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-accent-teal text-white text-sm font-semibold hover:bg-accent-teal-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {status === 'submitting' ? (
            <>
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-20" />
                <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
              </svg>
              Sending...
            </>
          ) : (
            <>
              Email me this report
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </>
          )}
        </button>
      </form>

      {status === 'error' && (
        <p className="mt-2 text-xs text-accent-danger">{errorMsg}</p>
      )}

      <p className="mt-2 text-[10px] text-text-muted">
        One email with your report copy. No spam, unsubscribe anytime.{' '}
        <a href="/privacy/" className="text-text-muted underline hover:text-text-secondary">Privacy Policy</a>
      </p>
    </div>
  );
}