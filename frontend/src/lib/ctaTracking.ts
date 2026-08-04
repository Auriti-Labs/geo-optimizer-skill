/**
 * ctaTracking.ts — Listener delegato per CTA marcate con data-attribute.
 *
 * Caricato una sola volta da Shell.astro, copre tutte le pagine statiche Astro
 * (pricing, home, early-access, …) senza dover idratare componenti React.
 *
 * Riusa gli helper di geo_track.ts: il consenso cookie, l'arricchimento con
 * referrer_type e i parametri UTM sono già gestiti da `track()`. Se gtag non è
 * caricato (consenso non dato) l'evento viene silenziosamente ignorato — quindi
 * il listener può essere attaccato sempre, anche prima del consenso.
 *
 * Convenzioni markup:
 *   - CTA di selezione piano  → <a data-plan-id data-plan-name data-plan-period
 *                                  data-plan-price data-plan-currency
 *                                  data-cta-location> → evento geo_plan_selected
 *   - CTA generica            → <a data-cta="<location>"> → evento geo_cta_clicked
 *   Un link è O un piano O una CTA generica: i due rami si escludono, niente doppio evento.
 */
import {
  track,
  trackPlanSelected,
  trackCtaClicked,
  trackSignupStarted,
  trackOnboardingStarted,
  trackReportClaimStarted,
  trackUpgradeIntent,
} from './geo_track';

const MANUAL_PREVIEW_FILE = 'geo-readiness-manual-preview.pdf';
const MANUAL_DOWNLOAD_ENDPOINT = '/public/download-manual';
const APP_HOST = 'app.geoready.dev';
const trackedManualPreviewLinks = new WeakSet<HTMLElement>();

type ManualRequestContext = {
  location: string;
  marketingConsent: boolean;
  submittedAt: number;
};

let pendingManualRequest: ManualRequestContext | null = null;

/** Estrae il valore numerico da una stringa prezzo ("$19" → "19", "Custom" → "custom"). */
function normalizePrice(raw: string | null): string {
  if (!raw) return '';
  const digits = raw.replace(/[^0-9]/g, '');
  return digits || raw.trim().toLowerCase();
}

/** Gestisce il click su una CTA di selezione piano. */
function handlePlanCta(link: HTMLElement): void {
  const planId = link.getAttribute('data-plan-id');
  const planName = link.getAttribute('data-plan-name');
  if (!planId || !planName) return;

  const currency = link.getAttribute('data-plan-currency') || 'USD';
  const priceStr = normalizePrice(link.getAttribute('data-plan-price'));
  // GA4 ecommerce requires a numeric value; skip begin_checkout for "custom"
  // (non-numeric) price strings like the Enterprise plan.
  const numericPrice = parseFloat(priceStr);

  // GA4 standard ecommerce event — fires before the custom geo_plan_selected
  // so the funnel step is captured in GA4 reporting. Uses the same consent-gated
  // pattern as track(): if gtag isn't loaded (consent not given), this is a no-op.
  if (typeof window !== 'undefined' && typeof window.gtag === 'function' && !isNaN(numericPrice)) {
    window.gtag('event', 'begin_checkout', {
      currency,
      value: numericPrice,
      items: [{ item_id: planId, item_name: planName, price: numericPrice, quantity: 1 }],
    });
  }

  trackPlanSelected({
    plan_id: planId,
    plan_name: planName,
    billing_period: link.getAttribute('data-plan-period') || 'one-time',
    price: priceStr,
    currency,
    cta_location: link.getAttribute('data-cta-location') || 'pricing_page',
  });
}

/** Gestisce il click su una CTA generica verso pricing/signup. */
function handleGenericCta(link: HTMLElement): void {
  const location = link.getAttribute('data-cta');
  if (!location) return;

  trackCtaClicked({
    cta_location: location,
    cta_text: (link.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80) || 'unknown',
  });
}

function linkText(link: HTMLElement): string {
  return (link.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80) || 'unknown';
}

function ctaLocation(link: HTMLElement): string {
  return (
    link.getAttribute('data-cta-location') ||
    link.getAttribute('data-cta') ||
    link.getAttribute('aria-label') ||
    'app_outbound'
  );
}

function appUrl(link: HTMLElement): URL | null {
  const href = link.getAttribute('href');
  if (!href) return null;
  try {
    const url = new URL(href, window.location.href);
    return url.hostname === APP_HOST ? url : null;
  } catch {
    return null;
  }
}

function planIdFor(link: HTMLElement, url: URL): string {
  return link.getAttribute('data-plan-id') || url.searchParams.get('plan') || '';
}

function planNameFor(link: HTMLElement, planId: string): string | undefined {
  return link.getAttribute('data-plan-name') || (planId ? planId.charAt(0).toUpperCase() + planId.slice(1) : undefined);
}

function appDestination(url: URL): 'signup' | 'login' | 'unknown' {
  if (url.pathname.startsWith('/signup')) return 'signup';
  if (url.pathname.startsWith('/login')) return 'login';
  return 'unknown';
}

