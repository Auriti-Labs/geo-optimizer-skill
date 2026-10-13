import React from 'react';

interface ReportHeaderProps {
  url: string;
  geoScore: number;
  citabilityScore: number | null;
  grade: 'excellent' | 'good' | 'foundation' | 'critical';
  timestamp: string;
  version: string;
  criticalCount?: number;
  highCount?: number;
}

// Band → state token (Status Monopoly rule): excellent/good report pass,
// foundation reports warn, critical reports fail.
const gradeConfig = {
  excellent: { text: 'text-pass-deep', chip: 'bg-pass-wash text-pass-deep', label: 'Excellent' },
  good: { text: 'text-pass-deep', chip: 'bg-pass-wash text-pass-deep', label: 'Good' },
  foundation: { text: 'text-warn', chip: 'bg-warn-wash text-warn', label: 'Foundation' },
  critical: { text: 'text-fail', chip: 'bg-fail-wash text-fail', label: 'Critical' },
};

export default function ReportHeader({
  url,
  geoScore,
  citabilityScore,
  grade,
  timestamp,
  version,
  criticalCount = 0,
  highCount = 0,
}: ReportHeaderProps) {
  const config = gradeConfig[grade];
  const date = new Date(timestamp).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="overflow-hidden rounded-[4px] border border-rail bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-rail px-5 py-2.5">
        <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-mute">Audit Report</span>
        <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-mute">v{version}</span>
      </div>

      <div className="flex flex-col gap-5 p-5 md:flex-row md:items-start md:justify-between">
        <div className="flex-1 min-w-0">
          <h2 className="text-lg md:text-xl font-bold text-ink break-all leading-snug" title={url}>
            {url}
          </h2>

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 font-mono text-[11px] text-ink-mute">
            <span>{date}</span>
            <span className="h-1 w-1 rounded-full bg-ink-mute" aria-hidden="true" />
            <span className={`rounded-[2px] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] ${config.chip}`}>
              {config.label}
            </span>
            {(criticalCount > 0 || highCount > 0) && (
              <>
                <span className="h-1 w-1 rounded-full bg-ink-mute" aria-hidden="true" />
                <span className="tabular-nums">
                  {criticalCount > 0 && (
                    <span className="text-fail">{criticalCount} critical</span>
                  )}
                  {criticalCount > 0 && highCount > 0 && ' · '}
                  {highCount > 0 && (
                    <span className="text-warn">{highCount} high</span>
                  )}
                </span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-6 shrink-0">
          <div className="text-center min-w-[72px]">
            <div className={`font-head text-2xl md:text-3xl font-extrabold tabular-nums ${config.text}`}>
              {geoScore}
            </div>
            <div className="mt-0.5 font-mono text-[10px] text-ink-mute">/ 100 GEO</div>
          </div>

          <div className="h-10 w-px bg-rail" aria-hidden="true" />

          <div className="text-center min-w-[72px]">
            <div className="font-head text-2xl md:text-3xl font-extrabold tabular-nums text-ink-soft">
              {citabilityScore ?? '—'}
            </div>
            <div className="mt-0.5 font-mono text-[10px] text-ink-mute">/ 100 Citability</div>
          </div>
        </div>
      </div>
    </div>
  );
}
