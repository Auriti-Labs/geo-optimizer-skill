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
import { trackPlanSelected, trackCtaClicked } from './geo_track';

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

  trackPlanSelected({
    plan_id: planId,
    plan_name: planName,
    billing_period: link.getAttribute('data-plan-period') || 'one-time',
    price: normalizePrice(link.getAttribute('data-plan-price')),
    currency: link.getAttribute('data-plan-currency') || 'USD',
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

/** Attacca un singolo listener delegato per le CTA tracciate. Idempotente. */
export function initCtaTracking(): void {
  if (typeof document === 'undefined') return;
  if ((window as unknown as { __geoCtaTracking?: boolean }).__geoCtaTracking) return;
  (window as unknown as { __geoCtaTracking?: boolean }).__geoCtaTracking = true;

  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement | null;
    if (!target) return;
    const link = target.closest<HTMLElement>('a[data-plan-id], a[data-cta]');
    if (!link) return;

    // Ramo piano prima: una CTA piano non riceve mai anche data-cta.
    if (link.hasAttribute('data-plan-id')) {
      handlePlanCta(link);
    } else {
      handleGenericCta(link);
    }
  });
}
