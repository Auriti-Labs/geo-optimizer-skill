import React, { useEffect, useState } from 'react';
import { trackAuditCompleted, trackCtaClicked } from '../../lib/geo_track';
import { fetchAuditReport } from '../../lib/api';
import { mockAuditReport } from '../../lib/mockData';
import type { AuditReport, CategoryScore, Recommendation } from '../../lib/mockData';
import { saveScore } from '../../lib/scoreHistory';
import ReportHeader from './ReportHeader';
import ScoreGauge from './ScoreGauge';
import ScoreHistory from './ScoreHistory';
import BenchmarkComparison from './BenchmarkComparison';
import CategoryBreakdown from './CategoryBreakdown';
import EmailGateBanner from './EmailGateBanner';
import TechnicalSignals from './TechnicalSignals';
import RecommendationList from './RecommendationList';
import ExportActions from './ExportActions';

const FREE_SLUGS = new Set(['robots', 'meta', 'signals']);
const ALL_LOCKED_SLUGS = ['llms', 'schema', 'content', 'ai_discovery', 'brand_entity'];

const categoryAction: Record<string, { label: string; detail: string }> = {
  robots: {
    label: 'Fix crawler access first',
    detail: 'AI systems cannot cite pages they are blocked from reaching. Check robots.txt, X-Robots-Tag, and AI crawler directives before rewriting content.',
  },
  llms: {
    label: 'Publish an llms.txt source map',
    detail: 'Expose your best pages, product facts, pricing pages, docs, and canonical resources in one file that answer engines can parse quickly.',
  },
  schema: {
    label: 'Add machine-readable schema',
    detail: 'Ship Organization, WebSite, Article, Product, and FAQ JSON-LD where relevant so engines can resolve what the page, brand, and offer are.',
  },
  meta: {
    label: 'Stabilize page metadata',
    detail: 'Canonical URLs, titles, descriptions, and Open Graph tags reduce ambiguity when engines choose which URL or snippet to trust.',
  },
  content: {
    label: 'Rewrite for extractable answers',
    detail: 'Lead important sections with direct answers, add concrete facts, and split long explanations into self-contained blocks that can be cited.',
  },
  signals: {
    label: 'Monitor freshness signals',
    detail: 'Keep sitemap, feeds, dates, and core technical signals consistent so score regressions are visible before rankings or citations drop.',
  },
  ai_discovery: {
    label: 'Expose AI discovery endpoints',
    detail: 'Add /.well-known/ai.txt, summary files, and FAQ-style resources so answer engines can discover the site beyond standard HTML crawling.',
  },
  brand_entity: {
    label: 'Strengthen entity resolution',
    detail: 'Connect the brand, authors, social profiles, contact page, and sameAs references so engines can identify the company consistently.',
  },
};

const priorityRank: Record<Recommendation['priority'], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

interface AuditReportContainerProps {
  reportId: string;
}

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; report: AuditReport; claim_token: string | null; expires_at: string | null };

function categoryRatio(category: CategoryScore): number {
  if (category.maxScore <= 0) return 1;
  return category.score / category.maxScore;
}

function findWeakestCategory(categories: CategoryScore[]): CategoryScore | null {
  if (categories.length === 0) return null;
  return [...categories].sort((a, b) => categoryRatio(a) - categoryRatio(b))[0];
}

function topRecommendations(recommendations: Recommendation[]): Recommendation[] {
  return [...recommendations]
    .sort((a, b) => priorityRank[a.priority] - priorityRank[b.priority])
    .slice(0, 3);
}

function proSignupHref(claimToken: string | null): string {
  const params = new URLSearchParams({
    plan: 'pro',
    intent: 'report_monitoring',
    utm_source: 'audit_report',
    utm_medium: 'result_cta',
    utm_campaign: 'free_audit_to_paid',
  });
  if (claimToken) params.set('claim', claimToken);
  return `https://app.geoready.dev/signup?${params.toString()}`;
}

