export type CookieType = 'cookie' | 'localStorage' | 'sessionStorage' | 'external-request';
export type CookieCategory = 'necessary' | 'preferences' | 'analytics' | 'marketing';

export interface CookieEntry {
  name: string;
  provider: string;
  domain: string;
  category: CookieCategory;
  purpose: string;
  legalBasis: string;
  duration: string;
  type: CookieType;
  firstOrThirdParty: 'first' | 'third';
  isEssential: boolean;
  isCurrentlyUsed: boolean;
  service: string;
  dataShared?: string;
  privacyPolicyUrl?: string;
  notes?: string;
}

export const CONSENT_VERSION = 'v1.0';

export const cookieRegistry: CookieEntry[] = [
  {
    name: 'geo_cookie_consent',
    provider: 'GeoReady',
    domain: 'geoready.dev',
    category: 'necessary',
    purpose: 'Memorizza le preferenze cookie/privacy dell\'utente per evitare di richiedere il consenso ad ogni visita.',
    legalBasis: 'Interesse legittimo / necessita tecnica per memorizzare una scelta privacy',
    duration: '6 mesi o fino a cambio versione policy',
    type: 'localStorage',
    firstOrThirdParty: 'first',
    isEssential: true,
    isCurrentlyUsed: true,
    service: 'GeoReady Consent Manager',
    notes: 'Storage locale usato per persistere la scelta privacy. Nessun dato personale raccolto.',
  },
  {
    name: '_ga',
    provider: 'Google LLC',
    domain: 'geoready.dev',
    category: 'analytics',
    purpose: 'Distinguere gli utenti unici e generare statistiche aggregate sul traffico.',
    legalBasis: 'Consenso',
    duration: '2 anni',
    type: 'cookie',
    firstOrThirdParty: 'third',
    isEssential: false,
    isCurrentlyUsed: false,
    service: 'Google Analytics 4',
    dataShared: 'Dati di navigazione aggregati',
    privacyPolicyUrl: 'https://policies.google.com/privacy',
    notes: 'Caricato solo se PUBLIC_GA_MEASUREMENT_ID e esplicito consenso analytics. Al momento non attivo.',
  },
  {
    name: '_ga_<container-id>',
    provider: 'Google LLC',
    domain: 'geoready.dev',
    category: 'analytics',
    purpose: 'Persistenza della sessione all\'interno del container GA4.',
    legalBasis: 'Consenso',
    duration: '2 anni',
    type: 'cookie',
    firstOrThirdParty: 'third',
    isEssential: false,
    isCurrentlyUsed: false,
    service: 'Google Analytics 4',
    dataShared: 'Dati di navigazione aggregati',
    privacyPolicyUrl: 'https://policies.google.com/privacy',
    notes: 'Caricato solo se PUBLIC_GA_MEASUREMENT_ID e esplicito consenso analytics. Al momento non attivo.',
  },
];

export function getCookiesByCategory(category: CookieCategory): CookieEntry[] {
  return cookieRegistry.filter((c) => c.category === category);
}

export function getCurrentlyUsedCookies(): CookieEntry[] {
  return cookieRegistry.filter((c) => c.isCurrentlyUsed);
}

export function getCategories(): CookieCategory[] {
  return ['necessary', 'preferences', 'analytics', 'marketing'];
}

export function getCategoryLabel(cat: CookieCategory): string {
  const labels: Record<CookieCategory, string> = {
    necessary: 'Necessary',
    preferences: 'Preferences',
    analytics: 'Analytics',
    marketing: 'Marketing',
  };
  return labels[cat];
}

export function getCategoryDescription(cat: CookieCategory): string {
  const descriptions: Record<CookieCategory, string> = {
    necessary:
      'Essential for the site to function. Cannot be disabled. Includes consent storage and security measures.',
    preferences:
      'Remember your settings and choices (language, layout, etc.) to improve the experience.',
    analytics:
      'Help us understand how visitors interact with the site by collecting anonymous statistical data.',
    marketing:
      'Used to deliver personalized advertisements and measure campaign performance. Currently not used.',
  };
  return descriptions[cat];
}
