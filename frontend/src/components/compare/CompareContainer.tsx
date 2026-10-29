import React, { useEffect, useState } from 'react';
import { fetchAuditReport } from '../../lib/api';
import type { AuditReport } from '../../lib/mockData';
import ReportHeader from '../report/ReportHeader';
import ScoreGauge from '../report/ScoreGauge';
import CategoryBreakdown from '../report/CategoryBreakdown';
import RecommendationList from '../report/RecommendationList';
import { toAuditableUrl } from '../../lib/urlInput';

type CompareState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; report1: AuditReport; report2: AuditReport };

function readQueryParams(): { url1: string; url2: string } {
  if (typeof window === 'undefined') return { url1: '', url2: '' };
  const params = new URLSearchParams(window.location.search);
  return {
    url1: params.get('url1') || '',
    url2: params.get('url2') || '',
  };
}

function CompactReport({ report }: { report: AuditReport }) {
  const criticalCount = report.recommendations.filter((r) => r.priority === 'critical').length;
  const highCount = report.recommendations.filter((r) => r.priority === 'high').length;
  const passSignals = report.technicalSignals.filter((s) => s.status === 'pass').length;
  const warnSignals = report.technicalSignals.filter((s) => s.status === 'warn').length;
  const failSignals = report.technicalSignals.filter((s) => s.status === 'fail').length;

  return (
    <div className="space-y-6">
      <ReportHeader
        url={report.url}
        geoScore={report.geoScore}
        citabilityScore={report.citabilityScore}
        grade={report.grade}
        timestamp={report.timestamp}
        version={report.version}
        criticalCount={criticalCount}
        highCount={highCount}
      />

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col items-center rounded-[10px] border border-rail bg-paper p-4">
          <ScoreGauge score={report.geoScore} label="GEO Score" />
        </div>
        <div className="flex flex-col items-center rounded-[10px] border border-rail bg-paper p-4">
          {report.citabilityScore === null ? (
            <div className="font-mono text-sm text-ink-mute">Citability not available</div>
          ) : (
            <ScoreGauge score={report.citabilityScore} label="Citability" />
          )}
        </div>
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-text text-[12.5px] font-semibold text-ink-mute">Category Breakdown</h2>
        </div>
        <CategoryBreakdown categories={report.categories} />
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-text text-[12.5px] font-semibold text-ink-mute">Technical Signals</h2>
          <span className="font-mono text-[11px] tabular-nums text-ink-mute">
            {passSignals} pass · {warnSignals} warn · {failSignals} fail
          </span>
        </div>
        <div className="text-sm text-ink-soft">
          {report.technicalSignals.map((s) => (
            <div key={s.id} className="flex items-center gap-2 border-b border-rail py-1.5 last:border-0">
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${
                  s.status === 'pass' ? 'bg-pass' : s.status === 'warn' ? 'bg-warn' : 'bg-fail'
                }`}
              />
              <span className="flex-1">{s.name}</span>
              <span className="text-xs text-ink-mute">{s.description}</span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-text text-[12.5px] font-semibold text-ink-mute">Recommendations</h2>
          <span className="font-mono text-[11px] tabular-nums text-ink-mute">{report.recommendations.length} total</span>
        </div>
        <RecommendationList recommendations={report.recommendations} />
      </section>
    </div>
  );
}

export default function CompareContainer() {
  const [{ url1, url2 }, setUrls] = useState(readQueryParams);
  const [state, setState] = useState<CompareState>({ status: 'idle' });

  useEffect(() => {
    const params = readQueryParams();
    if (!params.url1 || !params.url2) {
      setState({ status: 'idle' });
      return;
    }
    setUrls(params);
    setState({ status: 'loading' });

    Promise.all([fetchAuditReport(params.url1), fetchAuditReport(params.url2)]).then(([r1, r2]) => {
      if (r1.error || r2.error) {
        setState({
          status: 'error',
          message: `First: ${r1.error || 'OK'} — Second: ${r2.error || 'OK'}`,
        });
      } else if (r1.report && r2.report) {
        setState({ status: 'ready', report1: r1.report, report2: r2.report });
      } else {
        setState({ status: 'error', message: 'Unexpected empty response from one or both audits.' });
      }
    });
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Normalise before building the query string: the placeholders show bare
    // hostnames ("site-a.com"), and the raw value used to be forwarded as-is.
    const first = toAuditableUrl(url1);
    const second = toAuditableUrl(url2);
    if (!first || !second) return;
    const u = new URL(window.location.href);
    u.searchParams.set('url1', first);
    u.searchParams.set('url2', second);
    window.location.href = u.toString();
  };

  if (state.status === 'loading') {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 text-center sm:px-6">
        <div className="inline-flex items-center gap-2 text-sm text-ink-soft">
          <svg className="h-4 w-4 animate-spin text-pass-deep" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-20" />
            <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
          </svg>
          Running comparison audits...
        </div>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div
          role="alert"
          className="flex items-start gap-3 rounded-[10px] border border-fail/30 bg-fail-wash px-4 py-3 text-sm text-fail"
        >
          <span aria-hidden="true" className="mt-0.5 font-text text-[12.5px] font-semibold">
            err
          </span>
          <div>
            <div className="mb-1 font-semibold">Comparison failed</div>
            {state.message}
          </div>
        </div>
        <button
          onClick={() => setState({ status: 'idle' })}
          className="mt-4 inline-flex items-center gap-2 rounded-[10px] border border-rail bg-raised px-4 py-2 font-text text-[13px] font-semibold text-ink transition-colors hover:bg-pass-wash"
        >
          Back to form
        </button>
      </div>
    );
  }

  if (state.status === 'ready') {
    return (
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 md:py-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h2 className="font-head text-lg font-semibold tracking-[-0.01em] text-ink">Side-by-side comparison</h2>
            <span className="font-text font-medium text-[12.5px] text-ink-mute">POST /api/public/audits × 2</span>
          </div>
          <button
            onClick={() => {
              const u = new URL(window.location.href);
              u.search = '';
              window.location.href = u.toString();
            }}
            className="inline-flex items-center gap-2 rounded-[10px] border border-rail bg-raised px-3 py-1.5 font-text text-[12.5px] font-semibold text-ink transition-colors hover:bg-pass-wash"
          >
            New comparison
          </button>
        </div>

        {/* Solid-vs-Dashed: Site A (your baseline) is drawn solid, Site B (the
            competing profile) is drawn dashed — reference data, not yours. */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-[10px] border border-ink/40 bg-raised p-5 md:p-6">
            <div className="mb-4 border-b border-rail pb-3">
              <span className="rounded-[6px] border border-ink/40 px-1.5 py-0.5 font-text text-[12px] font-semibold text-ink">Site A</span>
              <p className="mt-2 truncate text-sm font-medium text-ink">{state.report1.url}</p>
            </div>
            <CompactReport report={state.report1} />
          </div>
          <div className="rounded-[10px] border border-dashed border-ink-mute/60 bg-raised p-5 md:p-6">
            <div className="mb-4 border-b border-rail pb-3">
              <span className="rounded-[6px] border border-dashed border-ink-mute/60 px-1.5 py-0.5 font-text text-[12px] font-semibold text-ink-mute">Site B</span>
              <p className="mt-2 truncate text-sm font-medium text-ink">{state.report2.url}</p>
            </div>
            <CompactReport report={state.report2} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6">
      <div className="overflow-hidden rounded-[10px] border border-rail bg-raised">
        <div className="flex items-center justify-between gap-3 border-b border-rail px-6 py-2.5 md:px-8">
          <span className="font-text text-[12.5px] font-semibold text-ink-mute">POST /api/public/audits × 2</span>
          <span className="rounded-[6px] border border-rail px-1.5 py-0.5 font-text font-medium text-[12px] text-ink-mute">idle</span>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6 p-6 md:p-8">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="url1" className="mb-2 block text-sm font-medium text-ink">First URL</label>
              <input
                id="url1"
                type="text"
                inputMode="url"
                required
                placeholder="https://site-a.com"
                value={url1}
                onChange={(e) => setUrls((prev) => ({ ...prev, url1: e.target.value }))}
                className="w-full rounded-[10px] border border-ink/25 bg-raised px-4 py-3 font-mono text-[15px] text-ink caret-pass-deep transition-shadow placeholder:text-ink-mute focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30"
              />
            </div>
            <div>
              <label htmlFor="url2" className="mb-2 block text-sm font-medium text-ink">Second URL</label>
              <input
                id="url2"
                type="text"
                inputMode="url"
                required
                placeholder="https://site-b.com"
                value={url2}
                onChange={(e) => setUrls((prev) => ({ ...prev, url2: e.target.value }))}
                className="w-full rounded-[10px] border border-ink/25 bg-raised px-4 py-3 font-mono text-[15px] text-ink caret-pass-deep transition-shadow placeholder:text-ink-mute focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30"
              />
            </div>
          </div>
          <button
            type="submit"
            className="rounded-[10px] bg-pass-deep px-7 py-3.5 font-text text-[13px] font-semibold text-on-accent transition-colors hover:bg-pass"
          >
            Compare
          </button>
        </form>
      </div>
    </div>
  );
}
