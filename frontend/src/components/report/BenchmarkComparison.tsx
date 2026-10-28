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
  const { avgScore, medianScore, totalDomains, bands } = benchmark2026;
  const band = bands[grade];
  const isAboveAvg = score >= avgScore;
  // Derived from the band itself, not a separately-tuned score threshold —
  // a numeric cutoff (e.g. 66) can land inside a lower band (foundation is
  // 36-67) and produce self-contradictory copy ("top 25%" + "64.6% share
  // your band"). "Excellent" is always the top band by construction.
  const isTopQuarter = grade === 'excellent';

  return (
    <div className="overflow-hidden rounded-[10px] border border-rail bg-white">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-rail px-5 py-2.5">
        <span className="font-text text-[12.5px] font-semibold text-ink-mute">
          Benchmark
        </span>
        <span className="font-text font-medium text-[12px] text-ink-mute">
          State of GEO · {totalDomains} domains · June 2026
        </span>
      </div>

      <div className="p-5">
        {/* Score vs average */}
        <div className="mb-4 grid grid-cols-3 gap-4">
          <div>
            <div className="font-text text-[12px] font-semibold text-ink-mute">Your score</div>
            <div className="mt-0.5 font-mono text-2xl font-bold tabular-nums text-ink">{score}</div>
          </div>
          <div>
            <div className="font-text text-[12px] font-semibold text-ink-mute">Average</div>
            <div className="mt-0.5 font-mono text-2xl font-bold tabular-nums text-ink-soft">{avgScore}</div>
          </div>
          <div>
            <div className="font-text text-[12px] font-semibold text-ink-mute">Median</div>
            <div className="mt-0.5 font-mono text-2xl font-bold tabular-nums text-ink-soft">{medianScore}</div>
          </div>
        </div>

        {/* Position bar — the visitor's row is solid, the cohort marker dashed */}
        <div className="mb-3">
          <div className="mb-1.5 flex items-center justify-between font-mono text-[10px] tabular-nums text-ink-mute">
            <span>0</span>
            <span>50</span>
            <span>100</span>
          </div>
          <div className="relative h-2.5 overflow-hidden rounded-[6px] border border-ink/40 bg-paper">
            {/* Cohort average marker (reference data → dashed) */}
            <div
              className="absolute bottom-0 top-0 w-0 border-l border-dashed border-ink-mute/60"
              style={{ left: `${avgScore}%` }}
              title={`Average: ${avgScore}`}
            />
            {/* Score bar (your data → solid fill) */}
            <div
              className={`h-full transition-all duration-700 ${isAboveAvg ? 'bg-pass' : 'bg-warn'}`}
              style={{ width: `${Math.min(score, 100)}%` }}
            />
          </div>
        </div>

        {/* Verdict */}
        <p className="text-sm leading-relaxed text-ink-soft">
          {isTopQuarter ? (
            <>
              You're in the <strong className="font-semibold text-pass-deep">top {band.share}%</strong> of audited sites.
              Only <strong className="font-semibold text-ink">{band.domains}</strong> sites reach the {gradeLabels[grade]} band.
            </>
          ) : isAboveAvg ? (
            <>
              You're <strong className="font-semibold text-pass-deep">above average</strong> (+{(score - avgScore).toFixed(1)} points),
              but still in the {gradeLabels[grade]} band. <strong className="font-semibold text-ink">{band.share}%</strong> of sites are here.
            </>
          ) : (
            <>
              You're <strong className="font-semibold text-warn">below average</strong> ({(score - avgScore).toFixed(1)} points).
              <strong className="font-semibold text-ink"> {band.share}%</strong> of sites are in the {gradeLabels[grade]} band. Most can be reached by AI but cannot be cited with confidence.
            </>
          )}
        </p>
      </div>

      <div className="border-t border-rail px-5 py-2.5">
        <p className="font-text font-medium text-[12px] text-ink-mute">
          source: lib/benchmark2026.ts
        </p>
      </div>
    </div>
  );
}
