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
// v3.0: Microsoft Clarity (session recordings and heatmaps) joined the analytics
// category. A choice recorded under v2.0 covered Google Analytics only.
export const CONSENT_VERSION = 'v3.0';

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
  {
    name: '_clck',
    provider: 'Microsoft Corporation',
    domain: 'geoready.dev',
    category: 'analytics',
    purpose: 'Keeps the Clarity user id and preferences, so one browser is recognised as the same user on this site.',
    legalBasis: 'Consent (GDPR art. 6(1)(a) and ePrivacy Directive art. 5(3))',
    duration: 'Not stated by Microsoft (cookie list read on 26 October 2026)',
    type: 'cookie',
    firstOrThirdParty: 'first',
    isEssential: false,
    isCurrentlyUsed: true,
    service: 'Microsoft Clarity',
    dataShared: 'Pseudonymous Clarity user id',
    privacyPolicyUrl: 'https://privacy.microsoft.com/privacystatement',
    notes: 'Set only after you accept analytics. Microsoft Clarity records how pages are used (clicks, scrolling, page movement) as session recordings and heatmaps.',
  },
  {
    name: '_clsk',
    provider: 'Microsoft Corporation',
    domain: 'geoready.dev',
    category: 'analytics',
    purpose: 'Joins several page views into a single Clarity session recording.',
    legalBasis: 'Consent (GDPR art. 6(1)(a) and ePrivacy Directive art. 5(3))',
    duration: 'Not stated by Microsoft (cookie list read on 26 October 2026)',
    type: 'cookie',
    firstOrThirdParty: 'first',
    isEssential: false,
    isCurrentlyUsed: true,
    service: 'Microsoft Clarity',
    dataShared: 'Pseudonymous session id',
    privacyPolicyUrl: 'https://privacy.microsoft.com/privacystatement',
    notes: 'Set only after you accept analytics.',
  },
  {
    name: 'CLID',
    provider: 'Microsoft Corporation',
    domain: 'clarity.ms',
    category: 'analytics',
    purpose: 'Identifies the first time Clarity saw this browser on any site that uses Clarity.',
    legalBasis: 'Consent (GDPR art. 6(1)(a) and ePrivacy Directive art. 5(3))',
    duration: 'Not stated by Microsoft (cookie list read on 26 October 2026)',
    type: 'cookie',
    firstOrThirdParty: 'third',
    isEssential: false,
    isCurrentlyUsed: true,
    service: 'Microsoft Clarity',
    dataShared: 'Pseudonymous browser identifier',
    privacyPolicyUrl: 'https://privacy.microsoft.com/privacystatement',
    notes: 'Set by clarity.ms, only after you accept analytics.',
  },
  {
    name: 'ANONCHK',
    provider: 'Microsoft Corporation',
    domain: 'clarity.ms',
    category: 'analytics',
    purpose: 'Records whether MUID is transferred to an advertising cookie. Clarity does not use that cookie, so the value is always 0.',
    legalBasis: 'Consent (GDPR art. 6(1)(a) and ePrivacy Directive art. 5(3))',
    duration: 'Not stated by Microsoft (cookie list read on 26 October 2026)',
    type: 'cookie',
    firstOrThirdParty: 'third',
    isEssential: false,
    isCurrentlyUsed: true,
    service: 'Microsoft Clarity',
    dataShared: 'A fixed flag, always 0',
    privacyPolicyUrl: 'https://privacy.microsoft.com/privacystatement',
    notes: 'Set by clarity.ms, only after you accept analytics.',
  },
  {
    name: 'MR',
    provider: 'Microsoft Corporation',
    domain: 'clarity.ms',
    category: 'analytics',
    purpose: 'Indicates whether the MUID identifier should be refreshed.',
    legalBasis: 'Consent (GDPR art. 6(1)(a) and ePrivacy Directive art. 5(3))',
    duration: 'Not stated by Microsoft (cookie list read on 26 October 2026)',
    type: 'cookie',
    firstOrThirdParty: 'third',
    isEssential: false,
    isCurrentlyUsed: true,
    service: 'Microsoft Clarity',
    dataShared: 'A refresh flag',
    privacyPolicyUrl: 'https://privacy.microsoft.com/privacystatement',
    notes: 'Set by clarity.ms, only after you accept analytics.',
  },
  {
    name: 'MUID',
    provider: 'Microsoft Corporation',
    domain: 'clarity.ms',
    category: 'marketing',
    purpose: 'Identifies unique browsers visiting Microsoft sites, used by Microsoft for advertising, site analytics and operations.',
    legalBasis: 'Consent (GDPR art. 6(1)(a) and ePrivacy Directive art. 5(3))',
    duration: 'Not stated by Microsoft (cookie list read on 26 October 2026)',
    type: 'cookie',
    firstOrThirdParty: 'third',
    isEssential: false,
    isCurrentlyUsed: true,
    service: 'Microsoft Clarity',
    dataShared: 'Pseudonymous browser identifier',
    privacyPolicyUrl: 'https://privacy.microsoft.com/privacystatement',
    notes: 'Set by clarity.ms only if you accept marketing: it is tied to the advertising signal sent to Clarity.',
  },
  {
    name: 'SM',
    provider: 'Microsoft Corporation',
    domain: 'clarity.ms',
    category: 'marketing',
    purpose: 'Synchronises the MUID identifier across Microsoft domains.',
    legalBasis: 'Consent (GDPR art. 6(1)(a) and ePrivacy Directive art. 5(3))',
    duration: 'Not stated by Microsoft (cookie list read on 26 October 2026)',
    type: 'cookie',
    firstOrThirdParty: 'third',
    isEssential: false,
    isCurrentlyUsed: true,
    service: 'Microsoft Clarity',
    dataShared: 'Pseudonymous browser identifier',
    privacyPolicyUrl: 'https://privacy.microsoft.com/privacystatement',
    notes: 'Set by clarity.ms only if you accept marketing.',
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
      'Let us measure how the site is used — which pages are read, which are ignored — through Google Analytics 4 and Microsoft Clarity (which records page use as anonymised session recordings and heatmaps). Off unless you accept.',
    marketing:
      'Governs advertising signals. No advertising tag is loaded on this site. What this controls is the ad-related consent sent to Google (accepting lets conversion measurement imported into Google Ads be attributed in full, declining keeps it limited) and to Microsoft Clarity (accepting lets Microsoft set its MUID and SM identifiers).',
  };
  return descriptions[cat];
}
