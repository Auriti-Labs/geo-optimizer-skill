import React from 'react';

interface ScoreGaugeProps {
  score: number;
  maxScore?: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
}

const getGradeColor = (score: number, max: number) => {
  const pct = score / max;
  if (pct >= 0.86) return '#059669';
  if (pct >= 0.68) return '#0D9488';
  if (pct >= 0.36) return '#D97706';
  return '#DC2626';
};

const getGradeLabel = (score: number, max: number) => {
  const pct = score / max;
  if (pct >= 0.86) return 'Excellent';
  if (pct >= 0.68) return 'Good';
  if (pct >= 0.36) return 'Foundation';
  return 'Critical';
};

export default function ScoreGauge({
  score,
  maxScore = 100,
  size = 140,
  strokeWidth = 8,
  label = 'GEO Score',
}: ScoreGaugeProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const percentage = Math.min(Math.max(score / maxScore, 0), 1);
  const offset = circumference * (1 - percentage);
  const color = getGradeColor(score, maxScore);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#E2E0DA"
            strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-2xl font-bold tabular-nums" style={{ color }}>
            {score}
          </span>
          <span className="text-[10px] font-mono text-text-muted">
            / {maxScore}
          </span>
        </div>
      </div>
      <div className="mt-2.5 text-center">
        <div className="text-[11px] font-mono font-semibold uppercase tracking-wider" style={{ color }}>
          {getGradeLabel(score, maxScore)}
        </div>
        <div className="text-[10px] text-text-muted">{label}</div>
      </div>
    </div>
  );
}
