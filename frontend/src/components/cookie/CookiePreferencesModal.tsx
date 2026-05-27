import React, { useEffect, useState } from 'react';
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
  type CookieCategory,
} from '../../lib/cookieRegistry';

interface CookiePreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CookiePreferencesModal({ isOpen, onClose }: CookiePreferencesModalProps) {
  const [consent, setConsent] = useState<ConsentState>(getConsent());

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
      className="fixed inset-0 z-[110] flex items-end sm:items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label="Cookie preferences"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-bg-surface border border-border rounded-t-xl sm:rounded-xl shadow-2xl m-0 sm:m-4">
        <div className="sticky top-0 bg-bg-surface border-b border-border px-5 py-4 flex items-center justify-between z-10">
          <h2 className="font-display text-lg font-bold text-text-primary">Cookie Preferences</h2>
          <button
            onClick={onClose}
            aria-label="Close preferences"
            className="p-1.5 rounded-md border border-border text-text-muted hover:text-text-primary hover:border-accent-teal/30 transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          <p className="text-sm text-text-secondary leading-relaxed">
            You can choose which categories of cookies and storage you accept. Necessary items cannot be disabled.{' '}
            <a href="/cookie-policy/" className="text-accent-teal hover:underline underline-offset-2">Learn more</a>.
          </p>

          {/* Category toggles */}
          <div className="space-y-3">
            {getCategories().map((cat) => {
              const label = getCategoryLabel(cat);
              const description = getCategoryDescription(cat);
              const isNecessary = cat === 'necessary';
              const isActive = isNecessary ? true : consent[cat];
              const cookies = getCookiesByCategory(cat);

              return (
                <div key={cat} className="rounded-lg border border-border bg-bg-base p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`w-2 h-2 rounded-full ${isNecessary ? 'bg-accent-success' : 'bg-accent-teal'}`} />
                        <span className="text-sm font-semibold text-text-primary">{label}</span>
                        {isNecessary && (
                          <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-accent-success border border-accent-success/20 px-1.5 py-0.5 rounded">Always on</span>
                        )}
                      </div>
                      <p className="text-xs text-text-secondary leading-relaxed">{description}</p>
                    </div>

                    <button
                      onClick={() => handleToggle(cat)}
                      disabled={isNecessary}
                      aria-pressed={isActive}
                      aria-label={`Toggle ${label}`}
                      className={`relative w-11 h-6 rounded-full transition-colors shrink-0 ${
                        isActive ? 'bg-accent-teal' : 'bg-text-muted/30'
                      } ${isNecessary ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
                    >
                      <span
                        className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                          isActive ? 'translate-x-5' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>

                  {/* Cookie list per category */}
                  {cookies.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <div className="space-y-2">
                        {cookies.map((c) => (
                          <div key={c.name} className="text-xs text-text-secondary">
                            <div className="flex items-center gap-1.5 mb-0.5">
                              <span className="font-mono font-semibold text-text-primary">{c.name}</span>
                              <span className="text-text-muted">{c.type}</span>
                              {c.firstOrThirdParty === 'third' && (
                                <span className="text-[10px] font-mono text-accent-warning border border-accent-warning/20 px-1 rounded">third party</span>
                              )}
                              {c.isCurrentlyUsed && (
                                <span className="text-[10px] font-mono text-accent-success border border-accent-success/20 px-1 rounded">active</span>
                              )}
                            </div>
                            <p className="leading-snug">{c.purpose}</p>
                            <div className="flex flex-wrap gap-2 mt-0.5 text-text-muted">
                              <span>Provider: {c.provider}</span>
                              <span>· Duration: {c.duration}</span>
                              {c.privacyPolicyUrl && (
                                <a
                                  href={c.privacyPolicyUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-accent-teal hover:underline"
                                >
                                  Provider privacy
                                </a>
                              )}
                            </div>
                            {c.notes && <p className="text-text-muted mt-0.5 italic">{c.notes}</p>}
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

        {/* Actions */}
        <div className="sticky bottom-0 bg-bg-surface border-t border-border px-5 py-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleReject}
              className="px-4 py-2 rounded-lg border border-border bg-bg-base text-sm font-medium text-text-secondary hover:text-text-primary hover:border-accent-teal/30 transition-colors"
            >
              Reject non-essential
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 rounded-lg bg-accent-teal text-white text-sm font-medium hover:bg-accent-teal-dark transition-colors"
            >
              Save preferences
            </button>
          </div>
          <button
            onClick={handleAcceptAll}
            className="px-4 py-2 rounded-lg border border-accent-teal/30 text-accent-teal text-sm font-medium hover:bg-accent-teal/5 transition-colors"
          >
            Accept all
          </button>
        </div>
      </div>
    </div>
  );
}
