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

type RecommendedPlan = {
  id: 'pro' | 'studio';
  name: 'Pro' | 'Studio';
  price: '$19' | '$49';
  cta: string;
  headline: string;
  reason: string;
  intent: string;
};

const planByCategory: Record<string, RecommendedPlan> = {
  robots: {
    id: 'pro',
    name: 'Pro',
    price: '$19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to keep technical GEO signals from regressing.',
    reason: 'This looks like a technical visibility problem. Pro is the right first upgrade when you need weekly checks, score history, PDF export, and regression alerts for one domain.',
    intent: 'technical_monitoring',
  },
  llms: {
    id: 'pro',
    name: 'Pro',
    price: '$19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to monitor llms.txt and crawl-readiness over time.',
    reason: 'llms.txt and crawler-discovery issues are usually fixed quickly, then monitored. Pro keeps the domain on a weekly audit loop and warns when the setup changes.',
    intent: 'llms_monitoring',
  },
  schema: {
    id: 'pro',
    name: 'Pro',
    price: '$19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to validate schema fixes every week.',
    reason: 'Schema regressions are easy to introduce during CMS, template, or release changes. Pro gives one-domain monitoring, history, and alerts after the first fix.',
    intent: 'schema_monitoring',
  },
  meta: {
    id: 'pro',
    name: 'Pro',
    price: '$19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to keep metadata and canonical signals stable.',
    reason: 'Metadata issues affect both classic SEO and AI answer extraction. Pro is enough when the main job is catching technical drift on one domain.',
    intent: 'metadata_monitoring',
  },
  signals: {
    id: 'pro',
    name: 'Pro',
    price: '$19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to catch freshness and technical signal drift.',
    reason: 'Freshness and technical signal changes are monitoring problems. Pro keeps a score history and alerts you when a working setup degrades.',
    intent: 'freshness_monitoring',
  },
  content: {
    id: 'studio',
    name: 'Studio',
    price: '$49',
    cta: 'Start Studio tracking',
    headline: 'Use Studio when the gap is citation quality, not just crawlability.',
    reason: 'Content gaps need more than a weekly technical score. Studio adds AI citation tracking, competitor comparison, and client-ready exports so you can see whether answer engines actually mention and cite you.',
    intent: 'citation_tracking',
  },
  ai_discovery: {
    id: 'studio',
    name: 'Studio',
    price: '$49',
    cta: 'Start Studio tracking',
    headline: 'Use Studio to track whether AI engines discover and cite the site.',
    reason: 'Discovery issues sit between technical access and answer-engine presence. Studio is the better fit when you need citation checks and competitor context, not only monitoring.',
    intent: 'ai_discovery_tracking',
  },
  brand_entity: {
    id: 'studio',
    name: 'Studio',
    price: '$49',
    cta: 'Start Studio tracking',
    headline: 'Use Studio when entity authority is the blocker.',
    reason: 'Brand and entity gaps show up in whether answer engines mention you against competitors. Studio adds citation tracking and comparison workflows for that job.',
    intent: 'entity_citation_tracking',
  },
};

interface AuditReportContainerProps {
  reportId: string;
}

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; report: AuditReport; claim_token: string | null; expires_at: string | null; repeat_count: number | null };

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

function recommendedPlanFor(category: CategoryScore | null): RecommendedPlan {
  if (!category) return planByCategory.robots;
  return planByCategory[category.slug] ?? planByCategory.robots;
}

function planSignupHref(plan: RecommendedPlan, claimToken: string | null): string {
  const params = new URLSearchParams({
    plan: plan.id,
    intent: plan.intent,
    onboarding: claimToken ? 'claim_report' : 'first_domain',
    utm_source: 'audit_report',
    utm_medium: 'result_cta',
    utm_campaign: 'free_audit_to_paid',
  });
  if (claimToken) {
    params.set('claim', claimToken);
    params.set('claim_source', 'free_audit_report');
  }
  return `https://app.geoready.dev/signup?${params.toString()}`;
}

function pricingHref(claimToken: string | null): string {
  const params = new URLSearchParams({
    utm_source: 'audit_report',
    utm_medium: 'result_cta',
    utm_campaign: 'free_audit_to_paid',
  });
  if (claimToken) {
    params.set('claim', claimToken);
    params.set('claim_source', 'free_audit_report');
  }
  return `/pricing/?${params.toString()}`;
}

