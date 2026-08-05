import React from 'react';

interface CookieFloatingButtonProps {
  onClick: () => void;
}

export default function CookieFloatingButton({ onClick }: CookieFloatingButtonProps) {
  return (
    <button
      onClick={onClick}
      aria-label="Manage cookie preferences"
      title="Manage cookie preferences"
      className="group fixed bottom-4 left-4 z-[90] flex items-center gap-2 rounded-full border border-white/10 bg-bg-dark/90 py-2 pl-2 pr-2 text-white/70 shadow-[0_10px_30px_-10px_rgba(2,6,23,0.6)] backdrop-blur-md transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-accent-teal/40 hover:pr-3.5 hover:text-text-inverse hover:shadow-[0_14px_36px_-10px_rgba(2,6,23,0.7)] motion-reduce:transition-none print:hidden"
    >
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-accent-teal/40 bg-accent-teal/10 text-accent-teal transition-colors group-hover:bg-accent-teal/20">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3a9 9 0 1 0 9 9 3 3 0 0 1-4-4 3 3 0 0 1-5-5Z" />
          <circle cx="9.5" cy="14.5" r="1" fill="currentColor" stroke="none" />
          <circle cx="14" cy="16" r="1" fill="currentColor" stroke="none" />
          <circle cx="8" cy="10" r="1" fill="currentColor" stroke="none" />
        </svg>
      </span>
      {/* Collapsed to an icon by default; the label expands on hover and focus so the
          control stays discoverable without occupying the corner permanently. */}
      <span className="max-w-0 overflow-hidden whitespace-nowrap text-xs font-medium opacity-0 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:max-w-[7rem] group-hover:opacity-100 group-focus-visible:max-w-[7rem] group-focus-visible:opacity-100 motion-reduce:transition-none">
        Cookie settings
      </span>
    </button>
  );
}
