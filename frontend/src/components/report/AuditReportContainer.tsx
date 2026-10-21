import React, { useEffect, useState } from 'react';
import { trackAuditCompleted, trackCtaClicked } from '../../lib/geo_track';
import { fetchAuditReport } from '../../lib/api';
import { mockAuditReport } from '../../lib/mockData';
import type { AuditReport, CategoryScore } from '../../lib/mockData';
import { saveScore } from '../../lib/scoreHistory';
import { estimateAfterFreeFixes, type CategoryGain } from '../../lib/reportEstimate';
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

type RecommendedPlan = {
  id: 'pro' | 'agency';
  name: 'Pro' | 'Agency';
  price: '€19' | '€89';
  cta: string;
  headline: string;
  reason: string;
  intent: string;
};

const planByCategory: Record<string, RecommendedPlan> = {
  robots: {
    id: 'pro',
    name: 'Pro',
    price: '€19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to keep technical GEO signals from regressing.',
    reason: 'This looks like a technical visibility problem. Pro is the right first upgrade when you need weekly checks, score history, PDF export, and regression alerts for up to 10 domains.',
    intent: 'technical_monitoring',
  },
  llms: {
    id: 'pro',
    name: 'Pro',
    price: '€19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to monitor llms.txt and crawl-readiness over time.',
    reason: 'llms.txt and crawler-discovery issues are usually fixed quickly, then monitored. Pro keeps the domain on a weekly audit loop and warns when the setup changes.',
    intent: 'llms_monitoring',
  },
  schema: {
    id: 'pro',
    name: 'Pro',
    price: '€19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to validate schema fixes every week.',
    reason: 'Schema regressions are easy to introduce during CMS, template, or release changes. Pro gives one-domain monitoring, history, and alerts after the first fix.',
    intent: 'schema_monitoring',
  },
  meta: {
    id: 'pro',
    name: 'Pro',
    price: '€19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to keep metadata and canonical signals stable.',
    reason: 'Metadata issues affect both classic SEO and AI answer extraction. Pro is enough when the main job is catching technical drift on up to 10 domains.',
    intent: 'metadata_monitoring',
  },
  signals: {
    id: 'pro',
    name: 'Pro',
    price: '€19',
    cta: 'Start Pro monitoring',
    headline: 'Start with Pro to catch freshness and technical signal drift.',
    reason: 'Freshness and technical signal changes are monitoring problems. Pro keeps a score history and alerts you when a working setup degrades.',
    intent: 'freshness_monitoring',
  },
  content: {
    id: 'agency',
    name: 'Agency',
    price: '€89',
    cta: 'Start Agency tracking',
    headline: 'Use Agency when the gap is citation quality, not just crawlability.',
    reason: 'Content gaps need more than a weekly technical score. Agency adds AI citation tracking, competitor comparison, and client-ready exports so you can see whether answer engines actually mention and cite you.',
    intent: 'citation_tracking',
  },
  ai_discovery: {
    id: 'agency',
    name: 'Agency',
    price: '€89',
    cta: 'Start Agency tracking',
    headline: 'Use Agency to track whether AI engines discover and cite the site.',
    reason: 'Discovery issues sit between technical access and answer-engine presence. Agency is the better fit when you need citation checks and competitor context, not only monitoring.',
    intent: 'ai_discovery_tracking',
  },
  brand_entity: {
    id: 'agency',
    name: 'Agency',
    price: '€89',
    cta: 'Start Agency tracking',
    headline: 'Use Agency when entity authority is the blocker.',
    reason: 'Brand and entity gaps show up in whether answer engines mention you against competitors. Agency adds citation tracking and comparison workflows for that job.',
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
  // Una categoria bloccata non va citata: la sua scheda mostra "??"
  const visible = categories.filter((c) => !c.locked);
  if (visible.length === 0) return null;
  return [...visible].sort((a, b) => categoryRatio(a) - categoryRatio(b))[0];
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

function claimHref(claimToken: string | null): string {
  const params = new URLSearchParams({
    onboarding: claimToken ? 'claim_report' : 'first_domain',
    utm_source: 'audit_report',
    utm_medium: 'result_cta',
    utm_campaign: 'free_claim',
  });
  if (claimToken) {
    params.set('claim', claimToken);
    params.set('claim_source', 'free_audit_report');
  }
  return `https://app.geoready.dev/signup?${params.toString()}`;
}

/** URL della report page che riesegue l'audit dello stesso indirizzo. */
function rerunHref(url: string): string {
  return `/report/audit/?url=${encodeURIComponent(url)}`;
}

/** "Robots.txt +14, Meta Tags +6 and Signals +3" */
function formatGains(gains: CategoryGain[]): string {
  const parts = gains.map((g) => `${g.name} +${g.points}`);
  if (parts.length <= 1) return parts.join('');
  return `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}`;
}

/**
 * Pannello "prossimo passo" del report.
 *
 * Ordine voluto (revisione del funnel del 13/10): prima cosa si recupera
 * gratis e come verificarlo, poi il claim gratuito, e solo dopo l'offerta a
 * pagamento. La stima è aritmetica sui dati dell'audit (vedi reportEstimate.ts).
 */
function ReportNextStep({
  report,
  claimToken,
  repeatCount,
}: {
  report: AuditReport;
  claimToken: string | null;
  repeatCount: number | null;
}) {
  const weakest = findWeakestCategory(report.categories);
  const plan = recommendedPlanFor(weakest);
  const estimate = estimateAfterFreeFixes(report);
  const lockedNames = report.categories.filter((c) => c.locked && c.score < c.maxScore).map((c) => c.name);
  const hasGain = estimate.ceiling > estimate.baseline;

  // Recurring-need CTA per i re-auditor: repeatCount è reale, contato
  // server-side dagli anonymous_reports.
  const isRepeat = repeatCount !== null && repeatCount >= 1;
  const host = report.url.replace(/^https?:\/\//, '').split('/')[0];
  const ordinal = repeatCount === 1 ? 'Second' : repeatCount === 2 ? 'Third' : `${(repeatCount ?? 0) + 1}th`;

  return (
    <section className="overflow-hidden rounded-[4px] border border-pass/50 bg-pass-wash/60">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-pass/30 px-5 py-2.5">
        <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-pass-deep">
          Your baseline
        </span>
        <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-pass-deep">
          {estimate.freeFixCount} free {estimate.freeFixCount === 1 ? 'fix' : 'fixes'} on this page
        </span>
      </div>

      <div className="space-y-6 p-5 md:p-6">
        {/* Baseline → tetto stimato */}
        <div>
          <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1 font-head font-extrabold tracking-[-0.02em] text-ink">
            <span className="text-3xl tabular-nums md:text-4xl">
              {estimate.baseline}
              <span className="text-lg text-ink-mute">/100</span>
            </span>
            {hasGain && (
              <>
                <span className="text-xl text-ink-mute" aria-hidden="true">→</span>
                <span className="text-3xl tabular-nums text-pass-deep md:text-4xl">
                  <span className="mr-1 align-middle font-mono text-[11px] font-semibold uppercase tracking-[0.12em]">up to</span>
                  {estimate.ceiling}
                  <span className="text-lg text-ink-mute">/100</span>
                </span>
              </>
            )}
          </p>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-soft md:text-base">
            {hasGain ? (
              <>
                If every free fix on this page lands: {formatGains(estimate.freeGains)}.
              </>
            ) : (
              <>The categories with free fixes on this page are already at their maximum.</>
            )}
            {estimate.lockedGain > 0 && lockedNames.length > 0 && (
              <>
                {' '}Another {estimate.lockedGain} points sit in {lockedNames.join(', ')}, whose fix details are part of Pro.
              </>
            )}
          </p>
          <p className="mt-1 max-w-3xl text-xs leading-relaxed text-ink-mute">
            How this is computed: your current score plus the points still missing in the categories whose fixes are
            listed here. It is a ceiling, not a forecast.
          </p>
        </div>

        {/* Loop gratuito: correggi → ri-verifica → segui il punteggio */}
        <ol className="grid gap-px overflow-hidden rounded-[4px] border border-rail bg-rail sm:grid-cols-3">
          <li className="bg-white p-4">
            <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-pass-deep">1 · Fix</div>
            <p className="mt-1 text-sm leading-snug text-ink-soft">
              Apply the fixes listed under Recommendations. They are free and need no account.
            </p>
          </li>
          <li className="bg-white p-4">
            <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-pass-deep">2 · Re-run</div>
            <p className="mt-1 text-sm leading-snug text-ink-soft">
              Audit the same URL again, free. Results are cached for about an hour, so re-run after your change is live.
            </p>
            <a
              href={rerunHref(report.url)}
              onClick={() => trackCtaClicked({ cta_location: 'audit_report_loop', cta_text: 'Re-run audit' })}
              className="mt-2 inline-flex font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-pass-deep underline decoration-rail underline-offset-4 hover:decoration-pass-deep"
            >
              Re-run audit
            </a>
          </li>
          <li className="bg-white p-4">
            <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-pass-deep">3 · Watch it climb</div>
            <p className="mt-1 text-sm leading-snug text-ink-soft">
              This browser keeps your score history. Claim the report to keep it in your account, with a weekly re-check.
            </p>
          </li>
        </ol>

        {/* Claim gratuito, separato dall'offerta a pagamento */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold text-ink">
              {isRepeat ? `${ordinal} audit of ${host}?` : 'Keep this baseline.'}
            </p>
            <p className="mt-0.5 text-sm leading-relaxed text-ink-soft">
              {isRepeat
                ? 'You are re-checking this site by hand. A free account keeps your last 5 audits and runs one real AI answer check a week. Weekly re-audits and drift alerts start on Pro.'
                : 'A free account saves this report, keeps your last 5 audits and runs one real AI answer check a week, so you can see how AI engines talk about the site. Weekly re-audits start on Pro.'}
            </p>
          </div>
          <a
            href={claimHref(claimToken)}
            data-cta-location="audit_report_claim_free"
            onClick={() =>
              trackCtaClicked({
                cta_location: 'audit_report_claim_free',
                cta_text: claimToken ? 'Claim this report' : 'Track this domain',
              })
            }
            className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-[4px] bg-pass-deep px-5 py-2.5 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-white transition-colors hover:bg-pass"
          >
            {claimToken ? 'Claim this report — free' : 'Track this domain — free'}
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
        </div>

        {/* Offerta a pagamento: dopo il percorso gratuito */}
        <div className="flex flex-col gap-3 border-t border-pass/30 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-2xl text-sm leading-relaxed text-ink-soft">
            <span className="font-semibold text-ink">
              Want it watched for you? {plan.name} {plan.price}/mo.
            </span>{' '}
            {plan.headline}
          </p>
          <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
            <a
              href={planSignupHref(plan, claimToken)}
              data-plan-id={plan.id}
              data-plan-name={plan.name}
              data-plan-period="monthly"
              data-plan-price={plan.price}
              data-plan-currency="EUR"
              data-cta-location="audit_report_next_step"
              className="inline-flex min-h-11 items-center justify-center rounded-[4px] border border-pass-deep bg-white px-5 py-2.5 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-pass-deep transition-colors hover:bg-pass-wash"
            >
              {plan.cta}
            </a>
            <a
              href={pricingHref(claimToken)}
              data-cta="audit_report_next_step_pricing"
              className="inline-flex min-h-11 items-center justify-center rounded-[4px] border border-rail bg-white px-5 py-2.5 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-ink transition-colors hover:bg-pass-wash"
            >
              Compare plans
            </a>
          </div>
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
  // The free report is meant to be complete ("no email required"); email capture
  // below is optional (send-me-a-copy), not a gate. If the backend still sends a
  // gated payload, its locked categories are shown as locked instead of being
  // rendered as failed checks from missing data.
  const lockedSlugs: string[] = report.categories.filter((c) => c.locked).map((c) => c.slug);
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
          <div className="mt-1 font-mono text-lg font-semibold tabular-nums text-ink-soft">{report.citabilityScore ?? '—'}</div>
          <div className="mt-0.5 font-mono text-[10px] text-ink-mute">/ 100</div>
        </div>
      </div>

      <ReportNextStep
        report={report}
        claimToken={state.claim_token}
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
                  {report.citabilityScore === null ? '—' : `${report.citabilityScore}/100`}
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
            <p className="text-xs text-ink-soft">Create a free account to save this report and see how AI engines answer about this site. Report link expires in 24h.</p>
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
