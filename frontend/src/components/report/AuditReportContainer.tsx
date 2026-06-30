import React, { useEffect, useState } from 'react';
import { trackAuditCompleted, trackCtaClicked } from '../../lib/geo_track';
import { fetchAuditReport } from '../../lib/api';
import { mockAuditReport } from '../../lib/mockData';
import type { AuditReport } from '../../lib/mockData';
import { saveScore } from '../../lib/scoreHistory';
import ReportHeader from './ReportHeader';
import ScoreGauge from './ScoreGauge';
import ScoreHistory from './ScoreHistory';
import CategoryBreakdown from './CategoryBreakdown';
import GateBanner from './GateBanner';
import TechnicalSignals from './TechnicalSignals';
import RecommendationList from './RecommendationList';
import ExportActions from './ExportActions';

const FREE_SLUGS = new Set(['robots', 'meta', 'signals']);
const LOCKED_SLUGS = ['llms', 'schema', 'content', 'ai_discovery', 'brand_entity'];
const LOCKED_MAX_POINTS = 18 + 16 + 12 + 6 + 10; // 62

interface AuditReportContainerProps {
  reportId: string;
}

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; report: AuditReport; claim_token: string | null; expires_at: string | null };

export default function AuditReportContainer({ reportId }: AuditReportContainerProps) {
  // La demo è una pagina marketing indicizzabile: inizializza già con i dati mock
  // così l'isola viene renderizzata lato server (SSG) con il contenuto completo
  // del report, invece di uno shell vuoto idratato solo client-side.
  const [state, setState] = useState<State>(() =>
    reportId === 'demo'
      ? { status: 'ready', report: mockAuditReport, claim_token: null, expires_at: null }
      : { status: 'loading' }
  );

  useEffect(() => {
    if (reportId === 'demo') {
      // Stato già pronto dall'initializer; nessun fetch necessario per la demo.
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
        setState({ status: 'ready', report: result.report, claim_token: result.claim_token, expires_at: result.expires_at });
        trackAuditCompleted({
          score: result.report.geoScore,
          score_band: result.report.grade ?? 'unknown',
        });
        saveScore({
          url: result.report.url,
          score: result.report.geoScore,
          grade: result.report.grade ?? 'unknown',
          timestamp: new Date().toISOString(),
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
          <svg className="animate-spin w-4 h-4 text-accent-teal" viewBox="0 0 24 24" fill="none" aria-hidden="true">
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

  const isDemo = reportId === 'demo';
  const lockedSlugs = isDemo ? [] : LOCKED_SLUGS;
  const lockedSet = new Set(lockedSlugs);

  const criticalCount = report.recommendations.filter((r) => r.priority === 'critical').length;
  const highCount = report.recommendations.filter((r) => r.priority === 'high').length;
  const activeCategories = report.categories.filter((c) => c.score > 0 && !lockedSet.has(c.slug)).length;
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

          <ScoreHistory url={report.url} currentScore={report.geoScore} />
        </div>

        <div className="lg:col-span-9 space-y-8">
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-muted">Category Breakdown</h2>
              <span className="text-[11px] text-text-muted">
                {activeCategories} of {report.categories.filter((c) => !lockedSet.has(c.slug)).length} visible
                {lockedSlugs.length > 0 && (
                  <span className="ml-1 text-accent-teal">· {lockedSlugs.length} locked</span>
                )}
              </span>
            </div>
            <CategoryBreakdown categories={report.categories} lockedSlugs={lockedSlugs} />
            {lockedSlugs.length > 0 && (
              <div className="mt-4">
                <GateBanner
                  score={report.geoScore}
                  lockedCount={lockedSlugs.length}
                  totalLockedPoints={LOCKED_MAX_POINTS}
                />
              </div>
            )}
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

      {state.claim_token && (
        <div className="mt-6 rounded-xl border border-accent-teal/30 bg-accent-teal/5 p-5 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex-1">
            <p className="text-sm font-semibold text-text-primary mb-0.5">Save this report to your dashboard</p>
            <p className="text-xs text-text-secondary">Create a free account to track this domain over time. Report link expires in 24h.</p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 shrink-0">
            <a
              href={`https://app.geoready.dev/signup?claim=${state.claim_token}`}
              onClick={() => trackCtaClicked({ cta_location: 'audit_report_claim', cta_text: 'Save report' })}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-accent-teal text-white text-sm font-semibold hover:bg-accent-teal-dark transition-colors"
            >
              Save report
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </a>
            <a
              href={`https://app.geoready.dev/login?claim=${state.claim_token}`}
              onClick={() => trackCtaClicked({ cta_location: 'audit_report_claim', cta_text: 'Log in to save' })}
              className="inline-flex items-center justify-center px-4 py-2 rounded-lg border border-border text-text-primary text-sm font-semibold hover:bg-bg-subtle transition-colors"
            >
              Log in to save
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
