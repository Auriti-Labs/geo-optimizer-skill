import React, { useState } from 'react';
import type { Recommendation } from '../../lib/mockData';

const priorityConfig = {
  critical: { color: '#DC2626', bg: 'rgba(220, 38, 38, 0.06)', border: 'rgba(220, 38, 38, 0.15)', label: 'Critical' },
  high: { color: '#D97706', bg: 'rgba(217, 119, 6, 0.06)', border: 'rgba(217, 119, 6, 0.15)', label: 'High' },
  medium: { color: '#0D9488', bg: 'rgba(13, 148, 136, 0.06)', border: 'rgba(13, 148, 136, 0.15)', label: 'Medium' },
  low: { color: '#475569', bg: 'rgba(71, 85, 105, 0.06)', border: 'rgba(71, 85, 105, 0.15)', label: 'Low' },
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
    <div className="space-y-2">
      {recommendations.map((rec) => {
        const config = priorityConfig[rec.priority];
        const isOpen = expanded.has(rec.id);
        const hasDetail = Boolean(rec.description);

        return (
          <div
            key={rec.id}
            className="rounded-lg border overflow-hidden transition-colors"
            style={{ borderColor: isOpen ? config.border : 'var(--color-border)' }}
          >
            {hasDetail ? (
              <button
                onClick={() => toggle(rec.id)}
                aria-expanded={isOpen}
                className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-bg-subtle/50 transition-colors"
              >
                <span
                  className="shrink-0 text-[11px] font-mono font-semibold px-2 py-0.5 rounded uppercase tracking-wider"
                  style={{ color: config.color, backgroundColor: config.bg }}
                >
                  {config.label}
                </span>
                <span className="flex-1 text-sm font-medium text-text-primary truncate min-w-0">{rec.title}</span>
                <span className="text-[11px] font-mono text-accent-teal shrink-0 hidden sm:inline">{rec.impact}</span>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className={`shrink-0 text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                >
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </button>
            ) : (
              <div className="px-4 py-3 flex items-start gap-3">
                <span
                  className="shrink-0 text-[11px] font-mono font-semibold px-2 py-0.5 rounded uppercase tracking-wider mt-0.5"
                  style={{ color: config.color, backgroundColor: config.bg }}
                >
                  {config.label}
                </span>
                <span className="text-sm text-text-primary leading-relaxed">{rec.title}</span>
              </div>
            )}

            {isOpen && hasDetail && (
              <div className="px-4 pb-4 pt-0 bg-bg-surface">
                <p className="text-sm text-text-secondary leading-relaxed pt-3">{rec.description}</p>
                <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] text-text-muted">Category:</span>
                    <span className="text-[11px] font-mono text-text-secondary">{rec.category}</span>
                  </div>
                  <div className="sm:hidden flex items-center gap-1.5">
                    <span className="text-[11px] text-text-muted">Impact:</span>
                    <span className="text-[11px] font-mono text-accent-teal">{rec.impact}</span>
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
