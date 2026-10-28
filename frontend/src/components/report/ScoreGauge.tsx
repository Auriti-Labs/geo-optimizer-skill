import React from 'react';

interface ScoreGaugeProps {
  score: number;
  maxScore?: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
}

// Band → state token (Status Monopoly rule): excellent/good report pass,
// foundation reports warn, critical reports fail. Bands from SCORE_BANDS.
const getBand = (score: number, max: number) => {
  const pct = score / max;
  if (pct >= 0.86) return { label: 'Excellent', chip: 'bg-pass-wash text-pass-deep', bar: 'bg-pass' };
  if (pct >= 0.68) return { label: 'Good', chip: 'bg-pass-wash text-pass-deep', bar: 'bg-pass' };
  if (pct >= 0.36) return { label: 'Foundation', chip: 'bg-warn-wash text-warn', bar: 'bg-warn' };
  return { label: 'Critical', chip: 'bg-fail-wash text-fail', bar: 'bg-fail' };
};

// Console treatment: the large Geist tabular score sits over a horizontal
// meter (the visitor's own data, drawn solid), with the band name as a chip.
// `size` is the meter width and `strokeWidth` its height, so the legacy
// ring-gauge props keep their meaning.
export default function ScoreGauge({
  score,
  maxScore = 100,
  size = 140,
  strokeWidth = 8,
  label = 'GEO Score',
}: ScoreGaugeProps) {
  const percentage = Math.min(Math.max(score / maxScore, 0), 1);
  const band = getBand(score, maxScore);

  return (
    <div className="flex flex-col items-center">
      <div className="flex items-baseline gap-1.5">
        <span className="font-head text-4xl font-semibold tabular-nums text-ink">
          {score}
        </span>
        <span className="font-mono text-[11px] tabular-nums text-ink-mute">
          / {maxScore}
        </span>
      </div>
      <div
        className="mt-2.5 overflow-hidden rounded-[6px] border border-ink/40 bg-paper"
        style={{ width: size, height: strokeWidth }}
        aria-hidden="true"
      >
        <div
          className={`h-full transition-[width] duration-1000 ease-out ${band.bar}`}
          style={{ width: `${percentage * 100}%` }}
        />
      </div>
      <div className="mt-2.5 flex flex-col items-center gap-1 text-center">
        <span className={`rounded-[6px] px-1.5 py-0.5 font-text text-[12px] font-semibold ${band.chip}`}>
          {band.label}
        </span>
        <span className="font-text font-medium text-[12px] text-ink-mute">{label}</span>
      </div>
    </div>
  );
}
