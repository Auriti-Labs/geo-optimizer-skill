import React from 'react';

interface ReportHeaderProps {
  url: string;
  geoScore: number;
  citabilityScore: number;
  grade: 'excellent' | 'good' | 'foundation' | 'critical';
  timestamp: string;
  version: string;
  criticalCount?: number;
  highCount?: number;
}

const gradeConfig = {
  excellent: { color: '#059669', label: 'Excellent' },
  good: { color: '#0D9488', label: 'Good' },
  foundation: { color: '#D97706', label: 'Foundation' },
  critical: { color: '#DC2626', label: 'Critical' },
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
    <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-5 p-5 rounded-xl border border-border bg-bg-surface">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 text-[10px] font-mono text-text-muted uppercase tracking-wider">
          <span>Audit Report</span>
          <span className="w-1 h-1 rounded-full bg-text-muted" />
          <span>v{version}</span>
        </div>

        <h2 className="mt-1.5 text-lg md:text-xl font-bold text-text-primary break-all leading-snug" title={url}>
          {url}
        </h2>

        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-text-muted">
          <span className="font-mono">{date}</span>
          <span className="w-1 h-1 rounded-full bg-text-muted" />
          <span
            className="font-mono font-semibold px-1.5 py-0.5 rounded text-[10px]"
            style={{ color: config.color, backgroundColor: `${config.color}14` }}
          >
            {config.label}
          </span>
          {(criticalCount > 0 || highCount > 0) && (
            <>
              <span className="w-1 h-1 rounded-full bg-text-muted" />
              <span className="font-mono">
                {criticalCount > 0 && (
                  <span style={{ color: '#DC2626' }}>{criticalCount} critical</span>
                )}
                {criticalCount > 0 && highCount > 0 && ' · '}
                {highCount > 0 && (
                  <span style={{ color: '#D97706' }}>{highCount} high</span>
                )}
              </span>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-6 shrink-0">
        <div className="text-center min-w-[72px]">
          <div className="font-mono text-2xl md:text-3xl font-bold tabular-nums" style={{ color: config.color }}>
            {geoScore}
          </div>
          <div className="text-[10px] font-mono text-text-muted mt-0.5">/ 100 GEO</div>
        </div>

        <div className="w-px h-10 bg-border" />

        <div className="text-center min-w-[72px]">
          <div className="font-mono text-2xl md:text-3xl font-bold tabular-nums text-text-secondary">
            {citabilityScore}
          </div>
          <div className="text-[10px] font-mono text-text-muted mt-0.5">/ 100 Citability</div>
        </div>
      </div>
    </div>
  );
}