function ReportNextStep({
  report,
  claimToken,
  criticalCount,
  highCount,
  repeatCount,
}: {
  report: AuditReport;
  claimToken: string | null;
  criticalCount: number;
  highCount: number;
  repeatCount: number | null;
}) {
  const weakest = findWeakestCategory(report.categories);
  const action = weakest ? categoryAction[weakest.slug] : null;
  const plan = recommendedPlanFor(weakest);
  const recs = topRecommendations(report.recommendations);
  const openIssues = criticalCount + highCount;
  // Recurring-need CTA per i re-auditor (growth: 665 URL ri-auditate a mano).
  // repeatCount è reale, contato server-side dagli anonymous_reports.
  const isRepeat = repeatCount !== null && repeatCount >= 1;
  const repeatHeadline = (() => {
    const host = report.url.replace(/^https?:\/\//, '').split('/')[0];
    const ordinal = repeatCount === 1 ? 'Second audit' : repeatCount === 2 ? 'Third audit' : `${repeatCount + 1}th audit`;
    return `${ordinal} of ${host}?`;
  })();
  const repeatReason =
    'You are re-checking this site by hand. The free plan runs the same audit weekly, emails you when the score moves, and keeps the full history — so the checking happens without you.';

  return (
    <section className="overflow-hidden rounded-[4px] border border-pass/50 bg-pass-wash/60">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-pass/30 px-5 py-2.5">
        <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-pass-deep">
          Recommended next step
        </span>
        <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-pass-deep">
          {plan.name} {plan.price}/mo
          {openIssues > 0 && <> · {openIssues} critical or high issues</>}
        </span>
      </div>

      <div className="flex flex-col gap-5 p-5 md:p-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-3xl">
          <h2 className="font-head text-xl font-extrabold tracking-[-0.02em] leading-tight text-ink md:text-2xl">
            {isRepeat ? repeatHeadline : plan.headline}
          </h2>

          <p className="mt-3 text-sm leading-relaxed text-ink-soft md:text-base">
            {isRepeat ? (
              repeatReason
            ) : weakest && action ? (
              <>
                The weakest area is <strong className="font-semibold text-ink">{weakest.name}</strong>
                {' '}at <strong className="font-semibold text-ink">{weakest.score}/{weakest.maxScore}</strong>.
                {' '}{action.detail}
                {' '}{plan.reason}
              </>
            ) : (
              plan.reason
            )}
          </p>

          {recs.length > 0 && (
            <ul className="mt-4 grid gap-2 text-sm text-ink-soft sm:grid-cols-3">
              {recs.map((rec) => (
                <li key={rec.id} className="flex gap-2 leading-snug">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ink-mute" aria-hidden="true" />
                  <span>{rec.title}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row lg:flex-col">
          <a
            href={planSignupHref(plan, claimToken)}
            data-plan-id={plan.id}
            data-plan-name={plan.name}
            data-plan-period="monthly"
            data-plan-price={plan.price}
            data-plan-currency="USD"
            data-cta-location="audit_report_next_step"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[4px] bg-pass-deep px-5 py-2.5 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-white transition-colors hover:bg-pass"
          >
            {plan.cta}
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
          <a
            href={pricingHref(claimToken)}
            data-cta="audit_report_next_step_pricing"
            className="inline-flex min-h-11 items-center justify-center rounded-[4px] border border-rail bg-white px-5 py-2.5 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-ink transition-colors hover:bg-pass-wash"
          >
            Compare plans
          </a>
          <p className="max-w-xs text-xs leading-relaxed text-ink-mute">
            {claimToken
              ? isRepeat
                ? 'This report carries over at signup, and weekly monitoring starts on this exact domain.'
                : 'Signup carries this report into the app so the first paid action is claiming the audited domain.'
              : 'After signup, the app opens on the first-domain monitoring step.'}
          </p>
        </div>
      </div>
    </section>
  );
}

export default function AuditReportContainer({ reportId }: AuditReportContainerProps) {
  const [state, setState] = useState<State>(() =>
    reportId === 'demo'
      ? { status: 'ready', report: mockAuditReport, claim_token: null, expires_at: null, repeat_count: null }
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
        setState({
          status: 'ready',
          report: result.report,
          claim_token: result.claim_token,
          expires_at: result.expires_at,
          repeat_count: result.repeat_count,
        });
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
        <div className="inline-flex items-center gap-2 font-mono text-[13px] text-ink-mute">
          <svg className="animate-spin w-4 h-4 text-pass-deep" viewBox="0 0 24 24" fill="none" aria-hidden="true">
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
        <div className="flex items-start gap-3 rounded-[4px] border border-fail/30 bg-fail-wash px-4 py-3 text-sm text-fail">
          <span aria-hidden="true" className="mt-0.5 font-mono text-[11px] font-semibold uppercase tracking-[0.12em]">
            err
          </span>
          <div>
            <div className="font-semibold mb-1">Audit failed</div>
            {state.message}
          </div>
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

      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[4px] border border-rail bg-rail sm:grid-cols-4">
        <div className="bg-white p-4">
          <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Categories</div>
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums">
            <span className="text-ink">{activeCategories}</span>
            <span className="text-sm text-ink-mute"> / {report.categories.length}</span>
          </div>
          <div className="mt-0.5 font-mono text-[10px] text-ink-mute">active</div>
        </div>
        <div className="bg-white p-4">
          <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Recommendations</div>
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums text-ink">{report.recommendations.length}</div>
          <div className="mt-0.5 font-mono text-[10px] text-ink-mute">{criticalCount} critical</div>
        </div>
        <div className="bg-white p-4">
          <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Signals</div>
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums">
            <span className="text-pass-deep">{passSignals}</span>
            <span className="text-sm text-ink-mute"> / {report.technicalSignals.length}</span>
          </div>
          <div className="mt-0.5 font-mono text-[10px] text-ink-mute">{warnSignals} warn, {failSignals} fail</div>
        </div>
        <div className="bg-white p-4">
          <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Citability</div>
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums text-ink-soft">{report.citabilityScore}</div>
          <div className="mt-0.5 font-mono text-[10px] text-ink-mute">/ 100</div>
        </div>
      </div>

      <ReportNextStep
        report={report}
        claimToken={state.claim_token}
        criticalCount={criticalCount}
        highCount={highCount}
        repeatCount={state.repeat_count}
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-3 space-y-4">
          <div className="flex flex-col items-center rounded-[4px] border border-rail bg-white p-5">
            <ScoreGauge score={report.geoScore} label="GEO Score" />
            <div className="mt-4 w-full border-t border-rail pt-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-ink-mute">Citability Score</span>
                <span className="font-mono font-semibold tabular-nums text-ink-soft">
                  {report.citabilityScore}/100
                </span>
              </div>
            </div>
          </div>

          <div className="rounded-[4px] border border-rail bg-white p-4">
            <h3 className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Export Report</h3>
            <ExportActions reportUrl={report.url} />
          </div>

          <ScoreHistory url={report.url} currentScore={report.geoScore} />
          <BenchmarkComparison score={report.geoScore} grade={report.grade} />
        </div>

        <div className="lg:col-span-9 space-y-8">
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Category Breakdown</h2>
              <span className="font-mono text-[11px] tabular-nums text-ink-mute">
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
              <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Technical Signals</h2>
              <span className="font-mono text-[11px] tabular-nums text-ink-mute">
                {passSignals} pass · {warnSignals} warn · {failSignals} fail
              </span>
            </div>
            <TechnicalSignals signals={report.technicalSignals} />
          </section>

          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Recommendations</h2>
              <div className="flex items-center gap-2 font-mono text-[11px] tabular-nums">
                {criticalCount > 0 && (
                  <span className="text-fail">{criticalCount} critical</span>
                )}
                {highCount > 0 && (
                  <span className="text-warn">{highCount} high</span>
                )}
                <span className="text-ink-mute">· {report.recommendations.length} total</span>
              </div>
            </div>
            <RecommendationList recommendations={report.recommendations} />
          </section>
        </div>
      </div>

      {state.claim_token && (
        <div className="mt-6 flex flex-col items-start gap-4 rounded-[4px] border border-pass/50 bg-pass-wash/60 p-5 sm:flex-row sm:items-center">
          <div className="flex-1">
            <p className="mb-0.5 text-sm font-semibold text-ink">Save this report to your dashboard</p>
            <p className="text-xs text-ink-soft">Create a free account to track this domain over time. Report link expires in 24h.</p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 shrink-0">
            <a
              href={`https://app.geoready.dev/signup?claim=${state.claim_token}`}
              onClick={() => trackCtaClicked({ cta_location: 'audit_report_claim', cta_text: 'Save report' })}
              className="inline-flex items-center justify-center gap-2 rounded-[4px] bg-pass-deep px-4 py-2 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-white transition-colors hover:bg-pass"
            >
              Save report
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </a>
            <a
              href={`https://app.geoready.dev/login?claim=${state.claim_token}`}
              onClick={() => trackCtaClicked({ cta_location: 'audit_report_claim', cta_text: 'Log in to save' })}
              className="inline-flex items-center justify-center rounded-[4px] border border-rail bg-white px-4 py-2 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-ink transition-colors hover:bg-pass-wash"
            >
              Log in to save
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
