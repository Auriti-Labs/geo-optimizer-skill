// Score-band bars for the State of GEO pages.
//
// One colour per band, fixed (the colour follows the band, not its position). The four colours were
// checked with the dataviz palette validator: all clear 3:1 on white and stay apart under colour-vision
// deficiency. The same mapping is used by the newsletter chart on the platform side.

export const BAND_COLORS: Record<string, string> = {
  Excellent: '#0D9488',
  Good: '#2A78D6',
  Foundation: '#6250D6',
  Critical: '#EB6834',
};

export const FALLBACK_COLOR = '#0D9488';
const MIN_SLIVER_PCT = 0.7; // a real 0.2% would be invisible: keep a thin bar so the row still shows one

export interface BandBar {
  label: string;
  pct: number; // clamped 0-100, as printed
  widthPct: number; // as drawn, never below the sliver
  color: string;
}

export function bandBars(shares: ReadonlyArray<readonly [string, number]>): BandBar[] {
  return shares.map(([label, raw]) => {
    const pct = Math.max(0, Math.min(100, Number.isFinite(raw) ? raw : 0));
    return {
      label,
      pct,
      widthPct: Math.max(MIN_SLIVER_PCT, pct),
      color: BAND_COLORS[label] ?? FALLBACK_COLOR,
    };
  });
}
