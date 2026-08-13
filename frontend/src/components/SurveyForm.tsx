import { useState, useRef } from 'react';
import { trackSurveyStarted, trackSurveyCompleted } from '../lib/geo_track';

type FormState = 'idle' | 'loading' | 'success' | 'error';

const CURRENT_TOOL_OPTIONS = [
  { value: 'nothing', label: "I don't check AI visibility" },
  { value: 'manual', label: 'Manual check (ChatGPT/Perplexity by hand)' },
  { value: 'seo-tool', label: 'SEO tool (Semrush, Ahrefs, etc.)' },
  { value: 'geo-cli', label: 'GEO Optimizer CLI' },
  { value: 'other', label: 'Other tool or script' },
];

const MAIN_PROBLEM_OPTIONS = [
  { value: 'not-visible', label: "Don't know if my site appears in AI answers" },
  { value: 'no-monitoring', label: 'No way to track visibility changes over time' },
  { value: 'client-reports', label: "Can't deliver GEO reports to clients" },
  { value: 'no-fix-guidance', label: "Know I have issues but don't know how to fix them" },
  { value: 'no-problem', label: 'I manage fine without a dedicated tool' },
];

const WTP_OPTIONS = [
  { value: 'yes-now', label: 'Yes, I would pay today if the tool existed' },
  { value: 'yes-trial', label: 'Yes, but I need to try it first' },
  { value: 'maybe', label: "Maybe — depends on what's included" },
  { value: 'no', label: 'No, the free tier is enough for me' },
];

const PRIORITY_FEATURE_OPTIONS = [
  { value: 'monitoring', label: 'Weekly AI search monitoring with alerts' },
  { value: 'history', label: 'Score history and audit log' },
  { value: 'pdf', label: 'PDF report export for clients' },
  { value: 'full-report', label: 'Deeper per-signal detail in reports' },
  { value: 'api', label: 'API access for integrations' },
  { value: 'agency', label: 'White-label reporting for agencies' },
];

const ANALYTICS_ENDPOINT =
  (import.meta as unknown as { env: Record<string, string> }).env
    .PUBLIC_ANALYTICS_ENDPOINT ?? 'https://app.geoready.dev/api/analytics/event';

export default function SurveyForm() {
  const [state, setState] = useState<FormState>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const startedRef = useRef(false);

  function handleFirstInteraction() {
    if (!startedRef.current) {
      startedRef.current = true;
      trackSurveyStarted();
    }
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setState('loading');

    const form = e.currentTarget;
    const data = new FormData(form);

    const payload = {
      event: 'geo_survey_completed',
      properties: {
        current_tool: data.get('current_tool') as string,
        main_problem: data.get('main_problem') as string,
        wtp: data.get('wtp') as string,
        priority_feature: data.get('priority_feature') as string,
      },
    };

    try {
      const res = await fetch(ANALYTICS_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      trackSurveyCompleted({
        wtp: payload.properties.wtp,
        main_problem: payload.properties.main_problem,
      });
      setState('success');
    } catch {
      setState('error');
      setErrorMsg('Could not submit. Please try again.');
    }
  }

  if (state === 'success') {
    return (
      <div className="rounded-[--radius-lg] border border-border bg-bg-surface p-6 text-center">
        <div className="w-10 h-10 rounded-full bg-accent-success/10 flex items-center justify-center mx-auto mb-4">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-success">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <p className="text-base font-semibold text-text-primary">Thanks — feedback received.</p>
        <p className="mt-2 text-sm text-text-secondary">
          Your answers directly shape what we build first.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5" onChange={handleFirstInteraction}>
      <div>
        <label htmlFor="sv-current-tool" className="block text-sm font-medium text-text-primary mb-1.5">
          How do you currently check your site's AI visibility? <span className="text-accent-danger">*</span>
        </label>
        <select
          id="sv-current-tool"
          name="current_tool"
          required
          className="w-full px-3 py-2 rounded-[--radius-md] border border-border bg-bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors"
        >
          <option value="">Select…</option>
          {CURRENT_TOOL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="sv-main-problem" className="block text-sm font-medium text-text-primary mb-1.5">
          What's your main pain point with AI search visibility? <span className="text-accent-danger">*</span>
        </label>
        <select
          id="sv-main-problem"
          name="main_problem"
          required
          className="w-full px-3 py-2 rounded-[--radius-md] border border-border bg-bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors"
        >
          <option value="">Select…</option>
          {MAIN_PROBLEM_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="sv-wtp" className="block text-sm font-medium text-text-primary mb-1.5">
          Would you pay $19/month for GeoReady Pro? <span className="text-accent-danger">*</span>
        </label>
        <select
          id="sv-wtp"
          name="wtp"
          required
          className="w-full px-3 py-2 rounded-[--radius-md] border border-border bg-bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors"
        >
          <option value="">Select…</option>
          {WTP_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="sv-priority" className="block text-sm font-medium text-text-primary mb-1.5">
          What feature would you use most? <span className="text-accent-danger">*</span>
        </label>
        <select
          id="sv-priority"
          name="priority_feature"
          required
          className="w-full px-3 py-2 rounded-[--radius-md] border border-border bg-bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors"
        >
          <option value="">Select…</option>
          {PRIORITY_FEATURE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {state === 'error' && (
        <p role="alert" className="text-sm text-accent-danger bg-accent-danger/5 border border-accent-danger/20 rounded-[--radius-md] px-3 py-2">
          {errorMsg}
        </p>
      )}

      <button
        type="submit"
        disabled={state === 'loading'}
        className="w-full py-2.5 px-4 rounded-[--radius-md] bg-bg-subtle text-text-primary font-semibold text-sm border border-border hover:border-accent-teal/40 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {state === 'loading' ? 'Submitting…' : 'Submit answers'}
      </button>
    </form>
  );
}
