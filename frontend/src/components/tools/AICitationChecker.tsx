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

// Classi condivise del mondo console (input su ground bianco, ring pass al focus).
const FIELD_CLASSES =
  'mt-1 w-full rounded-[4px] border border-ink/25 bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-mute transition-colors focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30';

// Copy del verdetto: stessa semantica dei verdetti della CLI `geo citations`.
// L'icona emoji è sostituita da path SVG (stroke-width 2) disegnati inline;
// i toni usano i colori di stato del mondo console (pass / warn / fail).
const VERDICT_COPY: Record<
  CitationsData['verdict'],
  { iconPaths: string[]; title: string; detail: string; tone: string; iconTone: string }
> = {
  strong: {
    iconPaths: [
      'M8 21h8',
      'M12 17v4',
      'M7 4h10v4a5 5 0 0 1-10 0V4Z',
      'M7 6H4a3 3 0 0 0 3 3',
      'M17 6h3a3 3 0 0 1-3 3',
    ],
    title: 'Strong — AI engines cite you',
    detail: 'Your domain appears as a source in most AI answers. Protect this position: it can degrade silently.',
    tone: 'border-pass/40 bg-pass-wash',
    iconTone: 'text-pass-deep',
  },
  cited: {
    iconPaths: ['M20 6 9 17l-5-5'],
    title: 'Cited — but not consistently',
    detail: 'Your domain shows up among AI sources, but not in every answer. There is room to win more.',
    tone: 'border-pass/40 bg-pass-wash',
    iconTone: 'text-pass-deep',
  },
  mentioned_only: {
    iconPaths: ['M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Z', 'M12 8v4', 'M12 16h.01'],
    title: 'Mentioned, never cited',
    detail:
      'The AI knows your brand from third-party pages, but never cites your own domain as a source. Your content is not the reference yet.',
    tone: 'border-warn/40 bg-warn-wash',
    iconTone: 'text-warn',
  },
  invisible: {
    iconPaths: ['M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Z', 'm15 9-6 6', 'm9 9 6 6'],
    title: 'Invisible to AI answers',
    detail: 'AI answers neither mention your brand nor cite your domain. Your customers are being sent elsewhere.',
    tone: 'border-fail/40 bg-fail-wash',
    iconTone: 'text-fail',
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
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium text-ink">Brand name</span>
            <input
              type="text"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="Acme"
              className={FIELD_CLASSES}
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-ink">Your domain</span>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="acme.com"
              className={`${FIELD_CLASSES} font-mono`}
            />
          </label>
        </div>
        <label className="block">
          <span className="text-sm font-medium text-ink">
            What do you sell? <span className="font-normal text-ink-mute">(optional, sharpens the questions)</span>
          </span>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="project management software for agencies"
            className={FIELD_CLASSES}
          />
        </label>

        <button
          type="submit"
          disabled={status === 'loading'}
          className="w-full rounded-[4px] bg-pass-deep px-6 py-2.5 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-white transition-colors hover:bg-pass disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          {status === 'loading' ? 'Asking the AI… (~20s)' : 'Check my AI citations'}
        </button>
      </form>

      {status === 'error' && (
        <p
          role="alert"
          className="mt-4 flex items-start gap-3 rounded-[4px] border border-fail/30 bg-fail-wash px-4 py-3 text-sm text-fail"
        >
          <span aria-hidden="true" className="mt-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em]">
            err
          </span>
          <span>{errorMsg}</span>
        </p>
      )}

      {status === 'success' && result && verdict && (
        <div className="mt-8 space-y-6">
          <div className={`rounded-[4px] border px-5 py-4 ${verdict.tone}`}>
            <p className="flex items-start gap-2.5 text-lg font-semibold text-ink">
              <svg
                viewBox="0 0 24 24"
                className={`mt-1 h-5 w-5 shrink-0 ${verdict.iconTone}`}
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                {verdict.iconPaths.map((d) => (
                  <path key={d} d={d} />
                ))}
              </svg>
              <span>{verdict.title}</span>
            </p>
            <p className="mt-1 text-sm text-ink-soft">{verdict.detail}</p>
          </div>

          <div className="grid gap-px overflow-hidden rounded-[4px] border border-rail bg-rail text-sm sm:grid-cols-2">
            <div className="bg-white px-4 py-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-mute">Brand mentioned</p>
              <p className="mt-1 font-mono text-2xl font-semibold tabular-nums text-ink">
                {Math.round(result.brand_mention_rate * 100)}%
              </p>
              <p className="text-xs text-ink-mute">of AI answers analyzed</p>
            </div>
            <div className="bg-white px-4 py-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-mute">Domain cited as source</p>
              <p className="mt-1 font-mono text-2xl font-semibold tabular-nums text-ink">
                {Math.round(result.domain_citation_rate * 100)}%
              </p>
              <p className="text-xs text-ink-mute">of AI answers analyzed</p>
            </div>
          </div>

          {result.top_cited_domains.length > 0 && (
            <div className="rounded-[4px] border border-rail bg-white px-4 py-3">
              <p className="text-sm font-semibold text-ink">Cited instead of you</p>
              <ul className="mt-2 space-y-1 text-sm text-ink-soft">
                {result.top_cited_domains.map(([d, n]) => (
                  <li key={d}>
                    <span className="font-mono">{d}</span>
                    <span className="text-ink-mute"> — in {n} answer{n > 1 ? 's' : ''}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-3">
            {result.entries.map((entry) => (
              <details key={entry.query} className="rounded-[4px] border border-rail bg-white px-4 py-3 text-sm">
                <summary className="cursor-pointer text-ink">
                  “{entry.query}” —{' '}
                  <span
                    className={`font-mono text-[11px] font-semibold uppercase tracking-[0.1em] ${
                      entry.domain_cited ? 'text-pass-deep' : entry.brand_mentioned ? 'text-warn' : 'text-fail'
                    }`}
                  >
                    {entry.domain_cited ? 'cited' : entry.brand_mentioned ? 'mentioned' : 'absent'}
                  </span>
                </summary>
                <p className="mt-2 italic text-ink-soft">“{entry.snippet}…”</p>
                {entry.cited_sources.length > 0 && (
                  <p className="mt-1 text-xs text-ink-mute">
                    Sources: <span className="font-mono">{entry.cited_sources.join(', ')}</span>
                  </p>
                )}
              </details>
            ))}
          </div>

          <div className="rounded-[4px] border border-pass/40 bg-pass-wash/60 px-5 py-4">
            <p className="text-sm font-semibold text-ink">
              This is one snapshot. AI answers change every week.
            </p>
            <p className="mt-1 text-sm text-ink-soft">
              GeoReady tracks your citations on a schedule, alerts you when you lose (or win) a spot, and shows
              who replaced you.
            </p>
            <a
              href="https://app.geoready.dev/signup?plan=agency&intent=citations&utm_source=ai_citation_checker&utm_medium=tool_result&utm_campaign=tool_to_paid"
              onClick={() => trackPlanSelected({
                plan_id: 'agency',
                plan_name: 'Agency',
                billing_period: 'monthly',
                price: '89',
                currency: 'USD',
                cta_location: 'citation_checker_result_tracking',
              })}
              className="mt-3 inline-block rounded-[4px] bg-pass-deep px-5 py-2 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-white transition-colors hover:bg-pass"
            >
              Track weekly citations
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
