import React, { useEffect, useState } from 'react';
import { loadScores } from '../../lib/scoreHistory';
import type { ScoreEntry } from '../../lib/scoreHistory';

// Band → state token (Status Monopoly rule): excellent/good report pass,
// foundation reports warn, critical reports fail; unknown grades read as queued.
const gradeColor: Record<string, string> = {
  excellent: 'var(--color-pass)',
  good: 'var(--color-pass)',
  foundation: 'var(--color-warn)',
  critical: 'var(--color-fail)',
};

interface ScoreHistoryProps {
  url: string;
  currentScore: number;
}

export default function ScoreHistory({ url, currentScore }: ScoreHistoryProps) {
  const [entries, setEntries] = useState<ScoreEntry[]>([]);

  useEffect(() => {
    setEntries(loadScores(url));
  }, [url, currentScore]);

  if (entries.length < 2) return null;

  const oldest = entries[entries.length - 1];
  const delta = currentScore - oldest.score;
  const deltaPositive = delta > 0;

  return (
    <div className="rounded-[10px] border border-rail bg-raised p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-text text-[12.5px] font-semibold text-ink-mute">
          Score History
        </h3>
        <span className={`font-mono text-xs font-semibold tabular-nums ${deltaPositive ? 'text-pass-deep' : delta < 0 ? 'text-fail' : 'text-ink-mute'}`}>
          {deltaPositive ? '+' : ''}{delta} vs first
        </span>
      </div>

      <div className="flex h-10 items-end gap-1">
        {[...entries].reverse().map((entry, i) => {
          const isLast = i === entries.length - 1;
          const heightPct = Math.max(8, (entry.score / 100) * 100);
          const color = gradeColor[entry.grade] ?? 'var(--color-queued)';
          return (
            <div key={i} className="group relative flex flex-1 flex-col items-center gap-0.5">
              <div
                className={`w-full rounded-[6px] transition-all ${isLast ? 'ring-1 ring-ink/40' : ''}`}
                style={{ height: `${heightPct}%`, backgroundColor: color, opacity: isLast ? 1 : 0.5 }}
              />
              <div className="absolute -top-7 left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded-[6px] border border-rail bg-raised px-1.5 py-0.5 font-mono text-[10px] tabular-nums text-ink group-hover:flex">
                {entry.score} · {new Date(entry.timestamp).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-ink-mute">
        <span>{new Date(oldest.timestamp).toLocaleDateString('en', { month: 'short', day: 'numeric' })}</span>
        <span>Today</span>
      </div>
    </div>
  );
}
