import { useState } from 'react';
import { checkCitations } from '../../lib/api';
import type { CitationsCheckResult } from '../../lib/api';
import {
  trackCitationCheckerCompleted,
  trackCitationCheckerFailed,
  trackCitationCheckerStarted,
  trackPlanSelected,
} from '../../lib/geo_track';

type Status = 'idle' | 'loading' | 'error' | 'success';

type CitationsData = NonNullable<CitationsCheckResult['data']>;

// Copy del verdetto: stessa semantica dei verdetti della CLI `geo citations`.
const VERDICT_COPY: Record<
  CitationsData['verdict'],
  { icon: string; title: string; detail: string; tone: string }
> = {
  strong: {
    icon: '🏆',
    title: 'Strong — AI engines cite you',
    detail: 'Your domain appears as a source in most AI answers. Protect this position: it can degrade silently.',
    tone: 'border-emerald-500/40 bg-emerald-500/5',
  },
  cited: {
    icon: '✅',
    title: 'Cited — but not consistently',
    detail: 'Your domain shows up among AI sources, but not in every answer. There is room to win more.',
    tone: 'border-teal-500/40 bg-teal-500/5',
  },
  mentioned_only: {
    icon: '🟡',
    title: 'Mentioned, never cited',
    detail:
      'The AI knows your brand from third-party pages, but never cites your own domain as a source. Your content is not the reference yet.',
    tone: 'border-amber-500/40 bg-amber-500/5',
  },
  invisible: {
    icon: '❌',
    title: 'Invisible to AI answers',
    detail: 'AI answers neither mention your brand nor cite your domain. Your customers are being sent elsewhere.',
    tone: 'border-red-500/40 bg-red-500/5',
  },
};

export default function AICitationChecker() {
  const [brand, setBrand] = useState('');
  const [domain, setDomain] = useState('');
  const [topic, setTopic] = useState('');

  const [status, setStatus] = useState<Status>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [result, setResult] = useState<CitationsData | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrorMsg('');

    const trimmedBrand = brand.trim();
    const trimmedDomain = domain.trim();
    if (trimmedBrand.length < 2) {
      setStatus('error');
      setErrorMsg('Enter your brand name (at least 2 characters).');
      trackCitationCheckerFailed({ reason: 'validation' });
      return;
    }
    if (!trimmedDomain.includes('.')) {
      setStatus('error');
      setErrorMsg('Enter your domain, for example example.com.');
      trackCitationCheckerFailed({ reason: 'validation' });
      return;
    }

    setStatus('loading');
    setResult(null);
    trackCitationCheckerStarted({ has_topic: Boolean(topic.trim()) });

    const { data, error } = await checkCitations({
      brand: trimmedBrand,
      domain: trimmedDomain,
      topic: topic.trim() || undefined,
    });

    if (error || !data) {
      setStatus('error');
      setErrorMsg(error || 'Unexpected error. Try again.');
      trackCitationCheckerFailed({ reason: 'server' });
      return;
    }
    setResult(data);
    setStatus('success');
    trackCitationCheckerCompleted({
      verdict: data.verdict,
      brand_mention_rate: data.brand_mention_rate,
      domain_citation_rate: data.domain_citation_rate,
      cited_competitor_count: data.top_cited_domains.length,
    });
  }

  const verdict = result ? VERDICT_COPY[result.verdict] : null;

  return (
    <div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm font-medium text-text-primary">Brand name</span>
            <input
              type="text"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="Acme"
              className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-teal focus:outline-none"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-text-primary">Your domain</span>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="acme.com"
              className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-teal focus:outline-none"
            />
          </label>
        </div>
        <label className="block">
          <span className="text-sm font-medium text-text-primary">
            What do you sell? <span className="text-text-muted font-normal">(optional, sharpens the questions)</span>
          </span>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="project management software for agencies"
            className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-teal focus:outline-none"
          />
        </label>

        <button
          type="submit"
          disabled={status === 'loading'}
          className="w-full sm:w-auto rounded-lg bg-accent-teal px-6 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          {status === 'loading' ? 'Asking the AI… (~20s)' : 'Check my AI citations'}
        </button>
      </form>

      {status === 'error' && (
        <p className="mt-4 rounded-lg border border-red-500/40 bg-red-500/5 px-4 py-3 text-sm text-text-primary">
          {errorMsg}
        </p>
      )}

      {status === 'success' && result && verdict && (
        <div className="mt-8 space-y-6">
          <div className={`rounded-xl border px-5 py-4 ${verdict.tone}`}>
            <p className="text-lg font-semibold text-text-primary">
              {verdict.icon} {verdict.title}
            </p>
            <p className="mt-1 text-sm text-text-secondary">{verdict.detail}</p>
          </div>

          <div className="grid sm:grid-cols-2 gap-4 text-sm">
            <div className="rounded-lg border border-border px-4 py-3">
              <p className="text-text-muted">Brand mentioned</p>
              <p className="text-2xl font-bold text-text-primary">
                {Math.round(result.brand_mention_rate * 100)}%
              </p>
              <p className="text-xs text-text-muted">of AI answers analyzed</p>
            </div>
            <div className="rounded-lg border border-border px-4 py-3">
              <p className="text-text-muted">Domain cited as source</p>
              <p className="text-2xl font-bold text-text-primary">
                {Math.round(result.domain_citation_rate * 100)}%
              </p>
              <p className="text-xs text-text-muted">of AI answers analyzed</p>
            </div>
          </div>

          {result.top_cited_domains.length > 0 && (
            <div className="rounded-lg border border-border px-4 py-3">
              <p className="text-sm font-semibold text-text-primary">Cited instead of you</p>
              <ul className="mt-2 space-y-1 text-sm text-text-secondary">
                {result.top_cited_domains.map(([d, n]) => (
                  <li key={d}>
                    <span className="font-mono">{d}</span>
                    <span className="text-text-muted"> — in {n} answer{n > 1 ? 's' : ''}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-3">
            {result.entries.map((entry) => (
              <details key={entry.query} className="rounded-lg border border-border px-4 py-3 text-sm">
                <summary className="cursor-pointer text-text-primary">
                  “{entry.query}” — {entry.domain_cited ? '✅ cited' : entry.brand_mentioned ? '🟡 mentioned' : '❌ absent'}
                </summary>
                <p className="mt-2 text-text-secondary italic">“{entry.snippet}…”</p>
                {entry.cited_sources.length > 0 && (
                  <p className="mt-1 text-xs text-text-muted">Sources: {entry.cited_sources.join(', ')}</p>
                )}
              </details>
            ))}
          </div>

          <div className="rounded-xl border border-accent-teal/40 bg-accent-teal/5 px-5 py-4">
            <p className="text-sm font-semibold text-text-primary">
              This is one snapshot. AI answers change every week.
            </p>
            <p className="mt-1 text-sm text-text-secondary">
              GeoReady tracks your citations on a schedule, alerts you when you lose (or win) a spot, and shows
              who replaced you.
            </p>
            <a
              href="https://app.geoready.dev/signup?plan=studio&intent=citations&utm_source=ai_citation_checker&utm_medium=tool_result&utm_campaign=tool_to_paid"
              onClick={() => trackPlanSelected({
                plan_id: 'studio',
                plan_name: 'Studio',
                billing_period: 'monthly',
                price: '49',
                currency: 'USD',
                cta_location: 'citation_checker_result_tracking',
              })}
              className="mt-3 inline-block rounded-lg bg-accent-teal px-5 py-2 text-sm font-semibold text-white hover:opacity-90"
            >
              Track weekly citations
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
