import { CONSENT_VERSION, cookieRegistry, type CookieCategory } from './cookieRegistry';

export interface ConsentState {
  necessary: true;
  preferences: boolean;
  analytics: boolean;
  marketing: boolean;
  timestamp: string;
  version: string;
}

const STORAGE_KEY = 'geo_cookie_consent';
const GA_MEASUREMENT_ID = import.meta.env.PUBLIC_GA_MEASUREMENT_ID;

/**
 * Dispatched on the window every time the stored consent changes, and once on
 * page load for an already-recorded choice.
 *
 * Exists so that trackers which are not Google Analytics — PostHog on the app
 * domain — can be gated by this same module without it having to import them.
 * Keeping the dependency one-way lets both domains run a byte-identical copy of
 * this file instead of two drifting variants.
 */
export const CONSENT_EVENT = 'geo:consentchange';

const defaultConsent: ConsentState = {
  necessary: true,
  preferences: false,
  analytics: false,
  marketing: false,
  timestamp: '',
  version: CONSENT_VERSION,
};

/** Legge il consenso salvato in localStorage. Ritorna null se non esiste o se la versione e cambiata. */
export function loadConsent(): ConsentState | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ConsentState;
    if (parsed.version !== CONSENT_VERSION) return null;
    return parsed;
  } catch {
    return null;
  }
}

/** Salva il consenso in localStorage e notifica i tracker in ascolto. */
export function saveConsent(consent: Omit<ConsentState, 'timestamp' | 'version'>): void {
  if (typeof window === 'undefined') return;
  const full: ConsentState = {
    ...consent,
    timestamp: new Date().toISOString(),
    version: CONSENT_VERSION,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(full));
  updateConsentMode(full);
  announceConsent(full);
}

/** Ritorna il consenso corrente o il default. */
export function getConsent(): ConsentState {
  return loadConsent() || { ...defaultConsent };
}

/** Verifica se il consenso e stato gia dato. */
export function hasConsented(): boolean {
  if (typeof window === 'undefined') return false;
  const c = loadConsent();
  return c !== null && c.version === CONSENT_VERSION;
}

/** Rifiuta tutte le categorie non necessarie. */
export function rejectAll(): void {
  saveConsent({
    necessary: true,
    preferences: false,
    analytics: false,
    marketing: false,
  });
  removeAnalyticsCookies();
}

/** Accetta tutte le categorie. */
export function acceptAll(): void {
  saveConsent({
    necessary: true,
    preferences: true,
    analytics: true,
    marketing: true,
  });
  loadAnalyticsScript();
}

/** Salva consenso personalizzato. */
export function saveCustomConsent(categories: {
  preferences: boolean;
  analytics: boolean;
  marketing: boolean;
}): void {
  saveConsent({
    necessary: true,
    preferences: categories.preferences,
    analytics: categories.analytics,
    marketing: categories.marketing,
  });
  if (categories.analytics) {
    loadAnalyticsScript();
  } else {
    removeAnalyticsCookies();
  }
}

/** Revoca una categoria specifica. */
export function revokeCategory(category: CookieCategory): void {
  const current = getConsent();
  if (category === 'necessary') return;
  current[category] = false;
  saveConsent({
    necessary: true,
    preferences: current.preferences,
    analytics: current.analytics,
    marketing: current.marketing,
  });
  if (category === 'analytics') {
    removeAnalyticsCookies();
  }
}

/** Notify non-Google trackers of the current consent state. */
function announceConsent(consent: ConsentState): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent<ConsentState>(CONSENT_EVENT, { detail: consent }));
}

// ─── Google Consent Mode v2 ───────────────────────────────────────────────────

/**
 * Queue a gtag command on dataLayer.
 *
 * Deliberately uses the canonical `function(){dataLayer.push(arguments)}` shim
 * rather than pushing an array: gtag.js reads each queued entry as an
 * `arguments` object, and a plain array is not guaranteed to be interpreted as
 * a command. For consent defaults a silently ignored command is the worst
 * possible failure — the tag would run as if consent had never been declared.
 */
const gtag = function (): void {
  const w = window as any;
  w.dataLayer = w.dataLayer || [];
  w.dataLayer.push(arguments);
} as (...args: unknown[]) => void;

/**
 * Declare every consent type as denied, before any Google tag can load.
 *
 * Must run on every page load, including pages that will never load gtag.js:
 * Consent Mode is order-dependent — a `default` command arriving after gtag.js
 * has initialised is ignored, and the tag would then behave as if consent had
 * never been declared. This costs no network request, it only seeds dataLayer.
 *
 * `ad_user_data` and `ad_personalization` are the two types Google added in
 * Consent Mode v2 and requires for EU/EEA/UK/CH conversion measurement; they
 * are declared here even though no advertising tag is currently installed, so
 * that adding one later cannot silently start from an undeclared state.
 */
