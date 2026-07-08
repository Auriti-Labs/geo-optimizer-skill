import React, { useEffect } from 'react';
import { trackGateTriggered, trackCtaClicked } from '../../lib/geo_track';

interface GateBannerProps {
  score: number;
  lockedCount: number;
  totalLockedPoints: number;
}

export default function GateBanner({ score, lockedCount, totalLockedPoints }: GateBannerProps) {
  useEffect(() => {
    trackGateTriggered({ score, locked_categories: lockedCount });
  }, []);

  function handleCtaClick() {
    trackCtaClicked({ cta_location: 'gate_banner', cta_text: 'Unlock full report' });
  }

  const potentialScore = score + totalLockedPoints;

  return (
    <div className="rounded-xl border border-accent-teal/25 bg-accent-teal/5 p-5 flex flex-col sm:flex-row items-start sm:items-center gap-4">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-teal shrink-0" aria-hidden="true">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span className="text-sm font-semibold text-text-primary">
            {lockedCount} categories locked — {totalLockedPoints} points hidden
          </span>
        </div>
        <p className="text-sm text-text-secondary leading-snug">
          Your visible score is <strong className="text-text-primary">{score}/100</strong>.
          The locked categories (llms.txt, Schema, Content, AI Discovery, Brand &amp; Entity)
          can add up to <strong className="text-accent-teal">+{totalLockedPoints} points</strong>,
          potentially reaching <strong className="text-accent-teal">{Math.min(potentialScore, 100)}/100</strong>.
          Unlock to see exactly where those points are and how to capture them.
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {['llms.txt +18', 'Schema +16', 'Content +12', 'AI Discovery +6', 'Brand +10'].map((label) => (
            <span
              key={label}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle text-text-muted border border-border"
            >
              {label}
            </span>
          ))}
        </div>
      </div>
      <a
        href="https://app.geoready.dev/signup"
        onClick={handleCtaClick}
        className="shrink-0 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-teal text-white text-sm font-semibold hover:bg-accent-teal-dark transition-colors"
      >
        Unlock full report
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </a>
    </div>
  );
}