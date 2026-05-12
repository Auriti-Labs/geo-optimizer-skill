import React from 'react';

interface CookieBannerProps {
  onAcceptAll: () => void;
  onRejectNonEssential: () => void;
  onCustomize: () => void;
  onDismiss: () => void;
}

export default function CookieBanner({
  onAcceptAll,
  onRejectNonEssential,
  onCustomize,
  onDismiss,
}: CookieBannerProps) {
  return (
    <div
      role="dialog"
      aria-label="Cookie consent banner"
      aria-live="polite"
      className="fixed inset-x-0 bottom-0 z-[100] border-t border-border bg-bg-surface shadow-2xl"
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 sm:py-5">
        <div className="flex flex-col sm:flex-row gap-4 sm:items-start">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2 h-2 rounded-full bg-accent-teal" />
              <span className="text-sm font-semibold text-text-primary">Manage your privacy</span>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed">
              We use only the cookies and storage necessary for the site to function.
              Analytics and marketing are disabled by default. You can customize your preferences or learn more in our{' '}
              <a href="/cookie-policy" className="text-accent-teal hover:underline underline-offset-2">Cookie Policy</a>{' '}
              and{' '}
              <a href="/privacy" className="text-accent-teal hover:underline underline-offset-2">Privacy Policy</a>.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              onClick={onRejectNonEssential}
              className="px-4 py-2 rounded-lg border border-border bg-bg-base text-sm font-medium text-text-secondary hover:text-text-primary hover:border-accent-teal/30 transition-colors"
            >
              Reject non-essential
            </button>
            <button
              onClick={onCustomize}
              className="px-4 py-2 rounded-lg border border-border bg-bg-base text-sm font-medium text-text-secondary hover:text-text-primary hover:border-accent-teal/30 transition-colors"
            >
              Customize
            </button>
            <button
              onClick={onAcceptAll}
              className="px-4 py-2 rounded-lg bg-accent-teal text-white text-sm font-medium hover:bg-accent-teal-dark transition-colors"
            >
              Accept all
            </button>
          </div>

          <button
            onClick={onDismiss}
            aria-label="Close cookie banner and keep essential settings only"
            className="shrink-0 p-1.5 rounded-md border border-border text-text-muted hover:text-text-primary hover:border-accent-teal/30 transition-colors"
            title="Close and keep essential settings only"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
