import React, { useEffect, useRef, useState } from 'react';
import {
  getConsent,
  saveCustomConsent,
  acceptAll,
  rejectAll,
  type ConsentState,
} from '../../lib/cookieConsent';
import {
  getCategories,
  getCategoryLabel,
  getCategoryDescription,
  getCookiesByCategory,
  CONSENT_VERSION,
  type CookieCategory,
} from '../../lib/cookieRegistry';

interface CookiePreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CookiePreferencesModal({ isOpen, onClose }: CookiePreferencesModalProps) {
  const [consent, setConsent] = useState<ConsentState>(getConsent());
  const [expanded, setExpanded] = useState<CookieCategory | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setConsent(getConsent());
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Lock the page behind the dialog: without this the body scrolls under the
  // panel on desktop, which reads as the page having jumped when the dialog closes.
  useEffect(() => {
    if (!isOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [isOpen]);

  // Move focus into the dialog when it opens, so keyboard and screen-reader users
  // land on the content rather than continuing from wherever the page was.
  useEffect(() => {
    if (isOpen) {
      panelRef.current?.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleToggle = (category: CookieCategory) => {
    if (category === 'necessary') return;
    setConsent((prev) => ({ ...prev, [category]: !prev[category] }));
  };

  const handleSave = () => {
    saveCustomConsent({
      preferences: consent.preferences,
      analytics: consent.analytics,
      marketing: consent.marketing,
    });
    onClose();
  };

  const handleAcceptAll = () => {
    acceptAll();
    onClose();
  };

  const handleReject = () => {
    rejectAll();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[110] flex items-end justify-center sm:items-center print:hidden"
      role="dialog"
      aria-modal="true"
      aria-label="Cookie preferences"
    >
      <div
        className="absolute inset-0 bg-bg-dark/60 backdrop-blur-md"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        ref={panelRef}
        tabIndex={-1}
        className="relative m-0 flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-t-[var(--radius-xl)] border border-border bg-bg-base shadow-[0_32px_80px_-24px_rgba(2,6,23,0.6)] outline-none sm:m-4 sm:rounded-[var(--radius-xl)]"
      >
        {/* Dark header, same visual language as the banner: the panel reads as the
            expanded form of that card rather than a separate component. */}
        <div className="relative shrink-0 overflow-hidden border-b border-white/[0.06] bg-bg-dark px-5 py-4 sm:px-6">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -top-20 -left-10 h-40 w-40 rounded-full bg-[#5EEAD4]/15 blur-3xl"
          />
          <div className="relative flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/[0.06] text-[#5EEAD4]">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3a9 9 0 1 0 9 9 3 3 0 0 1-4-4 3 3 0 0 1-5-5Z" />
                  <circle cx="9.5" cy="14.5" r="1" fill="currentColor" stroke="none" />
                  <circle cx="14" cy="16" r="1" fill="currentColor" stroke="none" />
                  <circle cx="8" cy="10" r="1" fill="currentColor" stroke="none" />
                </svg>
              </span>
              <div>
                <h2 className="font-display text-base font-bold text-text-inverse">Cookie preferences</h2>
                <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-white/55">
                  Consent version {CONSENT_VERSION}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close preferences"
              className="-mr-1 shrink-0 rounded-md p-1.5 text-white/55 transition-colors hover:bg-white/5 hover:text-text-inverse"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
          <p className="text-sm leading-relaxed text-text-secondary">
            Choose which categories you accept. Necessary items keep the site working and cannot
            be switched off. Everything else is off until you say otherwise.{' '}
            <a href="/cookie-policy/" className="text-[#0F766E] underline decoration-[#0F766E] underline-offset-2 hover:text-[#115E59] hover:decoration-[#115E59]">
              Full cookie policy
            </a>
            .
          </p>

          <div className="mt-5 space-y-2.5">
            {getCategories().map((cat) => {
              const label = getCategoryLabel(cat);
              const description = getCategoryDescription(cat);
              const isNecessary = cat === 'necessary';
              const isActive = isNecessary ? true : consent[cat];
              const cookies = getCookiesByCategory(cat);
              const isExpanded = expanded === cat;

              return (
                <div
                  key={cat}
                  className={`overflow-hidden rounded-[var(--radius-md)] border bg-bg-surface transition-colors duration-200 motion-reduce:transition-none ${
                    isActive ? 'border-[#0F766E]/35' : 'border-border'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4 p-4">
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-text-primary">{label}</span>
                        {isNecessary ? (
                          <span className="rounded border border-[#047857]/25 bg-[#047857]/[0.06] px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-[#047857]">
                            always on
                          </span>
                        ) : (
                          <span className="font-mono text-[10px] uppercase tracking-wider text-text-secondary">
                            {cookies.length === 0 ? 'nothing stored' : `${cookies.length} item${cookies.length > 1 ? 's' : ''}`}
                          </span>
                        )}
                      </div>
                      <p className="text-xs leading-relaxed text-text-secondary">{description}</p>

                      {cookies.length > 0 && (
                        <button
                          onClick={() => setExpanded(isExpanded ? null : cat)}
                          aria-expanded={isExpanded}
                          className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-[#0F766E] transition-colors hover:text-[#115E59]"
                        >
                          {isExpanded ? 'Hide details' : 'What exactly is stored'}
                          <svg
                            width="11"
                            height="11"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            className={`transition-transform duration-200 motion-reduce:transition-none ${isExpanded ? 'rotate-180' : ''}`}
                            aria-hidden="true"
                          >
                            <polyline points="6 9 12 15 18 9" />
                          </svg>
                        </button>
                      )}
                    </div>

                    <button
                      onClick={() => handleToggle(cat)}
                      disabled={isNecessary}
                      aria-pressed={isActive}
                      aria-label={`Toggle ${label}`}
                      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200 motion-reduce:transition-none ${
                        isActive ? 'bg-[#0F766E]' : 'bg-text-secondary/30'
                      } ${isNecessary ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                    >
                      <span
                        className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none ${
                          isActive ? 'translate-x-5' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>

                  {/* Details stay collapsed by default: the inventory is long, and the
                      choice is easier to make when the summary comes first. */}
                  {isExpanded && cookies.length > 0 && (
                    <div className="border-t border-border bg-bg-base px-4 py-3">
                      <div className="space-y-3">
                        {cookies.map((c) => (
                          <div key={`${c.name}-${c.type}`} className="text-xs text-text-secondary">
                            <div className="mb-1 flex flex-wrap items-center gap-1.5">
                              <span className="font-mono text-[11px] font-semibold text-text-primary">{c.name}</span>
                              <span className="text-[10px] text-text-secondary">{c.type}</span>
                              {c.firstOrThirdParty === 'third' && (
                                <span className="rounded border border-[#B45309]/25 px-1 font-mono text-[10px] text-[#B45309]">
                                  third party
                                </span>
                              )}
                              {c.isCurrentlyUsed && (
                                <span className="rounded border border-[#047857]/25 px-1 font-mono text-[10px] text-[#047857]">
                                  active
                                </span>
                              )}
                            </div>
                            <p className="leading-snug">{c.purpose}</p>
                            <dl className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-[11px] leading-snug">
                              <dt className="font-mono uppercase tracking-wide text-text-secondary/70">Provider</dt>
                              <dd className="text-text-secondary">{c.provider}</dd>
                              <dt className="font-mono uppercase tracking-wide text-text-secondary/70">Duration</dt>
                              <dd className="text-text-secondary">{c.duration}</dd>
                              <dt className="font-mono uppercase tracking-wide text-text-secondary/70">Basis</dt>
                              <dd className="text-text-secondary">{c.legalBasis}</dd>
                            </dl>
                            {c.notes && <p className="mt-1 italic leading-snug text-text-secondary">{c.notes}</p>}
                            {c.privacyPolicyUrl && (
                              <a
                                href={c.privacyPolicyUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-1 inline-block text-[11px] text-[#0F766E] hover:underline"
                              >
                                Provider privacy policy →
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="shrink-0 border-t border-border bg-bg-surface px-5 py-4 sm:px-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <button
              onClick={handleReject}
              className="order-2 rounded-[var(--radius-sm)] border border-border bg-bg-base px-4 py-2 text-sm font-medium text-text-secondary transition-colors hover:border-text-secondary/30 hover:text-text-primary sm:order-1"
            >
              Essential only
            </button>
            <div className="order-1 flex gap-2 sm:order-2">
              <button
                onClick={handleSave}
                className="flex-1 rounded-[var(--radius-sm)] border border-[#0F766E]/40 px-4 py-2 text-sm font-medium text-[#0F766E] transition-colors hover:bg-[#0F766E]/[0.06] sm:flex-none"
              >
                Save choices
              </button>
              <button
                onClick={handleAcceptAll}
                className="flex-1 rounded-[var(--radius-sm)] bg-[#0F766E] px-4 py-2 text-sm font-semibold text-white shadow-md shadow-[#0F766E]/25 transition-colors hover:bg-[#115E59] sm:flex-none"
              >
                Accept all
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
