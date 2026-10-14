import React, { useEffect, useState } from 'react';
import { fetchAuditReport } from '../../lib/api';
import type { AuditReport } from '../../lib/mockData';
import ScoreGauge from '../report/ScoreGauge';

type CompetitorState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; reports: AuditReport[] };

function readQueryParam(): string {
  if (typeof window === 'undefined') return '';
  return new URLSearchParams(window.location.search).get('urls') || '';
}

function CompactCompetitorCard({ report, index }: { report: AuditReport; index: number }) {
  const criticalCount = report.recommendations.filter((r) => r.priority === 'critical').length;

  return (
    // Solid-vs-Dashed: every card in this batch is labelled "Competitor N",
    // so all of them are reference data and drawn dashed.
    <div className="rounded-[4px] border border-dashed border-ink-mute/60 bg-white p-5">
      <div className="mb-4 border-b border-rail pb-3">
        <span className="rounded-[2px] border border-dashed border-ink-mute/60 px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-mute">
          Competitor {index + 1}
        </span>
        <p className="mt-2 truncate text-sm font-medium text-ink">{report.url}</p>
      </div>

      <div className="mb-4 flex flex-col items-center">
        <ScoreGauge score={report.geoScore} label="GEO Score" />
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-ink-mute">Citability</span>
          <span className="font-mono font-semibold tabular-nums text-ink">{report.citabilityScore === null ? '—' : `${report.citabilityScore}/100`}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-ink-mute">Grade</span>
          <span className="font-mono font-semibold uppercase text-ink">{report.grade}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-ink-mute">Categories active</span>
          <span className="font-mono font-semibold tabular-nums text-ink">{report.categories.filter((c) => c.score > 0 && !c.locked).length}/{report.categories.length}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-ink-mute">Recommendations</span>
          <span className="font-mono font-semibold tabular-nums text-ink">{report.recommendations.length}</span>
        </div>
        {criticalCount > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-ink-mute">Critical</span>
            <span className="font-mono font-semibold tabular-nums text-fail">{criticalCount}</span>
          </div>
        )}
      </div>

      <div className="mt-4 border-t border-rail pt-3">
        <h3 className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Top issues</h3>
        <ul className="space-y-1.5">
          {report.recommendations.slice(0, 3).map((rec) => (
            <li key={rec.id} className="text-xs leading-snug text-ink-soft">
              <span
                className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-middle ${
                  rec.priority === 'critical'
                    ? 'bg-fail'
                    : rec.priority === 'high'
                      ? 'bg-warn'
                      : 'bg-ink-mute'
                }`}
              />
              {rec.title}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function AnalyzeCompetitorsContainer() {
  const [urlsInput, setUrlsInput] = useState(readQueryParam);
  const [state, setState] = useState<CompetitorState>({ status: 'idle' });

  useEffect(() => {
    const raw = readQueryParam();
    if (!raw.trim()) {
      setState({ status: 'idle' });
      return;
    }
    const urls = raw
      .split(',')
      .map((u) => u.trim())
      .filter((u) => u.startsWith('http'));
    if (urls.length === 0) {
      setState({ status: 'idle' });
      return;
    }
    setUrlsInput(raw);
    setState({ status: 'loading' });

    Promise.all(urls.map((u) => fetchAuditReport(u)))
      .then((results) => {
        const errors = results.filter((r) => r.error);
        if (errors.length > 0) {
          setState({
            status: 'error',
            message: `${errors.length} audit(s) failed: ${errors.map((e) => e.error).join('; ')}`,
          });
          return;
        }
        const reports = results.map((r) => r.report).filter(Boolean) as AuditReport[];
        if (reports.length === 0) {
          setState({ status: 'error', message: 'No valid reports returned.' });
          return;
        }
        setState({ status: 'ready', reports });
      })
      .catch((e) => setState({ status: 'error', message: e.message || 'Network error' }));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = urlsInput.trim();
    if (!trimmed) return;
    const u = new URL(window.location.href);
    u.searchParams.set('urls', trimmed);
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
          Running competitor audits...
        </div>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div
          role="alert"
          className="flex items-start gap-3 rounded-[4px] border border-fail/30 bg-fail-wash px-4 py-3 text-sm text-fail"
        >
          <span aria-hidden="true" className="mt-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em]">
            err
          </span>
          <div>
            <div className="mb-1 font-semibold">Analysis failed</div>
            {state.message}
          </div>
        </div>
        <button
          onClick={() => setState({ status: 'idle' })}
          className="mt-4 inline-flex items-center gap-2 rounded-[4px] border border-rail bg-white px-4 py-2 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-ink transition-colors hover:bg-pass-wash"
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
            <h2 className="font-head text-lg font-extrabold tracking-[-0.01em] text-ink">Competitor analysis</h2>
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-mute">POST /api/public/audits × {state.reports.length}</span>
          </div>
          <button
            onClick={() => {
              const u = new URL(window.location.href);
              u.search = '';
              window.location.href = u.toString();
            }}
            className="inline-flex items-center gap-2 rounded-[4px] border border-rail bg-white px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink transition-colors hover:bg-pass-wash"
          >
            New analysis
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {state.reports.map((report, i) => (
            <CompactCompetitorCard key={report.id} report={report} index={i} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6">
      <div className="overflow-hidden rounded-[4px] border border-rail bg-white">
        <div className="flex items-center justify-between gap-3 border-b border-rail px-6 py-2.5 md:px-8">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-mute">POST /api/public/audits · per domain</span>
          <span className="rounded-[2px] border border-rail px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-ink-mute">idle</span>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6 p-6 md:p-8">
          <div>
            <label htmlFor="urls" className="mb-2 block text-sm font-medium text-ink">Competitor URLs (comma-separated, max 5)</label>
            <input
              id="urls"
              type="text"
              required
              placeholder="https://competitor1.com, https://competitor2.com"
              value={urlsInput}
              onChange={(e) => setUrlsInput(e.target.value)}
              className="w-full rounded-[4px] border border-ink/25 bg-white px-4 py-3 font-mono text-[15px] text-ink caret-pass-deep transition-shadow placeholder:text-ink-mute focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30"
            />
            <p className="mt-1.5 text-xs text-ink-mute">Enter one or more URLs separated by commas.</p>
          </div>
          <button
            type="submit"
            className="rounded-[4px] bg-pass-deep px-7 py-3.5 font-mono text-[13px] font-semibold uppercase tracking-[0.12em] text-white transition-colors hover:bg-pass"
          >
            Analyze
          </button>
        </form>
      </div>
    </div>
  );
}