function handleAppFunnelClick(link: HTMLElement): void {
  const url = appUrl(link);
  if (!url) return;

  const location = ctaLocation(link);
  const planId = planIdFor(link, url);
  const intent = url.searchParams.get('intent') || undefined;
  const onboarding = url.searchParams.get('onboarding') || undefined;
  const hasClaim = url.searchParams.has('claim');
  const destination = appDestination(url);

  if (destination === 'signup') {
    trackSignupStarted({
      plan_id: planId || undefined,
      intent,
      onboarding,
      claim_present: hasClaim,
      cta_location: location,
      cta_text: linkText(link),
    });
  }

  if (onboarding) {
    trackOnboardingStarted({
      onboarding,
      plan_id: planId || undefined,
      intent,
      cta_location: location,
      claim_present: hasClaim,
    });
  }

  if (hasClaim) {
    trackReportClaimStarted({
      claim_source: url.searchParams.get('claim_source') || 'unknown',
      destination,
      cta_location: location,
    });
  }

  if (planId && planId !== 'free') {
    trackUpgradeIntent({
      plan_id: planId,
      plan_name: planNameFor(link, planId),
      intent,
      cta_location: location,
      claim_present: hasClaim,
    });
  }

  if (url.pathname.startsWith('/pricing')) {
    track('geo_app_pricing_opened', {
      cta_location: location,
      cta_text: linkText(link),
    });
  }
}

function manualFormLocation(element: HTMLElement): string {
  const container = element.closest<HTMLElement>('.manual-download-form');
  return container?.id || 'manual_download_form';
}

function manualPreviewLocation(link: HTMLElement): string {
  if (link.closest('[data-hero-bleed]')) return 'manual_hero_preview';
  return 'manual_footer_preview';
}

function handleManualPreviewDownload(link: HTMLElement): void {
  if (trackedManualPreviewLinks.has(link)) return;
  trackedManualPreviewLinks.add(link);
  window.setTimeout(() => trackedManualPreviewLinks.delete(link), 2000);

  track('manual_preview_downloaded', {
    manual_location: manualPreviewLocation(link),
    asset: MANUAL_PREVIEW_FILE,
    format: 'pdf',
    pages: 27,
  });
}

function rememberManualRequest(form: HTMLFormElement): void {
  const container = form.closest<HTMLElement>('.manual-download-form');
  const consent = container?.querySelector<HTMLInputElement>('.manual-marketing-consent')?.checked ?? false;
  pendingManualRequest = {
    location: manualFormLocation(form),
    marketingConsent: consent,
    submittedAt: Date.now(),
  };
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

function requestMethod(input: RequestInfo | URL, init?: RequestInit): string {
  if (init?.method) return init.method;
  if (typeof Request !== 'undefined' && input instanceof Request) return input.method;
  return 'GET';
}

function isManualDownloadRequest(input: RequestInfo | URL, init?: RequestInit): boolean {
  return (
    requestMethod(input, init).toUpperCase() === 'POST' &&
    requestUrl(input).includes(MANUAL_DOWNLOAD_ENDPOINT)
  );
}

function recentManualRequest(): ManualRequestContext | null {
  if (!pendingManualRequest) return null;
  const ctx = pendingManualRequest;
  pendingManualRequest = null;
  return Date.now() - ctx.submittedAt <= 15000 ? ctx : null;
}

function initManualDownloadFetchTracking(): void {
  if (typeof window === 'undefined' || typeof window.fetch !== 'function') return;
  const state = window as unknown as { __geoManualFetchTracking?: boolean };
  if (state.__geoManualFetchTracking) return;
  state.__geoManualFetchTracking = true;

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const response = await originalFetch(input, init);
    if (response.ok && isManualDownloadRequest(input, init)) {
      const ctx = recentManualRequest();
      track('manual_pdf_requested', {
        manual_location: ctx?.location || 'manual_download_form',
        marketing_consent: ctx?.marketingConsent ?? false,
        delivery: 'email_link',
      });
    }
    return response;
  };
}

/** Attacca un singolo listener delegato per le CTA tracciate. Idempotente. */
export function initCtaTracking(): void {
  if (typeof document === 'undefined') return;
  if ((window as unknown as { __geoCtaTracking?: boolean }).__geoCtaTracking) return;
  (window as unknown as { __geoCtaTracking?: boolean }).__geoCtaTracking = true;

  initManualDownloadFetchTracking();

  document.addEventListener('pointerdown', (e) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;
    const previewLink = target.closest<HTMLElement>(`a[href$="${MANUAL_PREVIEW_FILE}"]`);
    if (previewLink) handleManualPreviewDownload(previewLink);
  });

  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;
    const previewLink = target.closest<HTMLElement>(`a[href$="${MANUAL_PREVIEW_FILE}"]`);
    if (previewLink) handleManualPreviewDownload(previewLink);

    const appLink = target.closest<HTMLElement>(`a[href*="${APP_HOST}"]`);
    if (appLink) handleAppFunnelClick(appLink);

    const link = target.closest<HTMLElement>('a[data-plan-id], a[data-cta]');
    if (!link) return;

    // Ramo piano prima: una CTA piano non riceve mai anche data-cta.
    if (link.hasAttribute('data-plan-id')) {
      handlePlanCta(link);
    } else {
      handleGenericCta(link);
    }
  });

  document.addEventListener('submit', (e) => {
    const form = e.target instanceof HTMLFormElement ? e.target : null;
    if (!form || !form.matches('.manual-form')) return;
    rememberManualRequest(form);
  }, true);
}
