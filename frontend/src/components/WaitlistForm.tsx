import { useState } from "react";
import { trackWaitlistJoined } from "../lib/geo_track";

type FormState = "idle" | "loading" | "success" | "error";

const USER_TYPE_OPTIONS = [
  { value: "developer", label: "Developer / Indie hacker" },
  { value: "seo-specialist", label: "SEO specialist / Consultant" },
  { value: "agency-consultant", label: "Agency / Freelance consultant" },
  { value: "saas-founder", label: "SaaS founder" },
  { value: "wordpress-professional", label: "WordPress professional" },
  { value: "other", label: "Other" },
];

const SITES_RANGE_OPTIONS = [
  { value: "1", label: "1 site" },
  { value: "2-5", label: "2–5 sites" },
  { value: "6-15", label: "6–15 sites" },
  { value: "16-50", label: "16–50 sites" },
  { value: "50-plus", label: "50+ sites" },
];

const MAIN_INTEREST_OPTIONS = [
  { value: "ai-search-monitoring", label: "AI search monitoring (weekly alerts)" },
  { value: "full-geo-reports", label: "Full 8-category GEO reports" },
  { value: "audit-history", label: "Audit history and score trends" },
  { value: "pdf-reports", label: "PDF report export" },
  { value: "agency-reporting", label: "Agency / white-label reporting" },
  { value: "api-access", label: "API access for integrations" },
  { value: "wordpress-integration", label: "WordPress plugin integration" },
];

const ENDPOINT =
  (import.meta as unknown as { env: Record<string, string> }).env
    .PUBLIC_WAITLIST_ENDPOINT ?? "https://app.geoready.dev/api/waitlist";

export default function WaitlistForm() {
  const [state, setState] = useState<FormState>("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setState("loading");

    const form = e.currentTarget;
    const data = new FormData(form);

    const payload = {
      email: data.get("email") as string,
      user_type: data.get("user_type") as string,
      managed_sites_range: data.get("managed_sites_range") as string,
      main_interest: data.get("main_interest") as string,
      consent: data.get("consent") === "on",
      honeypot: data.get("website") as string,
    };

    try {
      const res = await fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = err?.detail?.[0]?.msg ?? err?.detail ?? "Something went wrong. Please try again.";
        setState("error");
        setMessage(typeof detail === "string" ? detail : "Something went wrong. Please try again.");
        return;
      }

      const json = await res.json();
      setState("success");
      setMessage(json.message ?? "You're on the list.");
      trackWaitlistJoined({
        user_type: payload.user_type,
        managed_sites_range: payload.managed_sites_range,
        main_interest: payload.main_interest,
      });
    } catch {
      setState("error");
      setMessage("Could not reach the server. Check your connection and try again.");
    }
  }

  if (state === "success") {
    return (
      <div className="rounded-[--radius-lg] border border-border bg-bg-surface p-6 text-center">
        <div className="w-10 h-10 rounded-full bg-accent-success/10 flex items-center justify-center mx-auto mb-4">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-success">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <p className="text-base font-semibold text-text-primary">{message}</p>
        <p className="mt-2 text-sm text-text-secondary">
          We'll reach out by email when early access opens. No spam, no newsletters.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {/* Honeypot — invisible to humans, ignored by screen readers */}
      <div
        style={{
          position: "absolute",
          left: "-9999px",
          width: "1px",
          height: "1px",
          overflow: "hidden",
        }}
        aria-hidden="true"
      >
        <label htmlFor="website">Website</label>
        <input
          id="website"
          name="website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          defaultValue=""
        />
      </div>

      <div>
        <label htmlFor="wl-email" className="block text-sm font-medium text-text-primary mb-1.5">
          Email <span className="text-accent-danger">*</span>
        </label>
        <input
          id="wl-email"
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
          className="w-full px-3 py-2 rounded-[--radius-md] border border-border bg-bg-surface text-text-primary text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors"
        />
      </div>

      <div>
        <label htmlFor="wl-user-type" className="block text-sm font-medium text-text-primary mb-1.5">
          What best describes you? <span className="text-accent-danger">*</span>
        </label>
        <select
          id="wl-user-type"
          name="user_type"
          required
          className="w-full px-3 py-2 rounded-[--radius-md] border border-border bg-bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors"
        >
          <option value="">Select…</option>
          {USER_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="wl-sites" className="block text-sm font-medium text-text-primary mb-1.5">
          How many sites do you manage? <span className="text-accent-danger">*</span>
        </label>
        <select
          id="wl-sites"
          name="managed_sites_range"
          required
          className="w-full px-3 py-2 rounded-[--radius-md] border border-border bg-bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors"
        >
          <option value="">Select…</option>
          {SITES_RANGE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="wl-interest" className="block text-sm font-medium text-text-primary mb-1.5">
          What's your main interest in GeoReady Pro? <span className="text-accent-danger">*</span>
        </label>
        <select
          id="wl-interest"
          name="main_interest"
          required
          className="w-full px-3 py-2 rounded-[--radius-md] border border-border bg-bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-accent-teal/40 focus:border-accent-teal transition-colors"
        >
          <option value="">Select…</option>
          {MAIN_INTEREST_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div className="flex items-start gap-3 pt-1">
        <input
          id="wl-consent"
          name="consent"
          type="checkbox"
          required
          className="mt-0.5 h-4 w-4 rounded border-border text-accent-teal focus:ring-accent-teal/40 cursor-pointer"
        />
        <label htmlFor="wl-consent" className="text-sm text-text-secondary leading-relaxed cursor-pointer">
          I agree to be contacted about GeoReady early access. See our{" "}
          <a href="/privacy/" className="text-accent-teal hover:underline">
            Privacy Policy
          </a>
          . No newsletters, no spam.
        </label>
      </div>

      {state === "error" && (
        <p role="alert" className="text-sm text-accent-danger bg-accent-danger/5 border border-accent-danger/20 rounded-[--radius-md] px-3 py-2">
          {message}
        </p>
      )}

      <button
        type="submit"
        disabled={state === "loading"}
        className="w-full py-2.5 px-4 rounded-[--radius-md] bg-accent-teal text-white font-semibold text-sm hover:bg-accent-teal-dark transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {state === "loading" ? "Joining…" : "Join early access"}
      </button>
    </form>
  );
}
