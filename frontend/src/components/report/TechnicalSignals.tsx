import React from 'react';
import type { TechnicalSignal } from '../../lib/mockData';

// Status → state token (Status Monopoly rule): color appears only where it
// reports pass / warn / fail.
const statusConfig = {
  pass: { text: 'text-pass-deep', chip: 'bg-pass-wash text-pass-deep', disk: 'bg-pass-wash', icon: 'check' },
  warn: { text: 'text-warn', chip: 'bg-warn-wash text-warn', disk: 'bg-warn-wash', icon: 'alert' },
  fail: { text: 'text-fail', chip: 'bg-fail-wash text-fail', disk: 'bg-fail-wash', icon: 'x' },
};

interface TechnicalSignalsProps {
  signals: TechnicalSignal[];
}

export default function TechnicalSignals({ signals }: TechnicalSignalsProps) {
  return (
    <div className="divide-y divide-rail overflow-hidden rounded-[10px] border border-rail bg-raised">
      {signals.map((signal) => {
        const config = statusConfig[signal.status];

        return (
          <div
            key={signal.id}
            className="flex items-center gap-3 px-4 py-3"
          >
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${config.disk} ${config.text}`}
              aria-hidden="true"
            >
              {config.icon === 'check' && (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              )}
              {config.icon === 'alert' && (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 9v4M12 17h.01" />
                </svg>
              )}
              {config.icon === 'x' && (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              )}
            </span>

            <div className="flex min-w-0 flex-1 flex-col gap-0.5 sm:flex-row sm:items-center sm:gap-3">
              <span className="truncate text-sm font-medium text-ink">{signal.name}</span>
              <span className="shrink-0 text-xs text-ink-soft sm:ml-auto">{signal.description}</span>
            </div>

            <span className={`shrink-0 rounded-[6px] px-1.5 py-0.5 font-text text-[12px] font-semibold ${config.chip}`}>
              {signal.status}
            </span>
          </div>
        );
      })}
    </div>
  );
}
