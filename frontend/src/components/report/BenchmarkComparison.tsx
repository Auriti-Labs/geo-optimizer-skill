import React from 'react';
import { benchmark2026 } from '../../lib/benchmark2026';

interface BenchmarkComparisonProps {
  score: number;
  grade: 'excellent' | 'good' | 'foundation' | 'critical';
}

const gradeLabels: Record<string, string> = {
  excellent: 'Excellent',
  good: 'Good',
  foundation: 'Foundation',
  critical: 'Critical',
};

export default function BenchmarkComparison({ score, grade }: BenchmarkComparisonProps) {
  const { avgScore, medianScore, topQuarterThreshold, totalDomains, bands } = benchmark2026;
  const band = bands[grade];
  const isAboveAvg = score >= avgScore;
  const isTopQuarter = score >= topQuarterThreshold;
  const percentile = Math.round(((totalDomains - band.domains) / totalDomains) * 100);

  return (
    <div className="p-5 rounded-xl border border-border bg-bg-surface">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-text-muted">
          Benchmark
        </span>
        <span className="text-[10px] font-mono text-text-muted">
          State of GEO · {totalDomains} domains · June 2026
        </span>
      </div>

      {/* Score vs average */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Your score</div>
          <div className="font-mono text-2xl font-bold tabular-nums text-text-primary mt-0.5">{score}</div>
        </div>
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Average</div>
          <div className="font-mono text-2xl font-bold tabular-nums text-text-secondary mt-0.5">{avgScore}</div>
        </div>
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Median</div>
          <div className="font-mono text-2xl font-bold tabular-nums text-text-secondary mt-0.5">{medianScore}</div>
        </div>
      </div>

      {/* Position bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-[10px] font-mono text-text-muted mb-1.5">
          <span>0</span>
          <span>50</span>
          <span>100</span>
        </div>
        <div className="relative h-2 rounded-full bg-bg-subtle overflow-hidden">
          {/* Average marker */}
          <div
            className="absolute top-0 bottom-0 w-px bg-text-muted/40"
            style={{ left: `${avgScore}%` }}
            title={`Average: ${avgScore}`}
          />
          {/* Score bar */}
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${Math.min(score, 100)}%`,
              backgroundColor: isAboveAvg ? '#059669' : '#D97706',
            }}
          />
        </div>
      </div>

      {/* Verdict */}
      <p className="text-sm text-text-secondary leading-relaxed">
        {isTopQuarter ? (
          <>
            You're in the <strong className="text-accent-success">top 25%</strong> of audited sites.
            Only <strong className="text-text-primary">{band.domains}</strong> sites ({band.share}%) reach the {gradeLabels[grade]} band.
          </>
        ) : isAboveAvg ? (
          <>
            You're <strong className="text-accent-success">above average</strong> (+{(score - avgScore).toFixed(1)} points),
            but still in the {gradeLabels[grade]} band — <strong className="text-text-primary">{band.share}%</strong> of sites are here.
          </>
        ) : (
          <>
            You're <strong className="text-accent-warning">below average</strong> ({(score - avgScore).toFixed(1)} points).
            <strong className="text-text-primary"> {band.share}%</strong> of sites are in the {gradeLabels[grade]} band — most can be reached by AI but cannot be cited with confidence.
          </>
        )}
      </p>
    </div>
  );
}