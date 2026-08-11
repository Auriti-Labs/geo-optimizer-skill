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
        <div className="p-4 rounded-lg border border-border bg-bg-surface flex flex-col items-center">
          <ScoreGauge score={report.geoScore} label="GEO Score" />
        </div>
        <div className="p-4 rounded-lg border border-border bg-bg-surface flex flex-col items-center">
          <ScoreGauge score={report.citabilityScore} label="Citability" />
        </div>
      </div>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-muted">Category Breakdown</h2>
        </div>
        <CategoryBreakdown categories={report.categories} />
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-muted">Technical Signals</h2>
          <span className="text-[11px] text-text-muted">
            {passSignals} pass · {warnSignals} warn · {failSignals} fail
          </span>
        </div>
        <div className="text-sm text-text-secondary">
          {report.technicalSignals.map((s) => (
            <div key={s.id} className="flex items-center gap-2 py-1.5 border-b border-border last:border-0">
              <span
                className={`w-2 h-2 rounded-full shrink-0 ${
                  s.status === 'pass' ? 'bg-accent-success' : s.status === 'warn' ? 'bg-accent-warning' : 'bg-accent-danger'
                }`}
              />
              <span className="flex-1">{s.name}</span>
              <span className="text-text-muted text-xs">{s.description}</span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-muted">Recommendations</h2>
          <span className="text-[11px] text-text-muted">{report.recommendations.length} total</span>
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 text-center">
        <div className="inline-flex items-center gap-2 text-sm text-text-muted">
          <svg className="animate-spin w-4 h-4 text-accent-teal" viewBox="0 0 24 24" fill="none">
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="p-5 rounded-xl border border-accent-danger/20 bg-accent-danger/5 text-accent-danger text-sm">
          <div className="font-semibold mb-1">Comparison failed</div>
          {state.message}
        </div>
        <button
          onClick={() => setState({ status: 'idle' })}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-text-primary hover:border-accent-teal/30 transition-colors"
        >
          Back to form
        </button>
      </div>
    );
  }

  if (state.status === 'ready') {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 md:py-8 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-bold text-text-primary">Side-by-side comparison</h2>
          <button
            onClick={() => {
              const u = new URL(window.location.href);
              u.search = '';
              window.location.href = u.toString();
            }}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-text-primary hover:border-accent-teal/30 transition-colors"
          >
            New comparison
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="rounded-xl border border-border bg-bg-surface p-5 md:p-6">
            <div className="mb-4 pb-3 border-b border-border">
              <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-accent-teal">Site A</span>
              <p className="mt-1 text-sm text-text-primary font-medium truncate">{state.report1.url}</p>
            </div>
            <CompactReport report={state.report1} />
          </div>
          <div className="rounded-xl border border-border bg-bg-surface p-5 md:p-6">
            <div className="mb-4 pb-3 border-b border-border">
              <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-accent-warning">Site B</span>
              <p className="mt-1 text-sm text-text-primary font-medium truncate">{state.report2.url}</p>
            </div>
            <CompactReport report={state.report2} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6">
      <div className="p-6 md:p-8 rounded-xl border border-border bg-bg-surface">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="url1" className="block text-sm font-medium mb-2">First URL</label>
              <input
                id="url1"
                type="text"
                inputMode="url"
                required
                placeholder="https://site-a.com"
                value={url1}
                onChange={(e) => setUrls((prev) => ({ ...prev, url1: e.target.value }))}
                className="w-full px-4 py-3 rounded-lg border border-border bg-bg-base text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal transition-shadow"
              />
            </div>
            <div>
              <label htmlFor="url2" className="block text-sm font-medium mb-2">Second URL</label>
              <input
                id="url2"
                type="text"
                inputMode="url"
                required
                placeholder="https://site-b.com"
                value={url2}
                onChange={(e) => setUrls((prev) => ({ ...prev, url2: e.target.value }))}
                className="w-full px-4 py-3 rounded-lg border border-border bg-bg-base text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal transition-shadow"
              />
            </div>
          </div>
          <button
            type="submit"
            className="px-6 py-3 rounded-lg bg-accent-teal text-white font-medium text-sm hover:bg-accent-teal-dark transition-colors"
          >
            Compare
          </button>
        </form>
      </div>
    </div>
  );
}
