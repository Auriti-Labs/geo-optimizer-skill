import React, { useState } from 'react';
import type { Recommendation } from '../../lib/mockData';

// Priority → state token (Status Monopoly rule): critical reports fail,
// high reports warn; medium/low carry no alarm state and stay neutral —
// the chip label alone ranks them.
const priorityConfig = {
  critical: { chip: 'bg-fail-wash text-fail', label: 'Critical' },
  high: { chip: 'bg-warn-wash text-warn', label: 'High' },
  medium: { chip: 'border border-rail text-ink-mute', label: 'Medium' },
  low: { chip: 'border border-rail text-ink-mute', label: 'Low' },
};

interface RecommendationListProps {
  recommendations: Recommendation[];
}

export default function RecommendationList({ recommendations }: RecommendationListProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="divide-y divide-rail overflow-hidden rounded-[10px] border border-rail bg-white">
      {recommendations.map((rec) => {
        const config = priorityConfig[rec.priority];
        const isOpen = expanded.has(rec.id);
        const hasDetail = Boolean(rec.description);

        return (
          <div key={rec.id}>
            {hasDetail ? (
              <button
                onClick={() => toggle(rec.id)}
                aria-expanded={isOpen}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-pass-wash/50"
              >
                <span className={`shrink-0 rounded-[6px] px-2 py-0.5 font-text text-[12px] font-semibold ${config.chip}`}>
                  {config.label}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">{rec.title}</span>
                <span className="hidden shrink-0 font-mono text-[11px] text-pass-deep sm:inline">{rec.impact}</span>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className={`shrink-0 text-ink-mute transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                  aria-hidden="true"
                >
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </button>
            ) : (
              <div className="flex items-start gap-3 px-4 py-3">
                <span className={`mt-0.5 shrink-0 rounded-[6px] px-2 py-0.5 font-text text-[12px] font-semibold ${config.chip}`}>
                  {config.label}
                </span>
                <span className="text-sm leading-relaxed text-ink">{rec.title}</span>
              </div>
            )}

            {isOpen && hasDetail && (
              <div className="px-4 pb-4 pt-0">
                <p className="pt-3 text-sm leading-relaxed text-ink-soft">{rec.description}</p>
                <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] text-ink-mute">Category:</span>
                    <span className="font-mono text-[11px] text-ink-soft">{rec.category}</span>
                  </div>
                  <div className="flex items-center gap-1.5 sm:hidden">
                    <span className="text-[11px] text-ink-mute">Impact:</span>
                    <span className="font-mono text-[11px] text-pass-deep">{rec.impact}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
