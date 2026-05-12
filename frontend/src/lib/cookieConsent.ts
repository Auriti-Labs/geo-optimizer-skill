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

/** Salva il consenso in localStorage. */
export function saveConsent(consent: Omit<ConsentState, 'timestamp' | 'version'>): void {
  if (typeof window === 'undefined') return;
  const full: ConsentState = {
    ...consent,
    timestamp: new Date().toISOString(),
    version: CONSENT_VERSION,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(full));
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

/** Carica lo script analytics se consentito e configurato. */
export function loadAnalyticsScript(): void {
  if (typeof window === 'undefined') return;
  if (!GA_MEASUREMENT_ID) return;
  const consent = getConsent();
  if (!consent.analytics) return;
  if (document.getElementById('ga-script')) return;

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
    gtag('config', '${GA_MEASUREMENT_ID}');
  `;
  document.head.appendChild(inline);
}

/** Rimuove i cookie analytics noti. */
export function removeAnalyticsCookies(): void {
  if (typeof document === 'undefined') return;
  const domains = [window.location.hostname, `.${window.location.hostname}`];
  const analyticsCookies = cookieRegistry
    .filter((c) => c.category === 'analytics')
    .map((c) => c.name);

  for (const cookieName of analyticsCookies) {
    for (const domain of domains) {
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${domain}`;
    }
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`;
  }

  // Pulisce anche dataLayer se presente
  if ((window as any).dataLayer) {
    (window as any).dataLayer = [];
  }
}
