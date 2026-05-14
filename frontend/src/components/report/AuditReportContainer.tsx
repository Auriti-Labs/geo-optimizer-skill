import React, { useEffect, useState } from 'react';
import { trackAuditCompleted } from '../../lib/geo_track';
import { fetchAuditReport } from '../../lib/api';
import { mockAuditReport } from '../../lib/mockData';
import type { AuditReport } from '../../lib/mockData';
import ReportHeader from './ReportHeader';
import ScoreGauge from './ScoreGauge';
import CategoryBreakdown from './CategoryBreakdown';
import TechnicalSignals from './TechnicalSignals';
import RecommendationList from './RecommendationList';
import ExportActions from './ExportActions';

interface AuditReportContainerProps {
  reportId: string;
}

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; report: AuditReport };

export default function AuditReportContainer({ reportId }: AuditReportContainerProps) {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    if (reportId === 'demo') {
      setState({ status: 'ready', report: mockAuditReport });
      return;
    }

    // In una pagina statica i query params non sono disponibili a build time.
    // Leggiamo l'URL direttamente dal browser quando siamo client-side.
    let targetUrl: string | null = null;
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlParam = params.get('url');
      if (urlParam) {
        targetUrl = urlParam;
      }
    }

    // Fallback alla prop reportId (cache hash o URL codificato)
    if (!targetUrl && reportId) {
      const isHexId = /^[a-f0-9]{32}$/i.test(reportId);
      targetUrl = isHexId ? null : decodeURIComponent(reportId);
    }

    if (!targetUrl) {
      setState({ status: 'error', message: 'Report ID not resolvable. Use /report/demo for a sample.' });
      return;
    }

    setState({ status: 'loading' });

    fetchAuditReport(targetUrl).then((result) => {
      if (result.error) {
        setState({ status: 'error', message: result.error });
      } else if (result.report) {
        setState({ status: 'ready', report: result.report });
        trackAuditCompleted({
          score: result.report.geoScore,
          score_band: result.report.grade ?? 'unknown',
        });
      } else {
        setState({ status: 'error', message: 'Unexpected empty response.' });
      }
    });
  }, [reportId]);

  if (state.status === 'loading') {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 text-center">
        <div className="inline-flex items-center gap-2 text-sm text-text-muted">
          <svg className="animate-spin w-4 h-4 text-accent-teal" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-20" />
            <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
          </svg>
          Running audit...
        </div>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        <div className="p-5 rounded-xl border border-accent-danger/20 bg-accent-danger/5 text-accent-danger text-sm">
          <div className="font-semibold mb-1">Audit failed</div>
          {state.message}
        </div>
      </div>
    );
  }

  const report = state.report;
  const criticalCount = report.recommendations.filter((r) => r.priority === 'critical').length;
  const highCount = report.recommendations.filter((r) => r.priority === 'high').length;
  const activeCategories = report.categories.filter((c) => c.score > 0).length;
  const passSignals = report.technicalSignals.filter((s) => s.status === 'pass').length;
  const warnSignals = report.technicalSignals.filter((s) => s.status === 'warn').length;
  const failSignals = report.technicalSignals.filter((s) => s.status === 'fail').length;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 md:py-8 space-y-6">
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

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-lg border border-border bg-bg-surface">
          <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Categories</div>
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums">
            <span className="text-text-primary">{activeCategories}</span>
            <span className="text-text-muted text-sm"> / {report.categories.length}</span>
          </div>
          <div className="text-[10px] text-text-muted mt-0.5">active</div>
        </div>
        <div className="p-4 rounded-lg border border-border bg-bg-surface">
          <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Recommendations</div>
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums text-text-primary">{report.recommendations.length}</div>
          <div className="text-[10px] text-text-muted mt-0.5">{criticalCount} critical</div>
        </div>
        <div className="p-4 rounded-lg border border-border bg-bg-surface">
          <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Signals</div>
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums">
            <span className="text-accent-success">{passSignals}</span>
            <span className="text-text-muted text-sm"> / {report.technicalSignals.length}</span>
          </div>
          <div className="text-[10px] text-text-muted mt-0.5">{warnSignals} warn, {failSignals} fail</div>
        </div>
        <div className="p-4 rounded-lg border border-border bg-bg-surface">
          <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Citability</div>
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums text-text-secondary">{report.citabilityScore}</div>
          <div className="text-[10px] text-text-muted mt-0.5">/ 100</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-3 space-y-4">
          <div className="p-5 rounded-xl border border-border bg-bg-surface flex flex-col items-center">
            <ScoreGauge score={report.geoScore} label="GEO Score" />
            <div className="mt-4 w-full pt-4 border-t border-border">
              <div className="flex items-center justify-between text-xs">
                <span className="text-text-muted">Citability Score</span>
                <span className="font-mono font-semibold text-text-secondary">
                  {report.citabilityScore}/100
                </span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-border bg-bg-surface">
            <h3 className="text-[10px] font-mono font-semibold uppercase tracking-wider text-text-muted mb-3">Export Report</h3>
            <ExportActions reportUrl={report.url} />
          </div>
        </div>

        <div className="lg:col-span-9 space-y-8">
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-muted">Category Breakdown</h2>
              <span className="text-[11px] text-text-muted">
                {activeCategories} of {report.categories.length} active
              </span>
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
            <TechnicalSignals signals={report.technicalSignals} />
          </section>

          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-muted">Recommendations</h2>
              <div className="flex items-center gap-2">
                {criticalCount > 0 && (
                  <span className="text-[11px] font-mono text-accent-danger">{criticalCount} critical</span>
                )}
                {highCount > 0 && (
                  <span className="text-[11px] font-mono text-accent-warning">{highCount} high</span>
                )}
                <span className="text-[11px] text-text-muted">· {report.recommendations.length} total</span>
              </div>
            </div>
            <RecommendationList recommendations={report.recommendations} />
          </section>
        </div>
      </div>
    </div>
  );
}
