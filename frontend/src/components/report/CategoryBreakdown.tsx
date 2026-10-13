import React from 'react';
import type { CategoryScore } from '../../lib/mockData';

// Band → state token (Status Monopoly rule): excellent/good report pass,
// foundation reports warn, critical reports fail.
const gradeConfig = {
  excellent: { text: 'text-pass-deep', chip: 'bg-pass-wash text-pass-deep', bar: 'bg-pass', dot: 'bg-pass', label: 'Excellent' },
  good: { text: 'text-pass-deep', chip: 'bg-pass-wash text-pass-deep', bar: 'bg-pass', dot: 'bg-pass', label: 'Good' },
  foundation: { text: 'text-warn', chip: 'bg-warn-wash text-warn', bar: 'bg-warn', dot: 'bg-warn', label: 'Foundation' },
  critical: { text: 'text-fail', chip: 'bg-fail-wash text-fail', bar: 'bg-fail', dot: 'bg-fail', label: 'Critical' },
};

interface LockedCardProps {
  category: CategoryScore;
}

// Nome e massimo arrivano dalla categoria mappata: con la rubrica v2 i massimi
// fissati qui (v1) mostravano valori sbagliati, per esempio "/ 10" per Brand.
function LockedCard({ category }: LockedCardProps) {
  return (
    <div className="relative overflow-hidden bg-white p-4">
      {/* Blurred content background — hides the locked data, not decoration */}
      <div className="blur-[3px] pointer-events-none select-none" aria-hidden="true">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="truncate text-xs font-medium text-ink-soft">
            {category.name}
          </span>
          <span className="shrink-0 rounded-[2px] border border-rail px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-mute">
            —
          </span>
        </div>
        <div className="mb-2.5 flex items-baseline gap-1.5">
          <span className="font-mono text-xl font-bold tabular-nums text-ink-mute">??</span>
          <span className="font-mono text-xs tabular-nums text-ink-mute">/ {category.maxScore}</span>
        </div>
        <div className="h-1 overflow-hidden rounded-[2px] bg-paper">
          <div className="h-full w-1/3 rounded-[2px] bg-ink-mute/30" />
        </div>
        <ul className="mt-2.5 space-y-1">
          {[1, 2, 3].map((i) => (
            <li key={i} className="h-3 rounded-[2px] bg-paper" />
          ))}
        </ul>
      </div>

      {/* Lock overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/85 p-3 text-center">
        <div className="mb-2 flex h-7 w-7 items-center justify-center rounded-full bg-pass-wash">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-pass-deep">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] leading-tight text-pass-deep">
          Pro
        </span>
      </div>
    </div>
  );
}

interface CategoryBreakdownProps {
  categories: CategoryScore[];
  lockedSlugs?: string[];
}

export default function CategoryBreakdown({ categories, lockedSlugs = [] }: CategoryBreakdownProps) {
  const lockedSet = new Set(lockedSlugs);

  return (
    <div className="grid grid-cols-1 gap-px overflow-hidden rounded-[4px] border border-rail bg-rail sm:grid-cols-2 lg:grid-cols-4">
      {categories.map((cat, i) => {
        // Il flag della categoria vale anche dove il chiamante non passa lockedSlugs (pagine di confronto)
        if (cat.locked || lockedSet.has(cat.slug)) {
          return <LockedCard key={cat.slug} category={cat} />;
        }

        const config = gradeConfig[cat.grade];
        const pct = (cat.score / cat.maxScore) * 100;
        const isEmpty = cat.score === 0;

        return (
          <div
            key={cat.slug}
            className={`bg-white p-4 ${isEmpty ? 'opacity-75' : ''}`}
          >
            <div className="mb-2 flex items-start justify-between gap-2">
              <span className="flex min-w-0 items-baseline gap-2">
                <span className="font-mono text-[11px] font-medium tabular-nums text-ink-mute">{String(i + 1).padStart(2, '0')}</span>
                <span className="truncate text-xs font-medium text-ink">{cat.name}</span>
              </span>
              <span className={`shrink-0 rounded-[2px] px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.1em] ${config.chip}`}>
                {config.label}
              </span>
            </div>

            <div className="mb-2.5 flex items-baseline justify-between gap-1.5">
              <span className="flex items-baseline gap-1.5">
                <span className={`font-mono text-xl font-bold tabular-nums ${config.text}`}>
                  {cat.score}
                </span>
                <span className="font-mono text-xs tabular-nums text-pass-deep">/ {cat.maxScore}</span>
              </span>
              <span className="truncate font-mono text-[11px] text-ink-mute">{cat.slug}</span>
            </div>

            <div className="h-1 overflow-hidden rounded-[2px] bg-paper">
              <div
                className={`h-full rounded-[2px] transition-all duration-700 ease-out ${config.bar}`}
                style={{ width: `${pct}%` }}
              />
            </div>

            {cat.signals.length > 0 && (
              <ul className="mt-2.5 space-y-1">
                {cat.signals.slice(0, 3).map((signal, j) => (
                  <li key={j} className="flex items-start gap-1.5 text-xs text-ink-mute">
                    <span className={`mt-[5px] h-1 w-1 shrink-0 rounded-full ${config.dot}`} aria-hidden="true" />
                    <span className="leading-snug">{signal}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
