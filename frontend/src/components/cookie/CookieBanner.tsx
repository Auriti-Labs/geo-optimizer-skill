import React, { useEffect, useState } from 'react';
import { getCategories, getCategoryLabel, getCookiesByCategory, type CookieCategory } from '../../lib/cookieRegistry';

interface CookieBannerProps {
  onAcceptAll: () => void;
  onRejectNonEssential: () => void;
  onCustomize: () => void;
  onDismiss: () => void;
}

/** Categories are shown as a read-only summary here; the modal is where they are toggled. */
const CATEGORY_STATE: Record<CookieCategory, string> = {
  necessary: 'on',
  preferences: 'off',
  analytics: 'off',
  marketing: 'off',
};

export default function CookieBanner({
  onAcceptAll,
  onRejectNonEssential,
  onCustomize,
  onDismiss,
}: CookieBannerProps) {
  // Mount before painting the entrance transition, so the card animates in
  // instead of appearing fully formed. Skipped entirely under reduced motion,
  // where the transition classes resolve to no movement anyway.
  const [entered, setEntered] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setEntered(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const categories = getCategories();

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      aria-live="polite"
      className="fixed z-[100] inset-x-3 bottom-3 sm:inset-x-auto sm:left-5 sm:bottom-5 sm:w-[27rem] print:hidden"
    >
      <div
        className={`relative overflow-hidden rounded-[10px] border border-rail bg-raised transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none ${
          entered ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        <div className="relative p-3 sm:p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="hidden items-center gap-2.5 sm:flex">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[6px] border border-rail bg-paper text-ink">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3a9 9 0 1 0 9 9 3 3 0 0 1-4-4 3 3 0 0 1-5-5Z" />
                  <circle cx="9.5" cy="14.5" r="1" fill="currentColor" stroke="none" />
                  <circle cx="14" cy="16" r="1" fill="currentColor" stroke="none" />
                  <circle cx="8" cy="10" r="1" fill="currentColor" stroke="none" />
                </svg>
              </span>
              <div>
                <p className="text-sm font-semibold text-ink">Your privacy, your call</p>
                <p className="font-text font-medium text-[12px] text-ink-mute">Nothing loads without consent</p>
              </div>
            </div>

            {/* Mobile: one short line replaces title, description, categories and
                footer, so the banner stays a low bar instead of covering the page. */}
            <p className="min-w-0 flex-1 text-[13px] leading-5 text-ink-soft sm:hidden">
              Analytics cookies stay off unless you accept.{' '}
              <a href="/cookie-policy/" className="text-pass-deep underline decoration-rail underline-offset-2">
                Cookie Policy
              </a>
              {' · '}
              <button
                onClick={onCustomize}
                className="text-pass-deep underline decoration-rail underline-offset-2"
              >
                Preferences
              </button>
            </p>

            <button
              onClick={onDismiss}
              aria-label="Close and keep essential settings only"
              title="Close and keep essential settings only"
              className="-mr-1 -mt-1 shrink-0 rounded-[6px] p-1.5 text-ink-mute transition-colors hover:bg-pass-wash hover:text-ink"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <p className="mt-3.5 hidden text-[13px] leading-relaxed text-ink-soft sm:block">
            We load only what the site needs to work. Analytics and marketing stay off until you
            turn them on — and the site behaves identically either way.
          </p>

          {/* Category summary: makes the default state legible before any click, so
              "reject" is an informed choice rather than a leap of faith. */}
          <ul className="mt-4 hidden grid-cols-2 gap-1.5 sm:grid">
            {categories.map((cat) => {
              const isOn = CATEGORY_STATE[cat] === 'on';
              const count = getCookiesByCategory(cat).length;
              return (
                <li
                  key={cat}
                  className="flex items-center gap-2 rounded-[6px] border border-rail bg-paper px-2.5 py-1.5"
                >
                  <span
                    aria-hidden="true"
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${isOn ? 'bg-pass' : 'bg-queued'}`}
                  />
                  <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-ink-soft">
                    {getCategoryLabel(cat)}
                  </span>
                  <span className={`shrink-0 font-text font-medium text-[12px] ${isOn ? 'text-pass-deep' : 'text-ink-mute'}`}>
                    {isOn ? 'on' : count === 0 ? 'none' : 'off'}
                  </span>
                </li>
              );
            })}
          </ul>

          {/* Mobile: Accept and Essential only side by side, same size; Customise
              moves to the "Preferences" link above. Desktop layout unchanged. */}
          <div className="mt-2.5 grid grid-cols-2 gap-2 sm:mt-4">
            <button
              onClick={onAcceptAll}
              className="min-h-11 w-full rounded-[10px] sm:col-span-2 sm:min-h-0 bg-pass-deep px-4 py-2.5 font-text text-[13px] font-semibold text-on-accent transition-colors duration-200 hover:bg-pass motion-reduce:transition-none"
            >
              Accept all
            </button>
            <button
              onClick={onRejectNonEssential}
              className="min-h-11 rounded-[10px] sm:min-h-0 border border-rail bg-raised px-3 py-2.5 font-text text-[13px] font-semibold text-ink transition-colors hover:bg-pass-wash"
            >
              Essential only
            </button>
            <button
              onClick={onCustomize}
              className="hidden rounded-[10px] sm:block border border-rail bg-raised px-3 py-2.5 font-text text-[13px] font-semibold text-ink transition-colors hover:bg-pass-wash"
            >
              Customise
            </button>
          </div>

          <p className="mt-3.5 hidden text-[11px] leading-relaxed text-ink-mute sm:block">
            <a href="/cookie-policy/" className="text-pass-deep underline decoration-rail underline-offset-2 transition-colors hover:decoration-pass-deep">
              Cookie Policy
            </a>
            {' · '}
            <a href="/privacy/" className="text-pass-deep underline decoration-rail underline-offset-2 transition-colors hover:decoration-pass-deep">
              Privacy Policy
            </a>
            {' — change your mind any time from the cookie button.'}
          </p>
        </div>
      </div>
    </div>
  );
}
