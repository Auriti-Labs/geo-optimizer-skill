import { useEffect, useRef, useState } from "react";
import {
  trackWaitlistJoined,
  trackWaitlistViewed,
  trackWaitlistStarted,
  trackWaitlistFailed,
} from "../lib/geo_track";

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
  { value: "full-geo-reports", label: "Full nine-category GEO reports" },
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
  const startedRef = useRef(false);
  const formRef = useRef<HTMLFormElement>(null);

  // Form entrato nel viewport — copre lo step "ha visto ma non ha iniziato".
  useEffect(() => {
    const el = formRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          trackWaitlistViewed();
          io.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  // Primo focus/change su un campo — sparato una sola volta per sessione di form.
  function handleFirstInteraction() {
    if (!startedRef.current) {
      startedRef.current = true;
      trackWaitlistStarted();
    }
  }

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
        // Causa anonima: 4xx = validazione, 5xx = errore server. Nessun dato personale.
        trackWaitlistFailed({
          reason: res.status >= 500 ? "server" : "validation",
          status: res.status,
        });
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
      trackWaitlistFailed({ reason: "network" });
    }
  }

  if (state === "success") {
    return (
      <div className="rounded-[10px] border border-rail bg-raised p-6 text-center">
        <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-pass-wash">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-pass-deep">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <p className="text-base font-semibold text-ink">{message}</p>
        <p className="mt-2 text-sm text-ink-soft">
          We'll email you about new features and GEO research. No spam.
        </p>
      </div>
    );
  }

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      onFocusCapture={handleFirstInteraction}
      onChange={handleFirstInteraction}
      noValidate
      className="space-y-5"
    >
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
        <label htmlFor="wl-email" className="mb-1.5 block text-sm font-medium text-ink">
          Email <span className="text-fail">*</span>
        </label>
        <input
          id="wl-email"
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
          className="w-full rounded-[10px] border border-ink/25 bg-raised px-3 py-2.5 text-sm text-ink placeholder:text-ink-mute transition-shadow focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30"
        />
      </div>

      <div>
        <label htmlFor="wl-user-type" className="mb-1.5 block text-sm font-medium text-ink">
          What best describes you? <span className="text-fail">*</span>
        </label>
        <select
          id="wl-user-type"
          name="user_type"
          required
          className="w-full rounded-[10px] border border-ink/25 bg-raised px-3 py-2.5 text-sm text-ink transition-shadow focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30"
        >
          <option value="">Select…</option>
          {USER_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="wl-sites" className="mb-1.5 block text-sm font-medium text-ink">
          How many sites do you manage? <span className="text-fail">*</span>
        </label>
        <select
          id="wl-sites"
          name="managed_sites_range"
          required
          className="w-full rounded-[10px] border border-ink/25 bg-raised px-3 py-2.5 text-sm text-ink transition-shadow focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30"
        >
          <option value="">Select…</option>
          {SITES_RANGE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="wl-interest" className="mb-1.5 block text-sm font-medium text-ink">
          What's your main interest in GeoReady Pro? <span className="text-fail">*</span>
        </label>
        <select
          id="wl-interest"
          name="main_interest"
          required
          className="w-full rounded-[10px] border border-ink/25 bg-raised px-3 py-2.5 text-sm text-ink transition-shadow focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30"
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
          className="mt-0.5 h-4 w-4 cursor-pointer rounded-[6px] border-ink/25 text-pass-deep focus:ring-pass/30"
        />
        <label htmlFor="wl-consent" className="cursor-pointer text-sm leading-relaxed text-ink-soft">
          I agree to receive product updates about GeoReady. See our{" "}
          <a href="/privacy/" className="text-pass-deep underline decoration-rail underline-offset-2 hover:decoration-pass-deep">
            Privacy Policy
          </a>
          . No newsletters, no spam.
        </label>
      </div>

      {state === "error" && (
        <div role="alert" className="flex items-start gap-3 rounded-[10px] border border-fail/30 bg-fail-wash px-4 py-3 text-sm text-fail">
          <span aria-hidden="true" className="mt-0.5 font-text text-[12.5px] font-semibold">
            err
          </span>
          <span>{message}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={state === "loading"}
        className="w-full rounded-[10px] bg-pass-deep px-4 py-3 font-text text-[13px] font-semibold text-on-accent transition-colors hover:bg-pass disabled:cursor-not-allowed disabled:opacity-60"
      >
        {state === "loading" ? "Subscribing…" : "Get product updates"}
      </button>
    </form>
  );
}
