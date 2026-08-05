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
        className={`relative overflow-hidden rounded-[var(--radius-lg)] border border-white/10 bg-bg-dark/95 shadow-[0_24px_60px_-20px_rgba(2,6,23,0.75)] backdrop-blur-xl transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none ${
          entered ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        {/* Teal wash in the top-left corner: gives the dark card depth without a second surface. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-24 -left-16 h-48 w-48 rounded-full bg-[#5EEAD4]/15 blur-3xl"
        />
        {/* Hairline highlight along the top edge, the way a lit panel catches light. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#5EEAD4]/50 to-transparent"
        />

        <div className="relative p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/[0.06]">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-[#5EEAD4]">
                  <path d="M12 3a9 9 0 1 0 9 9 3 3 0 0 1-4-4 3 3 0 0 1-5-5Z" />
                  <circle cx="9.5" cy="14.5" r="1" fill="currentColor" stroke="none" />
                  <circle cx="14" cy="16" r="1" fill="currentColor" stroke="none" />
                  <circle cx="8" cy="10" r="1" fill="currentColor" stroke="none" />
                </svg>
              </span>
              <div>
                <p className="font-display text-sm font-semibold text-text-inverse">Your privacy, your call</p>
                <p className="text-[11px] font-mono uppercase tracking-wider text-white/55">Nothing loads without consent</p>
              </div>
            </div>

            <button
              onClick={onDismiss}
              aria-label="Close and keep essential settings only"
              title="Close and keep essential settings only"
              className="-mr-1 -mt-1 shrink-0 rounded-md p-1.5 text-white/55 transition-colors hover:bg-white/5 hover:text-text-inverse"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          <p className="mt-3.5 text-[13px] leading-relaxed text-white/70">
            We load only what the site needs to work. Analytics and marketing stay off until you
            turn them on — and the site behaves identically either way.
          </p>

          {/* Category summary: makes the default state legible before any click, so
              "reject" is an informed choice rather than a leap of faith. */}
          <ul className="mt-4 grid grid-cols-2 gap-1.5">
            {categories.map((cat) => {
              const isOn = CATEGORY_STATE[cat] === 'on';
              const count = getCookiesByCategory(cat).length;
              return (
                <li
                  key={cat}
                  className="flex items-center gap-2 rounded-[var(--radius-sm)] border border-white/[0.07] bg-white/[0.03] px-2.5 py-1.5"
                >
                  <span
                    aria-hidden="true"
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${isOn ? 'bg-[#5EEAD4]' : 'bg-white/45'}`}
                  />
                  <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-white/75">
                    {getCategoryLabel(cat)}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-white/55">
                    {isOn ? 'on' : count === 0 ? 'none' : 'off'}
                  </span>
                </li>
              );
            })}
          </ul>

          <div className="mt-4 flex flex-col gap-2">
            <button
              onClick={onAcceptAll}
              className="w-full rounded-[var(--radius-sm)] bg-[#0F766E] px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-[#0F766E]/25 transition-colors duration-200 hover:bg-[#115E59] motion-reduce:transition-none"
            >
              Accept all
            </button>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={onRejectNonEssential}
                className="rounded-[var(--radius-sm)] border border-white/12 bg-white/[0.04] px-3 py-2 text-[13px] font-medium text-white/80 transition-colors hover:border-white/25 hover:bg-white/[0.08] hover:text-text-inverse"
              >
                Essential only
              </button>
              <button
                onClick={onCustomize}
                className="rounded-[var(--radius-sm)] border border-white/12 bg-white/[0.04] px-3 py-2 text-[13px] font-medium text-white/80 transition-colors hover:border-white/25 hover:bg-white/[0.08] hover:text-text-inverse"
              >
                Customise
              </button>
            </div>
          </div>

          <p className="mt-3.5 text-[11px] leading-relaxed text-white/55">
            <a href="/cookie-policy/" className="text-[#5EEAD4] underline decoration-[#5EEAD4]/60 underline-offset-2 transition-colors hover:decoration-[#5EEAD4]">
              Cookie Policy
            </a>
            {' · '}
            <a href="/privacy/" className="text-[#5EEAD4] underline decoration-[#5EEAD4]/60 underline-offset-2 transition-colors hover:decoration-[#5EEAD4]">
              Privacy Policy
            </a>
            {' — change your mind any time from the cookie button.'}
          </p>
        </div>
      </div>
    </div>
  );
}
