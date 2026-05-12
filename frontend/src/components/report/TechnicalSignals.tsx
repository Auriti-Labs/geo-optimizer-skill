import React from 'react';
import type { TechnicalSignal } from '../../lib/mockData';

const statusConfig = {
  pass: { color: '#059669', bg: 'rgba(5, 150, 105, 0.08)', icon: 'check' },
  warn: { color: '#D97706', bg: 'rgba(217, 119, 6, 0.08)', icon: 'alert' },
  fail: { color: '#DC2626', bg: 'rgba(220, 38, 38, 0.08)', icon: 'x' },
};

interface TechnicalSignalsProps {
  signals: TechnicalSignal[];
}

export default function TechnicalSignals({ signals }: TechnicalSignalsProps) {
  return (
    <div className="divide-y divide-border border border-border rounded-lg bg-bg-surface overflow-hidden">
      {signals.map((signal) => {
        const config = statusConfig[signal.status];

        return (
          <div
            key={signal.id}
            className="flex items-center gap-3 px-4 py-3 hover:bg-bg-subtle/40 transition-colors"
          >
            <span
              className="shrink-0 w-6 h-6 rounded-md flex items-center justify-center"
              style={{ backgroundColor: config.bg }}
            >
              {config.icon === 'check' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={config.color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              )}
              {config.icon === 'alert' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={config.color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 9v4M12 17h.01" />
                </svg>
              )}
              {config.icon === 'x' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={config.color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              )}
            </span>

            <div className="flex-1 min-w-0 flex flex-col sm:flex-row sm:items-center gap-0.5 sm:gap-3">
              <span className="text-sm font-medium text-text-primary truncate">{signal.name}</span>
              <span className="text-xs text-text-secondary sm:ml-auto shrink-0">{signal.description}</span>
            </div>

            <span
              className="shrink-0 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded uppercase tracking-wider"
              style={{ color: config.color, backgroundColor: config.bg }}
            >
              {signal.status}
            </span>
          </div>
        );
      })}
    </div>
  );
}