export function initConsentMode(): void {
  if (typeof window === 'undefined') return;
  const w = window as any;
  if (w.__geoConsentModeReady) return;
  w.__geoConsentModeReady = true;

  gtag('consent', 'default', {
    ad_storage: 'denied',
    analytics_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
    // Give an async banner a moment to restore a stored choice before the tag
    // decides how to behave, so a returning visitor who already accepted is
    // not measured cookielessly for the first few hundred milliseconds.
    wait_for_update: 500,
  });

  const stored = loadConsent();
  if (stored) {
    updateConsentMode(stored);
    announceConsent(stored);
  }
}

/** Report the visitor's choice to Google. */
export function updateConsentMode(consent: ConsentState): void {
  if (typeof window === 'undefined') return;
  gtag('consent', 'update', {
    analytics_storage: consent.analytics ? 'granted' : 'denied',
    ad_storage: consent.marketing ? 'granted' : 'denied',
    ad_user_data: consent.marketing ? 'granted' : 'denied',
    ad_personalization: consent.marketing ? 'granted' : 'denied',
  });
}

/** Carica lo script analytics se consentito e configurato. */
export function loadAnalyticsScript(): void {
  if (typeof window === 'undefined') return;
  if (!GA_MEASUREMENT_ID) return;
  const consent = getConsent();
  if (!consent.analytics) return;
  if (document.getElementById('ga-script')) return;

  // Defaults first: injecting the tag before the `consent default` command has
  // been queued would let it initialise with consent undeclared.
  initConsentMode();
  updateConsentMode(consent);

  const script = document.createElement('script');
  script.id = 'ga-script';
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  document.head.appendChild(script);

  const inline = document.createElement('script');
  inline.id = 'ga-config';
  inline.textContent = `
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', '${GA_MEASUREMENT_ID}', {
      'linker': { 'domains': ['geoready.dev', 'app.geoready.dev'], 'decorate_forms': true }
    });
  `;
  document.head.appendChild(inline);
}

/** Rimuove i cookie analytics noti. */
export function removeAnalyticsCookies(): void {
  if (typeof document === 'undefined') return;
  const domains = [window.location.hostname, `.${window.location.hostname}`];
  const analyticsCookies = cookieRegistry
    .filter((c) => c.category === 'analytics' && c.type === 'cookie')
    .map((c) => c.name);

  // Registry names carry a `<placeholder>` where the provider substitutes a
  // property or project id at runtime (`_ga_<container-id>`,
  // `ph_<project-token>_posthog`), so the literal name never matches a real
  // cookie. Expand those into the prefix before the placeholder and sweep every
  // cookie that starts with it — all first-party, all ours.
  const exact: string[] = [];
  const prefixes: string[] = [];
  for (const name of analyticsCookies) {
    const placeholder = name.indexOf('<');
    if (placeholder === -1) exact.push(name);
    else prefixes.push(name.slice(0, placeholder));
  }
  for (const entry of document.cookie.split(';')) {
    const cookieName = entry.split('=')[0]?.trim();
    if (!cookieName) continue;
    if (prefixes.some((p) => cookieName.startsWith(p))) exact.push(cookieName);
  }

  for (const cookieName of new Set(exact)) {
    for (const domain of domains) {
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${domain}`;
    }
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;
  }

  // Drop any localStorage an analytics provider left behind (PostHog persists
  // its distinct id there as well as in a cookie).
  const analyticsStorageKeys = cookieRegistry
    .filter((c) => c.category === 'analytics' && c.type === 'localStorage')
    .map((c) => c.name);
  try {
    for (const key of Object.keys(localStorage)) {
      const matches = analyticsStorageKeys.some((n) => {
        const placeholder = n.indexOf('<');
        return placeholder === -1 ? key === n : key.startsWith(n.slice(0, placeholder));
      });
      if (matches) localStorage.removeItem(key);
    }
  } catch {
    // localStorage can throw in private-browsing modes; nothing to clean then.
  }

  // Drop anything the tag queued, then immediately re-declare the consent
  // defaults. Clearing dataLayer also discards the `consent default` command
  // that must precede gtag.js: without re-seeding, a visitor who rejects and
  // later accepts would load the tag with consent undeclared, since
  // initConsentMode() short-circuits on its own guard.
  const w = window as any;
  if (w.dataLayer) {
    w.dataLayer = [];
    w.__geoConsentModeReady = false;
    initConsentMode();
  }
}
