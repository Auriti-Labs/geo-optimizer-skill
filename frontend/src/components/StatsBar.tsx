import { useEffect, useState } from 'react';
import { buildApiUrl } from '../lib/api';

interface Stats {
  github_stars: number;
  pypi_downloads_month: number;
  audits_run: number;
}

function fmt(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

// I valori iniziali arrivano dal build (vedi utils/publicStats.ts): così l'HTML servito a
// un crawler AI porta già i contatori aggiornati, invece del vecchio fallback statico che
// dichiarava 5.134 download/mese contro i 71.997 reali. Il fetch qui sotto resta perché
// aggiorna i numeri nel browser fra un rebuild e l'altro.
interface StatsBarProps {
  initial?: Stats;
  /** true = i valori iniziali vengono dall'endpoint, non da un fallback hardcoded. */
  initialIsLive?: boolean;
  /** "console" is the homepage CI-run world; default keeps the incumbent look. */
  variant?: 'default' | 'console';
}

// Usato solo se la pagina non passa nulla (nessun chiamante oggi lo fa).
// Shown only until /api/stats answers. pypi_downloads_month is now genuinely
// monthly (pypistats /recent), so this value is an order of magnitude lower than
// the old one, which was a lifetime cumulative mislabelled as monthly.
const FALLBACK: Stats = { github_stars: 831, pypi_downloads_month: 5690, audits_run: 2006 };

export default function StatsBar({ initial, initialIsLive = false, variant = 'default' }: StatsBarProps) {
  const [stats, setStats] = useState<Stats>(initial ?? FALLBACK);
  const [live, setLive] = useState(initialIsLive);

  useEffect(() => {
    fetch(buildApiUrl('/stats'))
      .then((r) => r.json())
      .then((data: Stats) => {
        // All or nothing, same rule as utils/publicStats.ts: the endpoint returns 0
        // for any counter it could not fetch, and a 0 on screen reads as "nobody uses
        // this" — worse than the build-time value from a few hours earlier.
        if (data.github_stars > 0 && data.pypi_downloads_month > 0 && data.audits_run > 0) {
          setStats(data);
          setLive(true);
        }
      })
      .catch(() => {});
  }, []);

  if (variant === 'console') {
    const rows: Array<[string, string]> = [
      [fmt(stats.github_stars), 'GitHub stars'],
      [fmt(stats.pypi_downloads_month), 'downloads/mo'],
      [fmt(stats.audits_run), 'audits run'],
    ];
    return (
      <div>
        <dl className="mt-8 flex flex-wrap items-stretch gap-y-2 divide-x divide-rail">
          {rows.map(([value, label]) => (
            <div key={label} className="flex items-baseline gap-2 pr-5 pl-5 first:pl-0">
              <dd className="font-mono text-base font-semibold tabular-nums text-ink">{value}</dd>
              <dt className="text-[13px] text-ink-mute">{label}</dt>
            </div>
          ))}
        </dl>
        <p className="mt-2 font-text font-medium text-[12.5px] text-ink-mute">
          {live ? (
            <>
              <span aria-hidden="true" className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-pass align-middle" />
              live · GET /api/stats
            </>
          ) : (
            'snapshot: counters could not be refreshed'
          )}
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mt-8 flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-2 text-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="text-yellow-400 shrink-0" aria-hidden="true">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
          </svg>
          <span className="font-mono font-semibold">{fmt(stats.github_stars)}</span>
          <span className="text-text-muted">stars</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400 shrink-0" aria-hidden="true">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
            <line x1="12" y1="22.08" x2="12" y2="12"/>
          </svg>
          <span className="font-mono font-semibold">{fmt(stats.pypi_downloads_month)}</span>
          <span className="text-text-muted">downloads/mo</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-400 shrink-0" aria-hidden="true">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <span className="font-mono font-semibold">{fmt(stats.audits_run)}</span>
          <span className="text-text-muted">audits</span>
        </div>
      </div>
      {!live && (
        <p className="mt-2 text-xs text-text-muted font-mono">Snapshot: counters could not be refreshed</p>
      )}
    </div>
  );
}
