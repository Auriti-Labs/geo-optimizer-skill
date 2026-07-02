import React, { useState } from 'react';
import { trackCtaClicked } from '../../lib/geo_track';

interface EmailGateBannerProps {
  score: number;
  lockedCount: number;
  totalLockedPoints: number;
  onUnlock: () => void;
}

const API_BASE = import.meta.env.PUBLIC_API_BASE || '/api';

export default function EmailGateBanner({ score, lockedCount, totalLockedPoints, onUnlock }: EmailGateBannerProps) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const potentialScore = Math.min(score + totalLockedPoints, 100);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || status === 'submitting') return;

    setStatus('submitting');
    setErrorMsg('');

    try {
      const res = await fetch(`${API_BASE}/email/capture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          source: 'audit-report-unlock',
          source_url: typeof window !== 'undefined' ? window.location.href : undefined,
        }),
      });

      if (res.ok) {
        setStatus('success');
        trackCtaClicked({ cta_location: 'email_gate', cta_text: 'Unlock with email' });
        onUnlock();
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

  // Success state — categories unlocked
  if (status === 'success') {
    return (
      <div className="rounded-xl border border-accent-success/25 bg-accent-success/5 p-5 flex items-start gap-3">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-success shrink-0 mt-0.5" aria-hidden="true">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <path d="M22 4L12 14.01l-3-3" />
        </svg>
        <div>
          <p className="text-sm font-semibold text-text-primary">Full report unlocked</p>
          <p className="text-xs text-text-secondary mt-1">
            We saved your email and unlocked all 8 categories. We'll occasionally send you GEO benchmark updates — unsubscribe anytime.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-accent-teal/25 bg-accent-teal/5 p-5">
      <div className="flex items-center gap-2 mb-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-teal shrink-0" aria-hidden="true">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
        <span className="text-sm font-semibold text-text-primary">
          {lockedCount} categories locked — {totalLockedPoints} points hidden
        </span>
      </div>

      <p className="text-sm text-text-secondary leading-snug mb-3">
        Your visible score is <strong className="text-text-primary">{score}/100</strong>.
        The locked categories can add up to <strong className="text-accent-teal">+{totalLockedPoints} points</strong>,
        potentially reaching <strong className="text-accent-teal">{potentialScore}/100</strong>.
        Enter your email to unlock the full report — free, no account needed.
      </p>

      <div className="flex flex-wrap gap-1.5 mb-4">
        {['llms.txt +18', 'Schema +16', 'Content +12', 'AI Discovery +6', 'Brand +10'].map((label) => (
          <span
            key={label}
            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle text-text-muted border border-border"
          >
            {label}
          </span>
        ))}
      </div>

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
          disabled={status === 'submitting' || !email}
          className="shrink-0 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-accent-teal text-white text-sm font-semibold hover:bg-accent-teal-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {status === 'submitting' ? (
            <>
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-20" />
                <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
              </svg>
              Unlocking...
            </>
          ) : (
            <>
              Unlock full report
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
        We save your email to send occasional GEO updates. No spam, unsubscribe anytime.{' '}
        <a href="/privacy/" className="text-text-muted underline hover:text-text-secondary">Privacy Policy</a>
      </p>
    </div>
  );
}