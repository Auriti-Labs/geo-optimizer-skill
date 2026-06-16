/**
 * geo_track.ts — Utility eventi GA4 per GeoReady.dev
 * Rispetta il consenso cookie: se gtag non è caricato l'evento viene silenziosamente ignorato.
 * Prefisso eventi: `geo_` (coerente con backend telemetry).
 */

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

function gtagReady(): boolean {
  return typeof window !== 'undefined' && typeof window.gtag === 'function';
}

/** Estrae i parametri UTM dall'URL corrente. */
export function getUtmParams(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const search = new URLSearchParams(window.location.search);
  const result: Record<string, string> = {};
  for (const key of ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']) {
    const val = search.get(key);
    if (val) result[key] = val;
  }
  return result;
}

/** Ritorna il referrer semplificato ('organic', 'direct', 'github', ecc.). */
function referrerType(): string {
  if (typeof document === 'undefined') return 'unknown';
  const ref = document.referrer;
  if (!ref) return 'direct';
  if (ref.includes('github.com')) return 'github';
  if (ref.includes('google.')) return 'google';
  if (ref.includes('twitter.com') || ref.includes('t.co')) return 'twitter';
  if (ref.includes('linkedin.com')) return 'linkedin';
  if (ref.includes('news.ycombinator.com')) return 'hackernews';
  if (ref.includes('producthunt.com')) return 'producthunt';
  return 'referral';
}

export interface TrackParams {
  [key: string]: string | number | boolean | undefined;
}

/** Invia un evento GA4. Silenzioso se gtag non è disponibile (consenso non dato). */
export function track(eventName: string, params: TrackParams = {}): void {
  if (!gtagReady()) return;
  window.gtag!('event', eventName, {
    referrer_type: referrerType(),
    ...getUtmParams(),
    ...params,
  });
}

// ── Shorthand per gli eventi pre-launch ──────────────────────────────────────

/** Utente ha avviato un audit (submit URL). */
export function trackAuditStarted(): void {
  track('geo_audit_started');
}

/** Audit completato con score visibile. */
export function trackAuditCompleted(params: {
  score: number;
  score_band: string;
}): void {
  track('geo_audit_completed', params);
}

/** Iscrizione waitlist/early-access completata con successo. */
export function trackWaitlistJoined(params: {
  user_type: string;
  managed_sites_range: string;
  main_interest: string;
}): void {
  track('geo_waitlist_joined', params);
}

/** Form waitlist entrato nel viewport — copre lo step "ha visto ma non ha iniziato". */
export function trackWaitlistViewed(): void {
  track('geo_waitlist_viewed');
}

/** Utente inizia a compilare il form waitlist (primo focus/change su un campo). */
export function trackWaitlistStarted(): void {
  track('geo_waitlist_started');
}

/** Iscrizione waitlist fallita. `reason` è una causa anonima (validation/server/network),
 *  mai dati personali. `status` è il codice HTTP quando disponibile. */
export function trackWaitlistFailed(params: {
  reason: 'validation' | 'server' | 'network';
  status?: number;
}): void {
  track('geo_waitlist_failed', params);
}

/** Click su CTA significativo (hero, pricing, early-access). */
export function trackCtaClicked(params: {
  cta_location: string;
  cta_text: string;
}): void {
  track('geo_cta_clicked', params);
}

/** Gate visuale mostrato — categorie locked dopo il free report. */
export function trackGateTriggered(params: {
  score: number;
  locked_categories: number;
}): void {
  track('geo_gate_triggered', params);
}

/** Utente inizia a compilare il survey WTP. */
export function trackSurveyStarted(): void {
  track('geo_survey_started');
}

/** Survey WTP completato con successo. */
export function trackSurveyCompleted(params: {
  wtp: string;
  main_problem: string;
}): void {
  track('geo_survey_completed', params);
}

/** Piano selezionato — clic su una CTA di un piano (pricing, home, report). */
export function trackPlanSelected(params: {
  plan_id: string;
  plan_name: string;
  billing_period: string;
  price: string;
  currency: string;
  cta_location: string;
}): void {
  track('geo_plan_selected', params);
}

// ── Shorthand generatore llms.txt (Sprint 3) ─────────────────────────────────

/** Generatore llms.txt avviato — submit del form con/senza sitemap custom. */
export function trackLlmsGeneratorStarted(params: {
  has_custom_sitemap: boolean;
  max_per_section: number;
}): void {
  track('geo_llms_generator_started', params);
}

/** Generazione llms.txt completata con successo — esito e metriche del contenuto. */
export function trackLlmsGeneratorCompleted(params: {
  found_sitemap: boolean;
  url_count: number;
  line_count: number;
  size_bytes: number;
  max_per_section: number;
}): void {
  track('geo_llms_generator_completed', params);
}

/** Generazione llms.txt fallita — errore backend o di rete. */
export function trackLlmsGeneratorFailed(params: {
  has_custom_sitemap: boolean;
}): void {
  track('geo_llms_generator_failed', params);
}

/** Contenuto llms.txt copiato negli appunti. */
export function trackLlmsTxtCopied(): void {
  track('geo_llms_txt_copied');
}

/** File llms.txt scaricato — riporta la dimensione del file. */
export function trackLlmsTxtDownloaded(params: { size_bytes: number }): void {
  track('geo_llms_txt_downloaded', params);
}
