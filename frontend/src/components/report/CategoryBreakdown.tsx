import React from 'react';
import type { CategoryScore } from '../../lib/mockData';

const gradeConfig = {
  excellent: { color: '#059669', bg: 'rgba(5, 150, 105, 0.08)', label: 'Excellent' },
  good: { color: '#0D9488', bg: 'rgba(13, 148, 136, 0.08)', label: 'Good' },
  foundation: { color: '#D97706', bg: 'rgba(217, 119, 6, 0.08)', label: 'Foundation' },
  critical: { color: '#DC2626', bg: 'rgba(220, 38, 38, 0.08)', label: 'Critical' },
};

interface CategoryBreakdownProps {
  categories: CategoryScore[];
}

export default function CategoryBreakdown({ categories }: CategoryBreakdownProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {categories.map((cat) => {
        const config = gradeConfig[cat.grade];
        const pct = (cat.score / cat.maxScore) * 100;
        const isEmpty = cat.score === 0;

        return (
          <div
            key={cat.slug}
            className={`p-4 rounded-lg border bg-bg-surface transition-colors ${
              isEmpty ? 'border-border opacity-75' : 'border-border hover:border-accent-teal/25'
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-xs font-medium text-text-secondary truncate">{cat.name}</span>
              <span
                className="shrink-0 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded"
                style={{
                  color: config.color,
                  backgroundColor: config.bg,
                }}
              >
                {config.label}
              </span>
            </div>

            <div className="flex items-baseline gap-1.5 mb-2.5">
              <span className="font-mono text-xl font-bold tabular-nums" style={{ color: config.color }}>
                {cat.score}
              </span>
              <span className="font-mono text-xs text-text-muted">/ {cat.maxScore}</span>
            </div>

            <div className="h-1 rounded-full bg-bg-subtle overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700 ease-out"
                style={{
                  width: `${pct}%`,
                  backgroundColor: config.color,
                }}
              />
            </div>

            {cat.signals.length > 0 && (
              <ul className="mt-2.5 space-y-1">
                {cat.signals.slice(0, 3).map((signal, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-text-muted">
                    <span className="w-1 h-1 rounded-full mt-[5px] shrink-0" style={{ backgroundColor: config.color }} />
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
