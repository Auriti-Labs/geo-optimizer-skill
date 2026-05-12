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
      className="fixed bottom-4 left-4 z-[90] flex items-center gap-2 px-3 py-2 rounded-full border border-border bg-bg-surface text-text-secondary text-xs font-medium shadow-lg hover:text-text-primary hover:border-accent-teal/30 hover:shadow-xl transition-all"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 6v6l4 2" />
      </svg>
      <span className="hidden sm:inline">Cookies</span>
    </button>
  );
}