function ReportNextStep({
  report,
  claimToken,
  criticalCount,
  highCount,
}: {
  report: AuditReport;
  claimToken: string | null;
  criticalCount: number;
  highCount: number;
}) {
  const weakest = findWeakestCategory(report.categories);
  const action = weakest ? categoryAction[weakest.slug] : null;
  const recs = topRecommendations(report.recommendations);
  const openIssues = criticalCount + highCount;

  return (
    <section className="rounded-xl border border-accent-teal/25 bg-accent-teal/5 p-5 md:p-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-accent-teal">
            <span>Recommended next step</span>
            {openIssues > 0 && (
              <>
                <span className="w-1 h-1 rounded-full bg-accent-teal/70" />
                <span>{openIssues} critical or high issues</span>
              </>
            )}
          </div>

          <h2 className="mt-2 text-xl md:text-2xl font-bold text-text-primary leading-tight">
            Turn this one-time audit into weekly monitoring.
          </h2>

          <p className="mt-3 text-sm md:text-base text-text-secondary leading-relaxed">
            {weakest && action ? (
              <>
                The weakest area is <strong className="text-text-primary">{weakest.name}</strong>
                {' '}at <strong className="text-text-primary">{weakest.score}/{weakest.maxScore}</strong>.
                {' '}{action.detail}
              </>
            ) : (
              'GeoReady Pro keeps the same checks running every week, stores score history, and flags regressions before they become harder to diagnose.'
            )}
          </p>

          {recs.length > 0 && (
            <ul className="mt-4 grid gap-2 text-sm text-text-secondary sm:grid-cols-3">
              {recs.map((rec) => (
                <li key={rec.id} className="flex gap-2 leading-snug">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-teal" />
                  <span>{rec.title}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row lg:flex-col">
          <a
            href={proSignupHref(claimToken)}
            data-plan-id="pro"
            data-plan-name="Pro"
            data-plan-period="monthly"
            data-plan-price="$19"
            data-plan-currency="USD"
            data-cta-location="audit_report_next_step"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-accent-teal px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-teal-dark"
          >
            Monitor this URL
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
          <a
            href="/pricing/?utm_source=audit_report&utm_medium=result_cta&utm_campaign=free_audit_to_paid"
            data-cta="audit_report_next_step_pricing"
            className="inline-flex min-h-11 items-center justify-center rounded-lg border border-border bg-bg-surface px-5 py-2.5 text-sm font-semibold text-text-primary transition-colors hover:bg-bg-subtle"
          >
            Compare plans
          </a>
        </div>
      </div>
    </section>
  );
}

export default function AuditReportContainer({ reportId }: AuditReportContainerProps) {
  const [state, setState] = useState<State>(() =>
    reportId === 'demo'
      ? { status: 'ready', report: mockAuditReport, claim_token: null, expires_at: null }
      : { status: 'loading' }
  );

  useEffect(() => {
    if (reportId === 'demo') {
      return;
    }

    let targetUrl: string | null = null;
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlParam = params.get('url');
      if (urlParam) {
        targetUrl = urlParam;
      }
    }

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
  // All categories are visible on screen: the free report is complete, matching
  // the public API and the pricing promise ("no email required"). Email capture
  // below is optional (send-me-a-copy), not a gate.
  const lockedSlugs: string[] = [];
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

      <ReportNextStep
        report={report}
        claimToken={state.claim_token}
        criticalCount={criticalCount}
        highCount={highCount}
      />

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
          <BenchmarkComparison score={report.geoScore} grade={report.grade} />
        </div>

        <div className="lg:col-span-9 space-y-8">
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-muted">Category Breakdown</h2>
              <span className="text-[11px] text-text-muted">
                {activeCategories} of {report.categories.length} active
              </span>
            </div>
            <CategoryBreakdown categories={report.categories} lockedSlugs={lockedSlugs} />
            {!isDemo && state.claim_token && (
              <div className="mt-4">
                <EmailGateBanner
                  score={report.geoScore}
                  categories={report.categories}
                  claimToken={state.claim_token}
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
