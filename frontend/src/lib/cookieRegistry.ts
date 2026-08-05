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

// Bumped from v1.0 when Google Analytics 4 went live: the previous inventory
// declared analytics as "not currently used", so a consent choice recorded
// against it was made on inaccurate information and cannot be carried over.
// Changing this string invalidates every stored choice and re-prompts everyone.
export const CONSENT_VERSION = 'v2.0';

export const cookieRegistry: CookieEntry[] = [
  {
    name: 'geo_cookie_consent',
    provider: 'GeoReady',
    domain: 'geoready.dev',
    category: 'necessary',
    purpose:
      'Stores your cookie and privacy choices so you are not asked again on every visit, and so the choice can be honoured before any non-essential script loads.',
    legalBasis:
      'Technical necessity — recording a consent choice is required to demonstrate compliance (GDPR art. 7(1)) and is exempt from consent under the ePrivacy Directive',
    duration: '6 months, or until the consent version changes',
    type: 'localStorage',
    firstOrThirdParty: 'first',
    isEssential: true,
    isCurrentlyUsed: true,
    service: 'GeoReady Consent Manager',
    notes:
      'Stays on your device — never sent to a server. Contains only the four category flags, a timestamp and a version string.',
  },
  {
    name: '_ga',
    provider: 'Google Ireland Limited / Google LLC',
    domain: 'geoready.dev',
    category: 'analytics',
    purpose:
      'Distinguishes one visitor from another so aggregate traffic statistics can be produced (visits, pages, referrers).',
    legalBasis: 'Consent (GDPR art. 6(1)(a) and ePrivacy Directive art. 5(3))',
    duration: '2 years',
    type: 'cookie',
    firstOrThirdParty: 'third',
    isEssential: false,
    isCurrentlyUsed: true,
    service: 'Google Analytics 4',
    dataShared:
      'Pseudonymous identifier, pages viewed, referrer, approximate location derived from a truncated IP address, device and browser type',
    privacyPolicyUrl: 'https://policies.google.com/privacy',
    notes:
      'Set only after you accept analytics. Google Signals and advertising features are off, IP addresses are truncated before storage and are not retained for EU visitors.',
  },
  {
    name: '_ga_<container-id>',
    provider: 'Google Ireland Limited / Google LLC',
    domain: 'geoready.dev',
    category: 'analytics',
    purpose: 'Keeps session state for the specific GA4 property (session start, session number).',
    legalBasis: 'Consent (GDPR art. 6(1)(a) and ePrivacy Directive art. 5(3))',
    duration: '2 years',
    type: 'cookie',
    firstOrThirdParty: 'third',
    isEssential: false,
    isCurrentlyUsed: true,
    service: 'Google Analytics 4',
    dataShared: 'Pseudonymous session identifier and session counters',
    privacyPolicyUrl: 'https://policies.google.com/privacy',
    notes: 'Set only after you accept analytics.',
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
      'Essential for the site to work. Cannot be disabled. Covers storing your privacy choice itself and basic security measures.',
    preferences:
      'Remember settings and choices you make (such as layout or display options) so they persist between visits.',
    analytics:
      'Let us measure how the site is used — which pages are read, which are ignored — through Google Analytics 4. Off unless you accept.',
    marketing:
      'Would be used to measure advertising campaigns and personalise ads. No marketing cookie or tracker is currently set on this site.',
  };
  return descriptions[cat];
}
